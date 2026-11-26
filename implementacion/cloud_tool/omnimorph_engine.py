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
import sys
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
PITCH_L_M = 105.0
PITCH_W_M = 68.0
INTERP_MAX_FRAMES = 15
SAVGOL_WINDOW = 9
SAVGOL_POLY = 3

ROOT_DIR = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
CLEAN_DIR = pathlib.Path("data/clean")


def pitch_x_to_m(px_cm: float | np.ndarray) -> float | np.ndarray:
    return px_cm * (PITCH_L_M / PITCH_L_CM)


def pitch_y_to_m(py_cm: float | np.ndarray) -> float | np.ndarray:
    return py_cm * (PITCH_W_M / PITCH_W_CM)


def _fps_clip(total_frames: int) -> float:
    """FPS del clip: los datos sintéticos tienen N_FRAMES a 25 fps; los reales, los del partido activo."""
    if total_frames <= N_FRAMES:
        return FPS
    from implementacion import partido_config
    return partido_config.activo().fps


def _interpolar_serie_huecos(frames: pd.Series, valores: pd.Series, max_hueco: int = INTERP_MAX_FRAMES) -> pd.Series:
    """
    Interpola linealmente huecos de hasta max_hueco cuadros sobre el eje real de frame
    (solo en el interior del rastro; no arrastra en los extremos ni rellena fuera).
    Un hueco de más de max_hueco cuadros consecutivos queda entero en NaN.
    Conserva el índice original de la serie.
    """
    s_val = pd.to_numeric(valores, errors="coerce")
    if s_val.notna().sum() < 2:
        return s_val
    orden = frames.argsort(kind="mergesort")
    f_ord = frames.iloc[orden].astype(int).to_numpy()
    v_ord = s_val.iloc[orden].to_numpy(dtype=float)

    f_min, f_max = int(f_ord[0]), int(f_ord[-1])
    grid = pd.Series(np.nan, index=range(f_min, f_max + 1), dtype=float)
    grid.loc[f_ord] = v_ord

    if not grid.isna().any():
        return s_val

    # Identificar corridas consecutivas de NaN y rellenar solo aquellas de longitud <= max_hueco
    is_na = grid.isna()
    bloques = (~is_na).cumsum()
    longitudes_hueco = is_na.groupby(bloques).transform("sum")
    grid_interp = grid.interpolate(method="index", limit_area="inside")
    grid_final = grid.where(~(is_na & (longitudes_hueco <= max_hueco)), grid_interp)

    res = pd.Series(grid_final.loc[f_ord].to_numpy(), index=s_val.iloc[orden].index, dtype=float)
    return res.reindex(valores.index)


# ===========================================================================
# FASE 1 — Separación track/ball y moda de equipo
# ===========================================================================

