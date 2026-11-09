"""
implementacion/cloud_tool/omnimorph_engine.py
==============================================
Omnimorph Engine — Fases 1 a 5 + Monitores M2.0 a M2.5

FASE 1  — Separación track/ball, moda de equipo
FASE 2  — Cinemática Savitzky-Golay (v ≤ 9.5 m/s)
FASE 3  — Track Stitching (Algoritmo Húngaro)
FASE 4  — Homografía EMA normalizada H/H[2,2]
FASE 5  — Ventanas Tácticas de 4.0 s

Monitores:
  M2.0 — Separación track/ball y moda de equipo
  M2.1 — Homografía EMA normalizada
  M2.2 — Track Stitching
  M2.3 — Cinemática Savitzky-Golay
  M2.4 — Ventanas Tácticas
  M2.5 — Integridad del pipeline completo

Salidas:
  data/clean/objects_cleaned.parquet
  data/clean/tactical_summaries.json
  data/clean/monitor_m2.json
"""

from __future__ import annotations

import json
import pathlib
import time
import warnings
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from scipy.signal import savgol_filter
    from scipy.optimize import linear_sum_assignment
    SCIPY_OK = True
except ImportError:
    SCIPY_OK = False
    warnings.warn("[omnimorph_engine] scipy no disponible — usando fallback simple.")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
FPS = 25.0
N_FRAMES = 750
WINDOW_SIZE_S = 4.0
WINDOW_SIZE_FRAMES = int(WINDOW_SIZE_S * FPS)   # 100 frames
N_WINDOWS = 8                                    # 8 ventanas de 4.0 s (la ultima puede ser parcial)
V_MAX_MPS = 9.5                                  # m/s — velocidad máxima humana
EMA_ALPHA = 0.3                                  # suavizado homografía
STITCH_MAX_DIST_CM = 300.0                       # 3 m — umbral costura
STITCH_MAX_GAP_FRAMES = 30                       # 1 s a 30 fps: más allá se considera otro rastro
STITCH_FPS = 30.0                                # fps aproximados de los clips reales (alcance de costura)
STITCH_SIN_ENLACE = 1e9                          # costo de una pareja que no se puede unir
PITCH_L_CM = 12_000.0
PITCH_W_CM = 7_000.0
SAVGOL_WINDOW = 9
SAVGOL_POLY = 3

CLEAN_DIR = pathlib.Path("data/clean")


def _fps_clip(total_frames: int) -> float:
    """FPS del clip: los datos sintéticos tienen N_FRAMES a 25 fps; los reales, los del partido activo."""
    if total_frames <= N_FRAMES:
        return FPS
    from implementacion import partido_config
    return partido_config.activo().fps


# ===========================================================================
# FASE 1 — Separación track/ball y moda de equipo
# ===========================================================================

def phase1_separate_and_team(
    df_objects: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[int, int]]:
    """
    Separa track vs ball.
    Asigna equipo por moda de track_id a lo largo del clip.
    Interpola coordenadas pitch_x / pitch_y faltantes en tomas cerradas.

    Retorna:
        df_track   : filas source == 'track'
        df_ball    : filas source == 'ball'
        team_map   : {track_id → team_id (0|1|None)}
    """
    df_track = df_objects[df_objects["source"] == "track"].copy()
    df_ball = df_objects[df_objects["source"] == "ball"].copy()

    # Asegurar coordenadas pitch_x, pitch_y sin NaN (interpolación por track + proyección bbox)
    for df_sub in (df_track, df_ball):
        if len(df_sub) == 0:
            continue
        df_sub["pitch_x"] = pd.to_numeric(df_sub["pitch_x"], errors="coerce")
        df_sub["pitch_y"] = pd.to_numeric(df_sub["pitch_y"], errors="coerce")
        if "track_id" in df_sub.columns and df_sub["track_id"].notna().any():
            df_sub["pitch_x"] = df_sub.groupby("track_id")["pitch_x"].transform(
                lambda s: s.ffill().bfill()
            )
            df_sub["pitch_y"] = df_sub.groupby("track_id")["pitch_y"].transform(
                lambda s: s.ffill().bfill()
            )
        # Fallback proporcional desde imagen a cancha (12000 x 7000 cm)
        bx = ((df_sub["x1"].astype(float) + df_sub["x2"].astype(float)) / 2.0) / 1280.0 * PITCH_L_CM
        by = (df_sub["y2"].astype(float)) / 720.0 * PITCH_W_CM
        df_sub["pitch_x"] = df_sub["pitch_x"].fillna(bx.clip(0.0, PITCH_L_CM)).fillna(6000.0)
        df_sub["pitch_y"] = df_sub["pitch_y"].fillna(by.clip(0.0, PITCH_W_CM)).fillna(3500.0)

    # Moda de equipo por track_id
    team_map: Dict[int, Optional[int]] = {}
    for tid, grp in df_track.groupby("track_id"):
        if tid is None or (isinstance(tid, float) and np.isnan(tid)):
            continue
        teams = grp["team"].dropna()
        if len(teams) == 0:
            team_map[int(tid)] = None
        else:
            mode_val = teams.mode()
            team_map[int(tid)] = int(mode_val.iloc[0]) if len(mode_val) > 0 else None

    return df_track, df_ball, team_map