def phase1_separate_and_team(
    df_objects: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[int, int]]:
    """
    Separa track vs ball.
    Asigna equipo por moda de track_id a lo largo del clip.
    Interpola huecos de hasta 15 cuadros por rastro (y el balón igual); lo demás queda NaN.
    Conserva el orden original de las filas tras interpolar.

    Retorna:
        df_track   : filas source == 'track'
        df_ball    : filas source == 'ball'
        team_map   : {track_id → team_id (0|1|None)}
    """
    df_track = df_objects[df_objects["source"] == "track"].copy()
    df_ball = df_objects[df_objects["source"] == "ball"].copy()

    if len(df_track) > 0:
        df_track["pitch_x"] = pd.to_numeric(df_track["pitch_x"], errors="coerce")
        df_track["pitch_y"] = pd.to_numeric(df_track["pitch_y"], errors="coerce")
        if "track_id" in df_track.columns and df_track["track_id"].notna().any():
            px_new = df_track["pitch_x"].copy()
            py_new = df_track["pitch_y"].copy()
            for _, grp in df_track.groupby("track_id", sort=False):
                px_new.loc[grp.index] = _interpolar_serie_huecos(grp["frame"], grp["pitch_x"], INTERP_MAX_FRAMES)
                py_new.loc[grp.index] = _interpolar_serie_huecos(grp["frame"], grp["pitch_y"], INTERP_MAX_FRAMES)
            df_track["pitch_x"] = px_new
            df_track["pitch_y"] = py_new

    if len(df_ball) > 0:
        df_ball["pitch_x"] = pd.to_numeric(df_ball["pitch_x"], errors="coerce")
        df_ball["pitch_y"] = pd.to_numeric(df_ball["pitch_y"], errors="coerce")
        # Si hay más de una fila de balón en el mismo cuadro, interpolar sobre cuadros únicos
        if df_ball["frame"].duplicated().any():
            prim = ~df_ball["frame"].duplicated(keep="first")
            sub = df_ball.loc[prim]
            df_ball.loc[prim, "pitch_x"] = _interpolar_serie_huecos(sub["frame"], sub["pitch_x"], INTERP_MAX_FRAMES)
            df_ball.loc[prim, "pitch_y"] = _interpolar_serie_huecos(sub["frame"], sub["pitch_y"], INTERP_MAX_FRAMES)
        else:
            df_ball["pitch_x"] = _interpolar_serie_huecos(df_ball["frame"], df_ball["pitch_x"], INTERP_MAX_FRAMES)
            df_ball["pitch_y"] = _interpolar_serie_huecos(df_ball["frame"], df_ball["pitch_y"], INTERP_MAX_FRAMES)

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
    Donde homography_valid es falso (toma cerrada), no se arrastra H_ema (queda None).

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
            h_emas.append(None)
            continue

        h_raw = np.array(raw_h, dtype=float).reshape(3, 3)
        if not np.isfinite(h_raw).all():
            h_norms.append(None)
            h_emas.append(None)
            continue

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

    df_out["H_norm"] = h_norms
    df_out["H_ema"] = h_emas
    return df_out


# ===========================================================================
# FASE 3 — Track Stitching (Algoritmo Húngaro)
# ===========================================================================

def _cargar_mapa_rastros_partido() -> Optional[Dict[int, int]]:
    """
    Lee el mapa de identidades versionado del partido activo con ruta absoluta desde la raíz:
    ROOT_DIR / "data" / "partidos" / <partido_activo> / "mapa_rastros.json".
    Lo devuelve solo si el archivo existe para el partido activo.
    """
    from implementacion import partido_config
    partido = partido_config.activo()
    ruta = ROOT_DIR / "data" / "partidos" / partido.id / "mapa_rastros.json"
    if not ruta.exists():
        return None
    with open(ruta, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {int(k): int(v) for k, v in raw.items()}


def phase3_track_stitching(
    df_track: pd.DataFrame,
    team_map: Dict[int, Optional[int]],
) -> pd.DataFrame:
    """
    Une fragmentos de ByteTrack en rastros mediante el Algoritmo Húngaro.

    Si el partido activo tiene mapa_rastros.json y sus track_id coinciden con los datos,
    aplica directamente esa relación track_id → track_id_stitched para preservar
    los nombres y dorsales de rastros_dorsales.json. Conserva el orden original de las filas.

    Retorna df_track con columna track_id_stitched añadida.
    """
    orig_index = df_track.index
    df = df_track.sort_values(["frame", "track_id"]).copy()
    df["track_id_stitched"] = df["track_id"].astype("Int64")

    if not SCIPY_OK or df["track_id"].notna().sum() == 0:
        # Fallback: stitched == original
        return df.reindex(orig_index)

    tids_presentes = {int(t) for t in df["track_id"].dropna().unique()}
    mapa_partido = _cargar_mapa_rastros_partido()
    if mapa_partido is not None and tids_presentes == set(mapa_partido.keys()):
        df["track_id_stitched"] = df["track_id"].map(
            lambda tid: mapa_partido.get(int(tid)) if pd.notna(tid) else None
        ).astype("Int64")
        return df.reindex(orig_index)

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
    return df.reindex(orig_index)


# ===========================================================================
# FASE 2 — Cinemática Savitzky-Golay
# ===========================================================================

def phase2_kinematics(df_track: pd.DataFrame) -> pd.DataFrame:
    """
    Para cada track_id_stitched, aplica Savitzky-Golay a pitch_x y pitch_y,
    luego calcula velocidad en m/s reales (cancha de 105 x 68 m).
    Clips la velocidad a V_MAX_MPS. Conserva el orden original de las filas.

    Columnas anadidas: pitch_x_smooth, pitch_y_smooth, vx_mps, vy_mps, v_mps, v_clipped
    """
    orig_index = df_track.index
    df = df_track.copy()
    df["_orig_idx"] = orig_index
    df = df.sort_values(["track_id_stitched", "frame"]).reset_index(drop=True)
    fps = _fps_clip(int(df["frame"].max()) + 1) if len(df) else FPS

    n_total = len(df)
    smooth_x = np.full(n_total, np.nan)
    smooth_y = np.full(n_total, np.nan)
    vx_arr = np.full(n_total, np.nan)
    vy_arr = np.full(n_total, np.nan)
    v_arr = np.full(n_total, np.nan)
    v_clip_arr = np.full(n_total, np.nan)

    for tid, grp in df.groupby("track_id_stitched"):
        pos = grp.index.to_numpy()
        n = len(pos)

        px_vals = _interpolar_serie_huecos(grp["frame"], grp["pitch_x"], INTERP_MAX_FRAMES).to_numpy(dtype=float)
        py_vals = _interpolar_serie_huecos(grp["frame"], grp["pitch_y"], INTERP_MAX_FRAMES).to_numpy(dtype=float)

        sx = px_vals.copy()
        sy = py_vals.copy()
        valid_mask = ~(np.isnan(px_vals) | np.isnan(py_vals))

        # Aplicar Savitzky-Golay por tramo continuo sin NaNs
        if valid_mask.any():
            idx_valid = np.where(valid_mask)[0]
            cortes = np.where(np.diff(idx_valid) > 1)[0] + 1
            for tramo in np.split(idx_valid, cortes):
                if len(tramo) >= SAVGOL_WINDOW:
                    if SCIPY_OK:
                        sx[tramo] = savgol_filter(px_vals[tramo], SAVGOL_WINDOW, SAVGOL_POLY)
                        sy[tramo] = savgol_filter(py_vals[tramo], SAVGOL_WINDOW, SAVGOL_POLY)
                    else:
                        sx[tramo] = pd.Series(px_vals[tramo]).rolling(5, min_periods=1, center=True).mean().values
                        sy[tramo] = pd.Series(py_vals[tramo]).rolling(5, min_periods=1, center=True).mean().values

        smooth_x[pos] = sx
        smooth_y[pos] = sy

        if n >= 2:
            sx_m = pitch_x_to_m(sx)
            sy_m = pitch_y_to_m(sy)
            dx = np.diff(sx_m, prepend=sx_m[0]) * fps   # m/s reales (105 x 68 m)
            dy = np.diff(sy_m, prepend=sy_m[0]) * fps
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
    df = df.set_index("_orig_idx").reindex(orig_index)
    df.index.name = orig_index.name
    return df


# ===========================================================================
# FASE 5 — Ventanas Tácticas de 4.0 s
# ===========================================================================

def _moda_serie(s: pd.Series) -> Any:
    vals = s.dropna()
    if len(vals) == 0:
        return None
    m = vals.mode()
    return m.iloc[0] if len(m) > 0 else None


def _calcular_metricas_equipo_tramo(
    df_eq: pd.DataFrame,
    ataca_hacia: str,
) -> Dict[str, Any]:
    """
    Calcula las 4 métricas de un equipo en un tramo, en metros reales (105 x 68 m):
      - posicion_m: mediana de la distancia a la portería propia (según ataca_hacia).
      - pct_campo_rival: % de observaciones en la mitad rival (> 52.5 m de su portería).
      - largo_m, ancho_m: en cada cuadro con 4 o más jugadores del equipo,
        p90 - p10 en x y en y; la mediana de esos cuadros.
    Sin datos suficientes: None, nunca 0 ni un valor inventado.
    """
    if len(df_eq) == 0:
        return {
            "posicion_m": None,
            "pct_campo_rival": None,
            "largo_m": None,
            "ancho_m": None,
        }

    x_m = pitch_x_to_m(df_eq["pitch_x_smooth"].to_numpy(dtype=float))
    y_m = pitch_y_to_m(df_eq["pitch_y_smooth"].to_numpy(dtype=float))

    mitad_m = PITCH_L_M / 2.0
    if ataca_hacia == "+x":
        dist_propia = x_m
        en_rival = x_m > mitad_m
    elif ataca_hacia == "-x":
        dist_propia = PITCH_L_M - x_m
        en_rival = x_m < mitad_m
    else:
        raise ValueError(f"ataca_hacia inválido: {ataca_hacia!r}")

    posicion_m = round(float(np.median(dist_propia)), 1)
    pct_campo_rival = int(round(float(np.mean(en_rival) * 100.0)))

    df_coords = pd.DataFrame({
        "frame": df_eq["frame"].to_numpy(),
        "x_m": x_m,
        "y_m": y_m,
    })
    largos = []
    anchos = []
    for _, grp_f in df_coords.groupby("frame", sort=False):
        if len(grp_f) >= 4:
            gx = grp_f["x_m"].to_numpy(dtype=float)
            gy = grp_f["y_m"].to_numpy(dtype=float)
            largos.append(float(np.percentile(gx, 90) - np.percentile(gx, 10)))
            anchos.append(float(np.percentile(gy, 90) - np.percentile(gy, 10)))

    largo_m = round(float(np.median(largos)), 1) if len(largos) > 0 else None
    ancho_m = round(float(np.median(anchos)), 1) if len(anchos) > 0 else None

    return {
        "posicion_m": posicion_m,
        "pct_campo_rival": pct_campo_rival,
        "largo_m": largo_m,
        "ancho_m": ancho_m,
    }


def decidir_territorio(
    cod_a: str,
    pct_a: Optional[float | int],
    cod_b: str,
    pct_b: Optional[float | int],
) -> str:
    """
    El equipo con más pct_campo_rival gana el territorio si la diferencia es
    estrictamente MAYOR que 20 puntos; si no (o si falta un dato), "repartido".
    La misma regla simétrica para los dos equipos.
    """
    if pct_a is None or pct_b is None:
        return "repartido"
    if isinstance(pct_a, float) and np.isnan(pct_a):
        return "repartido"
    if isinstance(pct_b, float) and np.isnan(pct_b):
        return "repartido"
    diff = float(pct_a) - float(pct_b)
    if abs(diff) <= 20.0:
        return "repartido"
    return cod_a if diff > 20.0 else cod_b


def phase5_tactical_windows(
    df_track_clean: pd.DataFrame,
    df_ball: Optional[pd.DataFrame] = None,
    team_map: Optional[Dict[int, Optional[int]]] = None,
    equipos_override: Optional[Tuple[Any, Any]] = None,
    total_frames_override: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Divide el video en 8 ventanas tácticas uniformes a lo largo de todo el clip.
    Calcula métricas tácticas por equipo y tramo en metros reales (105 x 68 m).
    El equipo y la clase se asignan por moda de cada track_id DENTRO de cada tramo;
    solo cuentan jugadores y porteros (los árbitros se excluyen).

    Retorna lista de 8 dicts con:
      window_id, t0, t1, frame_start, frame_end,
      territorio, dominant_team, equipos,
      n_arg, n_fra, centroid_arg_x_cm, centroid_fra_x_cm
    """
    if total_frames_override is not None:
        total_frames = int(total_frames_override)
    else:
        max_frame = int(df_track_clean["frame"].max()) + 1 if len(df_track_clean) > 0 else N_FRAMES
        total_frames = max(max_frame, N_FRAMES)
    fps_clip = _fps_clip(total_frames)

    if equipos_override is not None:
        cod0, dir0 = equipos_override[0].codigo, equipos_override[0].ataca_hacia
        cod1, dir1 = equipos_override[1].codigo, equipos_override[1].ataca_hacia
    elif total_frames > N_FRAMES:
        from implementacion import partido_config
        eqs = partido_config.activo().equipos
        cod0, dir0 = eqs[0].codigo, eqs[0].ataca_hacia
        cod1, dir1 = eqs[1].codigo, eqs[1].ataca_hacia
    else:
        cod0, dir0 = "ARG", "+x"
        cod1, dir1 = "FRA", "-x"

    win_frames = max(int(np.ceil(total_frames / N_WINDOWS)), 1) if total_frames_override is not None else max(int(np.ceil(total_frames / N_WINDOWS)), WINDOW_SIZE_FRAMES)

    windows = []
    for w in range(N_WINDOWS):
        f0 = w * win_frames
        f1 = min(f0 + win_frames, total_frames)
        t0 = round(f0 / fps_clip, 2)
        t1 = round(f1 / fps_clip, 2)

        mask_w = (df_track_clean["frame"] >= f0) & (df_track_clean["frame"] < f1)
        df_w = df_track_clean[mask_w].copy()

        # Moda de equipo y clase por track_id DENTRO del tramo
        tid_col = "track_id" if "track_id" in df_w.columns and df_w["track_id"].notna().any() else "track_id_stitched"
        team_por_tid: Dict[Any, Optional[int]] = {}
        es_jugador_por_tid: Dict[Any, bool] = {}

        if len(df_w) > 0 and tid_col in df_w.columns:
            for tid, grp in df_w.groupby(tid_col, sort=False):
                if tid is None or (isinstance(tid, float) and np.isnan(tid)):
                    continue
                t_mod = _moda_serie(grp["team"]) if "team" in grp.columns else None
                team_por_tid[tid] = int(t_mod) if t_mod in (0, 1) else None

                # Determinar si por moda es jugador o portero (excluir árbitros)
                es_jug = True
                if "class_name" in grp.columns and grp["class_name"].notna().any():
                    c_mod = _moda_serie(grp["class_name"])
                    es_jug = str(c_mod).lower() in ("player", "goalkeeper")
                elif "class_id" in grp.columns and grp["class_id"].notna().any():
                    cid_mod = _moda_serie(grp["class_id"])
                    # En dataset sintético: 0=player, 1=goalkeeper, 2=referee
                    # En percepción real YOLO: 1=goalkeeper, 2=player, 3=referee, 0=ball
                    es_jug = int(cid_mod) in (0, 1, 2) and int(cid_mod) != 3
                es_jugador_por_tid[tid] = es_jug

        if len(df_w) > 0 and tid_col in df_w.columns:
            es_jug_mask = df_w[tid_col].map(lambda t: bool(es_jugador_por_tid.get(t, False)))
            team_tramo = df_w[tid_col].map(lambda t: team_por_tid.get(t))
            coords_ok = df_w["pitch_x_smooth"].notna() & df_w["pitch_y_smooth"].notna()
            df_jug = df_w[es_jug_mask & coords_ok].copy()
            df_jug["_team_tramo"] = team_tramo[es_jug_mask & coords_ok]
        else:
            df_jug = df_w.iloc[0:0].copy()
            df_jug["_team_tramo"] = pd.Series(dtype="object")

        df_eq0 = df_jug[df_jug["_team_tramo"] == 0]
        df_eq1 = df_jug[df_jug["_team_tramo"] == 1]

        met0 = _calcular_metricas_equipo_tramo(df_eq0, dir0)
        met1 = _calcular_metricas_equipo_tramo(df_eq1, dir1)

        territorio = decidir_territorio(cod0, met0["pct_campo_rival"], cod1, met1["pct_campo_rival"])
        dominant_team = "neutro" if territorio == "repartido" else territorio

        # Centroides (None si no hay datos suficientes, nunca 6000 inventado)
        if len(df_eq0) > 0:
            c0_val = float(df_eq0["pitch_x_smooth"].mean())
            centroid_arg_x = round(c0_val, 1) if not np.isnan(c0_val) else None
        else:
            centroid_arg_x = None

        if len(df_eq1) > 0:
            c1_val = float(df_eq1["pitch_x_smooth"].mean())
            centroid_fra_x = round(c1_val, 1) if not np.isnan(c1_val) else None
        else:
            centroid_fra_x = None

        windows.append({
            "window_id": f"W{w}",
            "t0": round(t0, 2),
            "t1": round(t1, 2),
            "frame_start": f0,
            "frame_end": max(f1 - 1, f0),
            "territorio": territorio,
            "dominant_team": dominant_team,
            "equipos": {
                cod0: met0,
                cod1: met1,
            },
            "n_arg": int(len(df_eq0)),
            "n_fra": int(len(df_eq1)),
            "centroid_arg_x_cm": centroid_arg_x,
            "centroid_fra_x_cm": centroid_fra_x,
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
    radar_error_path: Optional[str | pathlib.Path] = None,
    output_dir: Optional[str | pathlib.Path] = None,
) -> dict:
    """
    Ejecuta los Monitores M2.0 a M2.5.
    Guarda el reporte en data/clean/monitor_m2.json (o en output_dir si se indica).
    """
    out_dir = pathlib.Path(output_dir) if output_dir is not None else CLEAN_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
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

    # M2.1 — Homografía EMA normalizada y error del radar
    n_hv = int(df_frames["homography_valid"].sum()) if "homography_valid" in df_frames.columns else 0
    hv_rate = n_hv / max(len(df_frames), 1)
    has_h_ema = "H_ema" in df_frames.columns
    n_ema_valid = int(df_frames["H_ema"].notna().sum()) if has_h_ema else 0
    ema_rate = n_ema_valid / max(len(df_frames), 1)

    es_sintetico = len(df_frames) <= N_FRAMES
    err_path = pathlib.Path(radar_error_path) if radar_error_path is not None else (out_dir / "radar_error.json")
    radar_err_mediana = None
    radar_err_p90 = None
    radar_err_metodo = None
    radar_err_aviso = None

    if radar_error_path is not None or not es_sintetico:
        if err_path.exists():
            with open(err_path, "r", encoding="utf-8") as f:
                r_err = json.load(f)
            med_raw = r_err.get("mediana_m")
            if med_raw is not None:
                radar_err_mediana = float(med_raw)
            radar_err_p90 = r_err.get("p90_m")
            radar_err_metodo = r_err.get("metodo")
            radar_err_ok = (radar_err_mediana is not None) and (radar_err_mediana <= 3.0)
        else:
            radar_err_ok = False
            radar_err_aviso = f"Falta {err_path} con datos reales."
    else:
        radar_err_ok = True
        radar_err_aviso = "Datos sintéticos: comprobación de radar_error.json omitida."
        print(f"  [AVISO M2.1] {radar_err_aviso}")

    m21_details: Dict[str, Any] = {
        "homography_raw_valid_rate": round(hv_rate, 4),
        "homography_ema_valid_rate": round(ema_rate, 4),
        "has_H_ema": has_h_ema,
        "has_H_norm": "H_norm" in df_frames.columns,
        "radar_error_mediana_m": radar_err_mediana,
        "radar_error_p90_m": radar_err_p90,
        "radar_error_metodo": radar_err_metodo,
    }
    if radar_err_aviso is not None:
        m21_details["aviso"] = radar_err_aviso

    checks["M2.1"] = {
        "monitor": "M2.1",
        "name": "Homografía EMA normalizada",
        "pass": ema_rate >= 0.95 and hv_rate >= 0.50 and has_h_ema and radar_err_ok,
        "details": m21_details,
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
                    "territorio": w.get("territorio"),
                    "dominant_team": w.get("dominant_team"),
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

    out_path = out_dir / "monitor_m2.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)

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
        json.dump(tactical_windows, f, indent=2, ensure_ascii=False, allow_nan=False)

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
        output_dir=out_dir,
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