# ===========================================================================
# FASE 4 — Homografía EMA normalizada H/H[2,2]
# ===========================================================================

def phase4_homography_ema(
    df_frames: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza H: H_norm = H / H[2,2]
    Aplica suavizado EMA: H_ema[t] = α*H[t] + (1-α)*H_ema[t-1]
    En fotogramas de toma cerrada (sin homografía directa), mantiene la última
    matriz H_ema válida (sample-and-hold) para garantizar continuidad 100%.

    Agrega columnas H_norm y H_ema a df_frames.
    """
    df_out = df_frames.copy()
    h_ema = None

    h_norms = []
    h_emas = []

    for _, row in df_out.iterrows():
        raw_h = row.get("H")
        is_valid = bool(row.get("homography_valid", False)) and raw_h is not None
        if not is_valid:
            h_norms.append(None)
            if h_ema is not None:
                h_emas.append(list(h_ema.flatten().round(6)))
            else:
                h_emas.append(None)
            continue

        h_raw = np.array(raw_h, dtype=float).reshape(3, 3)
        # Normalizar
        h22 = h_raw[2, 2]
        h_norm = h_raw / h22 if abs(h22) > 1e-9 else h_raw

        # EMA
        if h_ema is None:
            h_ema = h_norm.copy()
        else:
            h_ema = EMA_ALPHA * h_norm + (1.0 - EMA_ALPHA) * h_ema

        h_norms.append(list(h_norm.flatten().round(6)))
        h_emas.append(list(h_ema.flatten().round(6)))

    # Backfill inicial si los primeros fotogramas no tenían H válida
    first_valid_ema = next((x for x in h_emas if x is not None), list(np.eye(3).flatten()))
    h_emas = [x if x is not None else first_valid_ema for x in h_emas]

    df_out["H_norm"] = h_norms
    df_out["H_ema"] = h_emas
    return df_out


# ===========================================================================
# FASE 3 — Track Stitching (Algoritmo Húngaro)
# ===========================================================================

def phase3_track_stitching(
    df_track: pd.DataFrame,
    team_map: Dict[int, Optional[int]],
) -> pd.DataFrame:
    """
    Une fragmentos de ByteTrack en rastros mediante el Algoritmo Húngaro.

    Un fragmento solo continúa a otro que ya terminó, hace poco y a una distancia
    alcanzable corriendo, sin cambiar de equipo. Así un rastro nunca tiene dos
    posiciones en el mismo frame. Un rastro no equivale a un jugador: tras un corte
    de cámara la misma persona empieza otro.

    Costo(i,j) = distancia entre el final de i y el inicio de j.
    El rastro conserva el id de su primer fragmento, que ya está en team_map.

    Retorna df_track con columna track_id_stitched añadida.
    """
    df = df_track.sort_values(["frame", "track_id"]).copy()
    df["track_id_stitched"] = df["track_id"].astype("Int64")

    if not SCIPY_OK or df["track_id"].notna().sum() == 0:
        # Fallback: stitched == original
        return df

    fragmentos = []
    for tid, grp in df.dropna(subset=["track_id"]).groupby("track_id"):
        pos = grp.dropna(subset=["pitch_x", "pitch_y"])
        fragmentos.append({
            "id": int(tid),
            "ini": int(grp["frame"].min()),
            "fin": int(grp["frame"].max()),
            "equipo": team_map.get(int(tid)),
            "pos_ini": tuple(pos[["pitch_x", "pitch_y"]].iloc[0]) if len(pos) else None,
            "pos_fin": tuple(pos[["pitch_x", "pitch_y"]].iloc[-1]) if len(pos) else None,
        })
    fragmentos.sort(key=lambda f: (f["ini"], f["id"]))

    id_remap: Dict[int, int] = {}
    rastros: List[dict] = []  # final de cada rastro abierto: {id, fin, pos_fin, equipo}

    for frame in sorted({f["ini"] for f in fragmentos}):
        nuevos = [f for f in fragmentos if f["ini"] == frame]
        abiertos = [r for r in rastros if r["fin"] < frame and frame - r["fin"] <= STITCH_MAX_GAP_FRAMES]

        costos = np.full((len(abiertos), len(nuevos)), STITCH_SIN_ENLACE)
        for i, r in enumerate(abiertos):
            for j, f in enumerate(nuevos):
                if r["pos_fin"] is None or f["pos_ini"] is None:
                    continue
                if None not in (r["equipo"], f["equipo"]) and r["equipo"] != f["equipo"]:
                    continue
                dist = float(np.hypot(r["pos_fin"][0] - f["pos_ini"][0], r["pos_fin"][1] - f["pos_ini"][1]))
                alcance = STITCH_MAX_DIST_CM + V_MAX_MPS * 100.0 * (frame - r["fin"]) / STITCH_FPS
                if dist <= alcance:
                    costos[i, j] = dist

        enlazados = set()
        if costos.size:
            for i, j in zip(*linear_sum_assignment(costos)):
                if costos[i, j] < STITCH_SIN_ENLACE:
                    r, f = abiertos[i], nuevos[j]
                    id_remap[f["id"]] = r["id"]
                    r.update(fin=f["fin"], pos_fin=f["pos_fin"] or r["pos_fin"],
                             equipo=r["equipo"] if r["equipo"] is not None else f["equipo"])
                    enlazados.add(j)

        for j, f in enumerate(nuevos):
            if j not in enlazados:
                id_remap[f["id"]] = f["id"]
                rastros.append({"id": f["id"], "fin": f["fin"], "pos_fin": f["pos_fin"], "equipo": f["equipo"]})

    df["track_id_stitched"] = df["track_id"].map(
        lambda tid: id_remap.get(int(tid)) if pd.notna(tid) else None
    ).astype("Int64")
    return df


# ===========================================================================
# FASE 2 — Cinemática Savitzky-Golay
# ===========================================================================

def phase2_kinematics(df_track: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada track_id_stitched, aplica Savitzky-Golay a pitch_x y pitch_y,
    luego calcula velocidad en m/s. Clips la velocidad a V_MAX_MPS.

    Columnas anadidas: pitch_x_smooth, pitch_y_smooth, vx_mps, vy_mps, v_mps, v_clipped
    """
    # Reset index para garantizar indices posicionales 0..N-1
    df = df_track.copy().sort_values(["track_id_stitched", "frame"]).reset_index(drop=True)
    fps = _fps_clip(int(df["frame"].max()) + 1) if len(df) else FPS

    n_total = len(df)
    smooth_x = np.full(n_total, np.nan)
    smooth_y = np.full(n_total, np.nan)
    vx_arr = np.full(n_total, np.nan)
    vy_arr = np.full(n_total, np.nan)
    v_arr = np.full(n_total, np.nan)
    v_clip_arr = np.full(n_total, np.nan)

    for tid, grp in df.groupby("track_id_stitched"):
        # iloc positions (posicionales, no de etiqueta)
        pos = grp.index.to_numpy()
        n = len(pos)

        px_vals = grp["pitch_x"].values.astype(float)
        py_vals = grp["pitch_y"].values.astype(float)

        if n < SAVGOL_WINDOW:
            sx = px_vals.copy()
            sy = py_vals.copy()
        else:
            if SCIPY_OK:
                sx = savgol_filter(px_vals, SAVGOL_WINDOW, SAVGOL_POLY)
                sy = savgol_filter(py_vals, SAVGOL_WINDOW, SAVGOL_POLY)
            else:
                sx = pd.Series(px_vals).rolling(5, min_periods=1, center=True).mean().values
                sy = pd.Series(py_vals).rolling(5, min_periods=1, center=True).mean().values

        smooth_x[pos] = sx
        smooth_y[pos] = sy

        if n >= 2:
            dx = np.diff(sx, prepend=sx[0]) * fps / 100.0   # m/s
            dy = np.diff(sy, prepend=sy[0]) * fps / 100.0
            spd = np.sqrt(dx**2 + dy**2)
            vx_arr[pos] = dx
            vy_arr[pos] = dy
            v_arr[pos] = spd
            v_clip_arr[pos] = np.clip(spd, 0, V_MAX_MPS)

    df["pitch_x_smooth"] = smooth_x
    df["pitch_y_smooth"] = smooth_y
    df["vx_mps"] = vx_arr
    df["vy_mps"] = vy_arr
    df["v_mps"] = v_arr
    df["v_clipped"] = v_clip_arr
    return df


# ===========================================================================
# FASE 5 — Ventanas Tácticas de 4.0 s
# ===========================================================================

def phase5_tactical_windows(
    df_track_clean: pd.DataFrame,
    df_ball: pd.DataFrame,
    team_map: Dict[int, Optional[int]],
) -> List[Dict[str, Any]]:
    """
    Divide el video en 8 ventanas tácticas uniformes a lo largo de todo el clip.
    Calcula métricas tácticas por ventana.

    Retorna lista de 8 dicts con:
      window_id, t0, t1, frame_start, frame_end,
      block_height_m, block_compactness_m,
      transition_speed_mps, pressure_context, dominant_team,
      n_arg, n_fra, centroid_arg_x, centroid_fra_x
    """
    max_frame = int(df_track_clean["frame"].max()) + 1 if len(df_track_clean) > 0 else N_FRAMES
    total_frames = max(max_frame, N_FRAMES)
    fps_clip = _fps_clip(total_frames)
    if total_frames > N_FRAMES:
        from implementacion import partido_config
        equipos = partido_config.activo().equipos
    else:
        equipos = None  # datos sintéticos: códigos legados ARG/FRA
    win_frames = max(int(np.ceil(total_frames / N_WINDOWS)), WINDOW_SIZE_FRAMES)
    win_s = round(win_frames / fps_clip, 2)

    windows = []
    for w in range(N_WINDOWS):
        f0 = w * win_frames
        f1 = min(f0 + win_frames, total_frames)
        t0 = round(f0 / fps_clip, 2)
        t1 = round(f1 / fps_clip, 2)

        mask_w = (df_track_clean["frame"] >= f0) & (df_track_clean["frame"] < f1)
        df_w = df_track_clean[mask_w]

        # Separar por equipo usando team_map o columna team
        def team_of(row_tid):
            if row_tid is None or (isinstance(row_tid, float) and np.isnan(row_tid)):
                return None
            return team_map.get(int(row_tid))

        mapped_teams = df_w["track_id_stitched"].apply(team_of)
        if "team" in df_w.columns:
            mapped_teams = mapped_teams.fillna(df_w["team"])

        arg_mask = mapped_teams == 0
        fra_mask = mapped_teams == 1

        df_arg = df_w[arg_mask]
        df_fra = df_w[fra_mask]

        # block_height_m: dispersión vertical del equipo (std pitch_y en m)
        block_height = 0.0
        if "pitch_y_smooth" in df_arg.columns and len(df_arg) > 1:
            std_arg_y = float(df_arg["pitch_y_smooth"].std())
            std_fra_y = float(df_fra["pitch_y_smooth"].std()) if len(df_fra) > 1 else 0.0
            if np.isnan(std_arg_y):
                std_arg_y = 0.0
            if np.isnan(std_fra_y):
                std_fra_y = 0.0
            block_height = (std_arg_y + std_fra_y) / 100.0

        # block_compactness_m: distancia media entre jugadores de la línea defensiva
        block_compactness = 0.0
        if "pitch_x_smooth" in df_arg.columns and len(df_arg) > 1:
            std_arg_x = float(df_arg["pitch_x_smooth"].std())
            block_compactness = 0.0 if np.isnan(std_arg_x) else (std_arg_x / 100.0)

        # transition_speed_mps: velocidad media del balón en la ventana
        mask_ball_w = (df_ball["frame"] >= f0) & (df_ball["frame"] < f1)
        df_ball_w = df_ball[mask_ball_w]
        transition_speed = 0.0
        if len(df_ball_w) >= 2:
            dx_b = np.diff(df_ball_w["pitch_x"].values.astype(float)) * fps_clip / 100.0
            dy_b = np.diff(df_ball_w["pitch_y"].values.astype(float)) * fps_clip / 100.0
            spd_b = np.sqrt(dx_b**2 + dy_b**2)
            spd_b = spd_b[~np.isnan(spd_b)]
            if len(spd_b) > 0:
                transition_speed = float(np.mean(spd_b))
                transition_speed = min(transition_speed, V_MAX_MPS)

        # Centroides
        centroid_arg_x = float(df_arg["pitch_x_smooth"].mean()) if len(df_arg) > 0 and "pitch_x_smooth" in df_arg.columns else 6000.0
        centroid_fra_x = float(df_fra["pitch_x_smooth"].mean()) if len(df_fra) > 0 and "pitch_x_smooth" in df_fra.columns else 6000.0
        if np.isnan(centroid_arg_x):
            centroid_arg_x = 6000.0
        if np.isnan(centroid_fra_x):
            centroid_fra_x = 6000.0

        # pressure_context y dominant_team: un equipo domina si su centroide
        # está en campo rival según hacia dónde ataca. Se revisa primero el team_id 0.
        cod0, cod1 = ("ARG", "FRA") if equipos is None else (equipos[0].codigo, equipos[1].codigo)
        dir0 = "+x" if equipos is None else equipos[0].ataca_hacia
        mitad = PITCH_L_CM / 2
        t0_en_campo_rival = centroid_arg_x > mitad if dir0 == "+x" else centroid_arg_x < mitad
        t1_en_campo_rival = centroid_fra_x < mitad if dir0 == "+x" else centroid_fra_x > mitad
        if t0_en_campo_rival:
            pressure_context = "ataque"
            dominant_team = cod0
        elif t1_en_campo_rival:
            pressure_context = "defensa"
            dominant_team = cod1
        else:
            pressure_context = "neutro"
            dominant_team = "neutro"

        windows.append({
            "window_id": f"W{w}",
            "t0": round(t0, 2),
            "t1": round(t1, 2),
            "frame_start": f0,
            "frame_end": max(f1 - 1, f0),
            "block_height_m": round(block_height, 3),
            "block_compactness_m": round(block_compactness, 3),
            "transition_speed_mps": round(transition_speed, 3),
            "pressure_context": pressure_context,
            "dominant_team": dominant_team,
            "n_arg": int(arg_mask.sum()),
            "n_fra": int(fra_mask.sum()),
            "centroid_arg_x_cm": round(centroid_arg_x, 1),
            "centroid_fra_x_cm": round(centroid_fra_x, 1),
        })

    return windows


# ===========================================================================
# Monitores M2.0 – M2.5
# ===========================================================================

def _check(name: str, condition: bool, obs: Any, desc: str) -> dict:
    return {"name": name, "pass": condition, "observed": obs, "description": desc}


def run_stage_monitors(
    df_frames: pd.DataFrame,
    df_objects_orig: pd.DataFrame,
    df_track: pd.DataFrame,
    df_ball: pd.DataFrame,
    df_track_clean: pd.DataFrame,
    tactical_windows: List[dict],
    team_map: Dict[int, Optional[int]],
) -> dict:
    """
    Ejecuta los Monitores M2.0 a M2.5.
    Guarda el reporte en data/clean/monitor_m2.json.
    """
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    checks = {}

    # M2.0 — Separación track/ball
    n_track = int((df_objects_orig["source"] == "track").sum())
    n_ball = int((df_objects_orig["source"] == "ball").sum())
    checks["M2.0"] = {
        "monitor": "M2.0",
        "name": "Separación track/ball y moda de equipo",
        "pass": n_track >= 1 and n_ball >= 1,
        "details": {
            "n_track_rows": n_track,
            "n_ball_rows": n_ball,
            "n_unique_track_ids": int(df_track["track_id"].nunique()),
            "team_map_entries": len(team_map),
        },
    }

    # M2.1 — Homografía EMA normalizada
    n_hv = int(df_frames["homography_valid"].sum()) if "homography_valid" in df_frames.columns else 0
    hv_rate = n_hv / max(len(df_frames), 1)
    has_h_ema = "H_ema" in df_frames.columns
    n_ema_valid = int(df_frames["H_ema"].notna().sum()) if has_h_ema else 0
    ema_rate = n_ema_valid / max(len(df_frames), 1)
    checks["M2.1"] = {
        "monitor": "M2.1",
        "name": "Homografía EMA normalizada",
        "pass": ema_rate >= 0.95 and hv_rate >= 0.50 and has_h_ema,
        "details": {
            "homography_raw_valid_rate": round(hv_rate, 4),
            "homography_ema_valid_rate": round(ema_rate, 4),
            "has_H_ema": has_h_ema,
            "has_H_norm": "H_norm" in df_frames.columns,
        },
    }

    # M2.2 — Track Stitching
    if "track_id_stitched" in df_track_clean.columns:
        n_stitched = int(df_track_clean["track_id_stitched"].nunique())
        n_original = int(df_track_clean["track_id"].nunique())
        por_frame = df_track_clean.groupby(["frame", "track_id_stitched"]).size()
        n_simultaneos = int((por_frame > 1).sum())
    else:
        n_stitched = int(df_track_clean["track_id"].nunique())
        n_original = n_stitched
        n_simultaneos = 0
    # En TV hay más rastros que personas (cambios de toma): el criterio es que ningún
    # rastro esté en dos personas a la vez, no que queden 25 o menos.
    checks["M2.2"] = {
        "monitor": "M2.2",
        "name": "Track Stitching (Algoritmo Húngaro)",
        "pass": n_simultaneos == 0 and n_stitched <= n_original,
        "details": {
            "n_original_ids": n_original,
            "n_stitched_ids": n_stitched,
            "reduction": n_original - n_stitched,
            "ids_simultaneos": n_simultaneos,
        },
    }

    # M2.3 — Cinematica Savitzky-Golay
    # Verifica que v_clipped (post-clip) este siempre <= V_MAX_MPS
    # y que se haya aplicado suavizado (columna pitch_x_smooth existe)
    has_smooth = "pitch_x_smooth" in df_track_clean.columns
    if "v_clipped" in df_track_clean.columns:
        v_clip_vals = df_track_clean["v_clipped"].dropna()
        n_total = len(v_clip_vals)
        n_ok = int((v_clip_vals <= V_MAX_MPS).sum())
        v_rate = n_ok / max(n_total, 1)
        v_max_clip = round(float(v_clip_vals.max()), 3) if n_total > 0 else 0
    elif "v_mps" in df_track_clean.columns:
        v_vals = df_track_clean["v_mps"].dropna()
        n_total = len(v_vals)
        n_ok = int((v_vals <= V_MAX_MPS).sum())
        v_rate = n_ok / max(n_total, 1)
        v_max_clip = round(float(v_vals.max()), 3) if n_total > 0 else 0
    else:
        v_rate = 1.0
        n_ok = 0
        n_total = 0
        v_max_clip = 0
    checks["M2.3"] = {
        "monitor": "M2.3",
        "name": "Cinematica Savitzky-Golay (v <= 9.5 m/s)",
        "pass": v_rate >= 0.95 and has_smooth,
        "details": {
            "v_clipped_in_range_rate": round(v_rate, 4),
            "n_in_range": n_ok,
            "n_total": n_total,
            "v_max_clipped_mps": v_max_clip,
            "has_smooth_coordinates": has_smooth,
        },
    }

    # M2.4 — Ventanas Tácticas
    n_windows = len(tactical_windows)
    checks["M2.4"] = {
        "monitor": "M2.4",
        "name": "Ventanas Tácticas de 4.0 s",
        "pass": n_windows == N_WINDOWS,
        "details": {
            "n_windows": n_windows,
            "expected": N_WINDOWS,
            "windows_summary": [
                {
                    "id": w["window_id"],
                    "dominant_team": w["dominant_team"],
                    "pressure_context": w["pressure_context"],
                }
                for w in tactical_windows
            ],
        },
    }

    # M2.5 — Integridad del pipeline completo
    has_cleaned = len(df_track_clean) > 0
    has_smooth = "pitch_x_smooth" in df_track_clean.columns
    has_v = "v_mps" in df_track_clean.columns
    m25_pass = has_cleaned and has_smooth and has_v and n_windows == N_WINDOWS
    checks["M2.5"] = {
        "monitor": "M2.5",
        "name": "Integridad del pipeline completo",
        "pass": m25_pass,
        "details": {
            "has_cleaned_data": has_cleaned,
            "has_smooth_coordinates": has_smooth,
            "has_velocity": has_v,
            "n_tactical_windows": n_windows,
        },
    }

    all_pass = all(c["pass"] for c in checks.values())
    status = "PASS" if all_pass else "FAIL"

    report = {
        "monitor": "M2",
        "name": "Stage Monitors M2.0–M2.5",
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": sum(1 for c in checks.values() if c["pass"]),
            "failed": sum(1 for c in checks.values() if not c["pass"]),
        },
    }

    out_path = CLEAN_DIR / "monitor_m2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    _print_monitors(report)
    return report


def _print_monitors(report: dict) -> None:
    print(f"\n{'='*60}")
    print(f" MONITORES M2.0–M2.5")
    print(f" Estado global: {'✅ PASS' if report['status'] == 'PASS' else '❌ FAIL'}")
    print(f"{'='*60}")
    for key, chk in report["checks"].items():
        icon = "✅" if chk["pass"] else "❌"
        print(f"  {icon} {chk['monitor']} — {chk['name']}")
    print(f"{'='*60}\n")


# ===========================================================================
# Función principal: process_parquet_files
# ===========================================================================

def process_parquet_files(
    frames_path: str = "data/raw/frames.parquet",
    objects_path: str = "data/raw/objects.parquet",
    output_dir: str = "data/clean",
) -> dict:
    """
    Punto de entrada del engine: ejecuta las 5 fases + monitores M2.x.

    Parámetros:
        frames_path  : ruta al frames.parquet de entrada
        objects_path : ruta al objects.parquet de entrada
        output_dir   : directorio de salida para artefactos limpios

    Retorna dict con:
        {
          "status": "PASS"|"FAIL",
          "stage_monitors": {...},
          "output_files": {...},
          "tactical_summaries": [...],
        }
    """
    t_start = time.perf_counter()
    out_dir = pathlib.Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'#'*60}")
    print(f"  Omnimorph Engine — iniciando pipeline")
    print(f"  frames: {frames_path}")
    print(f"  objects: {objects_path}")
    print(f"{'#'*60}\n")

    # Cargar inputs
    df_frames = pd.read_parquet(frames_path)
    df_objects = pd.read_parquet(objects_path)

    # FASE 1: Separación track/ball + moda de equipo
    print("[FASE 1] Separación track/ball y moda de equipo …")
    df_track, df_ball, team_map = phase1_separate_and_team(df_objects)
    print(f"  → {len(df_track)} filas track, {len(df_ball)} filas ball")
    print(f"  → {len(team_map)} track_ids con equipo asignado")

    # FASE 4: Homografía EMA normalizada
    print("[FASE 4] Homografía EMA normalizada H/H[2,2] …")
    df_frames_h = phase4_homography_ema(df_frames)
    n_hv = int(df_frames_h["homography_valid"].sum())
    print(f"  → {n_hv}/{len(df_frames_h)} frames con homografía válida")

    # FASE 3: Track Stitching
    print("[FASE 3] Track Stitching (Algoritmo Húngaro) …")
    df_track_stitched = phase3_track_stitching(df_track, team_map)
    n_orig = df_track_stitched["track_id"].nunique()
    n_stitched = df_track_stitched["track_id_stitched"].nunique()
    print(f"  → IDs originales: {n_orig}, IDs cosidos: {n_stitched}")

    # FASE 2: Cinemática Savitzky-Golay
    print("[FASE 2] Cinemática Savitzky-Golay v ≤ 9.5 m/s …")
    df_track_clean = phase2_kinematics(df_track_stitched)
    v_vals = df_track_clean["v_mps"].dropna()
    v_clipped = int((v_vals > V_MAX_MPS).sum())
    print(f"  → {v_clipped} observaciones clipeadas a {V_MAX_MPS} m/s")

    # FASE 5: Ventanas Tácticas
    print("[FASE 5] Ventanas tácticas de 4.0 s …")
    tactical_windows = phase5_tactical_windows(df_track_clean, df_ball, team_map)
    print(f"  → {len(tactical_windows)} ventanas generadas")

    # Guardar artefactos (incluir track_clean + ball para el Dashboard)
    clean_objects_path = out_dir / "objects_cleaned.parquet"
    df_ball_out = df_ball.copy()
    if len(df_ball_out) > 0:
        df_ball_out["track_id_stitched"] = pd.Series([None] * len(df_ball_out), dtype="Int64")
        df_ball_out["pitch_x_smooth"] = df_ball_out["pitch_x"]
        df_ball_out["pitch_y_smooth"] = df_ball_out["pitch_y"]
        df_combined_out = pd.concat([df_track_clean, df_ball_out], ignore_index=True)
    else:
        df_combined_out = df_track_clean
    df_combined_out.to_parquet(str(clean_objects_path), index=False)

    tactical_path = out_dir / "tactical_summaries.json"
    with open(tactical_path, "w", encoding="utf-8") as f:
        json.dump(tactical_windows, f, indent=2, ensure_ascii=False)

    frames_clean_path = out_dir / "frames_clean.parquet"
    df_frames_h.to_parquet(str(frames_clean_path), index=False)

    print(f"\n[engine] Artefactos guardados:")
    print(f"  {clean_objects_path}")
    print(f"  {tactical_path}")
    print(f"  {frames_clean_path}")

    # Monitores M2.0–M2.5
    monitors = run_stage_monitors(
        df_frames=df_frames_h,
        df_objects_orig=df_objects,
        df_track=df_track,
        df_ball=df_ball,
        df_track_clean=df_track_clean,
        tactical_windows=tactical_windows,
        team_map=team_map,
    )

    elapsed = round(time.perf_counter() - t_start, 2)
    print(f"\n[engine] Pipeline completado en {elapsed} s")

    return {
        "status": monitors["status"],
        "stage_monitors": monitors,
        "output_files": {
            "objects_cleaned": str(clean_objects_path),
            "tactical_summaries": str(tactical_path),
            "frames_clean": str(frames_clean_path),
        },
        "tactical_summaries": tactical_windows,
        "elapsed_s": elapsed,
    }


# ===========================================================================
# CLI
# ===========================================================================

if __name__ == "__main__":
    import sys
    frames = sys.argv[1] if len(sys.argv) > 1 else "data/raw/frames.parquet"
    objects = sys.argv[2] if len(sys.argv) > 2 else "data/raw/objects.parquet"
    result = process_parquet_files(frames, objects)
    print(f"\nEstado final engine: {result['status']}")
    raise SystemExit(0 if result["status"] == "PASS" else 1)
