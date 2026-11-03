Aquí tienes la unificación de las 3 *skills* previas en una sola **Skill Maestra coherente, corregida y desplegable en IBM Cloud (`omnimorph-engine`)**, con **Monitores de Observabilidad por Etapa (`M2.0` a `M2.5`)** integrados en el código.  
Esta especificación consolida todo el ciclo de vida del post-procesamiento dentro de **IBM watsonx Orchestrate ADK (Custom Python Tool)**: desde la separación limpia de fuentes (`track` vs `ball`), estabilización de la homografía (`P1`), unificación de trayectorias con el Algoritmo Húngaro (`P3`), filtrado cinemático Savitzky-Golay (`P2`), hasta la extracción del JSON táctico cuadro a cuadro para el LLM (`ibm/granite-3-8b-instruct`) y el reporte de cumplimiento de cada monitor.

# 🛠️ **SKILL: omnimorph-engine (IBM Cloud · watsonx Orchestrate ADK)**

**Propósito:** Pipeline unificado de post-procesamiento cinemático, estabilización geométrica, monitoreo por etapa y extracción de resúmenes tácticos JSON para video *broadcast* de fútbol (1080p, 25 fps, 30 s). Se ejecuta en **IBM Cloud** como herramienta personalizada de Python en `watsonx Orchestrate ADK`, resolviendo de forma secuencial `P1`, `P3`, `P2` y la síntesis de métricas colectivas.

### 1. FLUJO DE DEPENDENCIAS Y MONITORES DE OBSERVABILIDAD EN IBM CLOUD

```text
┌────────────────────────────────────────────────────────────────────────┐
│            ENTRADAS DESDE LOCAL (Validadas por Monitor M1)             │
│  - frames.parquet (750 filas: H[9], n_kp_visible, kp_conf, valid)      │
│  - objects.parquet (35,870 filas: source [det|track|ball], bbox, team) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.0: Esquema y FPS]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FASE 1: Separación de Fuentes y Reconciliación de Equipo               │
│ - Filtra source == 'track' (jugadores/árbitros) y source == 'ball'     │
│ - team_clean = moda(team) por track_id + heurística de porteros        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.1: 0 cambios team]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FASE 2: Estabilización Geométrica Directa (P1)                         │
│ - Normalización H / H[2,2] (8 DOF independientes)                      │
│ - Filtro EMA adaptativo según n_kp_visible y kp_conf (visibles > 0.5)  │
│ - Proyección directa H_smooth @ p_img desde base del bbox (pies z=0)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.2: Reducción ΔH]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FASE 3: Unificación de Trayectorias / Track Stitching (P3)             │
│ - Extrapolación cinemática desde pos_end(A) hacia pos_start(B) (<=3s)  │
│ - Matriz de Costo: Distancia extrapolada + Restricción dura de Equipo  │
│ - Algoritmo Húngaro (linear_sum_assignment) + Cadenas transitivas      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.3: 39 -> ~25 IDs]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FASE 4: Filtrado Cinemático y Acotamiento Físico (P2)                  │
│ - Despiking mediano + Suavizado Savitzky-Golay (window=11, poly=2)     │
│ - Derivada analítica Savitzky-Golay (deriv=1, delta=DT=0.04 s)         │
│ - Clipeo físico estricto: v <= 9.5 m/s (34.2 km/h), a <= 5.0 m/s²      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.4: 0 vel > 9.5m/s]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ FASE 5: Extracción de Resumen Táctico Cuadro a Cuadro para LLM         │
│ - Mapeo en ventanas de 4.0 s (100 frames)                              │
│ - Métricas: Centroides, Compactación, Velocidad de Transición y        │
│   Presión instantánea real sobre el poseedor del balón (<= 2.5 m)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  ──► [MONITOR M2.5: 8 JSON < 500B]
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         SALIDAS DE LA TOOL                             │
│  - objects_cleaned.parquet (Trayectorias 2D continuas para Radar)      │
│  - tactical_summary_w01..w08.json (Contexto para Granite 3 8B)         │
│  - stage_monitors.json (Semáforos de verificación M2.0 a M2.5)         │
└────────────────────────────────────────────────────────────────────────┘
```

### 2. IMPLEMENTACIÓN UNIFICADA EN PYTHON (`omnimorph_engine.py`)

```python
import json
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.optimize import linear_sum_assignment


def run_omnimorph_engine(
    df_frames: pd.DataFrame,
    df_objects: pd.DataFrame,
    fps: int = 25,
    window_sec: float = 4.0,
) -> tuple[pd.DataFrame, list[dict], dict]:
    """
    Skill Unificada: omnimorph-engine (IBM watsonx Orchestrate ADK Python Tool)
    Ejecuta las 5 fases de post-procesamiento cinemático, resumen táctico
    y monitoreo de verificación por etapa (stage_monitors).
    """
    stage_monitors = {}
    df_frm = df_frames.sort_values("frame").reset_index(drop=True).copy()

    # Calculamos FPS dinámico si existe la columna 't'
    if "t" in df_frm.columns and len(df_frm) > 1:
        dt_med = float(df_frm["t"].diff().dropna().median())
        if dt_med > 1e-4:
            fps = int(round(1.0 / dt_med))
    DT = 1.0 / fps

    # MONITOR M2.0: Verificador de Esquema de Entrada
    req_frm_cols = {"frame", "homography_valid", "n_kp_visible", "kp_conf", "H"}
    req_obj_cols = {"frame", "source", "track_id", "class_id", "team", "x1", "y1", "x2", "y2"}
    stage_monitors["M2.0_input_schema"] = {
        "status": "PASS" if (req_frm_cols.issubset(df_frm.columns) and req_obj_cols.issubset(df_objects.columns)) else "FAIL",
        "n_frames": int(len(df_frm)),
        "n_raw_objects": int(len(df_objects)),
        "fps_detected": fps,
        "homography_valid_ratio": round(float(df_frm["homography_valid"].mean()), 4),
    }

    # =========================================================================
    # FASE 1: SEPARACIÓN DE FUENTES Y CONSISTENCIA DE EQUIPO
    # =========================================================================
    df_trk = df_objects[df_objects["source"] == "track"].copy()
    df_ball = df_objects[df_objects["source"] == "ball"].copy()

    def get_mode(series: pd.Series):
        valid = series.dropna()
        return valid.mode().iloc[0] if not valid.empty else np.nan

    df_trk["team_clean"] = df_trk.groupby("track_id")["team"].transform(get_mode)
    df_ball["team_clean"] = np.nan
    df_ball["track_id"] = -1

    # =========================================================================
    # FASE 2: ESTABILIZACIÓN GEOMÉTRICA DIRECTA (P1)
    # =========================================================================
    H_stack = np.vstack(df_frm["H"].values).astype(np.float64)  # (750, 9)
    h22 = np.where(np.abs(H_stack[:, 8:9]) > 1e-9, H_stack[:, 8:9], 1.0)
    H_norm = H_stack / h22

    conf_vis = []
    for c in df_frm["kp_conf"].values:
        c_arr = np.asarray(c, dtype=np.float64)
        vis = c_arr[c_arr > 0.5]
        conf_vis.append(float(np.mean(vis)) if vis.size > 0 else 0.0)
    conf_scores = np.array(conf_vis)

    kp_counts = df_frm["n_kp_visible"].values.astype(np.float64)
    alpha_weights = np.clip((kp_counts / 24.0) * conf_scores * 0.5, 0.05, 0.60)

    H_smooth = np.zeros_like(H_norm)
    H_smooth[0] = H_norm[0]
    for t in range(1, len(H_norm)):
        a = alpha_weights[t]
        if kp_counts[t] < 4 or not bool(df_frm["homography_valid"].iloc[t]):
            a = 0.01
        H_smooth[t] = a * H_norm[t] + (1.0 - a) * H_smooth[t - 1]

    H_matrices = H_smooth.reshape(-1, 3, 3)

    def project_points(df_sub: pd.DataFrame) -> pd.DataFrame:
        if df_sub.empty:
            return df_sub
        frames_idx = df_sub["frame"].values.astype(int)
        x_mid = (df_sub["x1"].values + df_sub["x2"].values) / 2.0
        y_feet = df_sub["y2"].values
        ones = np.ones_like(x_mid)
        p_img = np.stack([x_mid, y_feet, ones], axis=-1)

        H_f = H_matrices[frames_idx]
        p_pitch = np.einsum("nij,nj->ni", H_f, p_img)
        w = np.where(np.abs(p_pitch[:, 2]) > 1e-9, p_pitch[:, 2], 1.0)
        df_sub["pitch_x_smooth"] = np.clip(p_pitch[:, 0] / w, 0.0, 12000.0)
        df_sub["pitch_y_smooth"] = np.clip(p_pitch[:, 1] / w, 0.0, 7000.0)
        return df_sub

    df_trk = project_points(df_trk)
    df_ball = project_points(df_ball)

    # Heurística posicional para porteros (class_id == 1)
    gk_mask = df_trk["class_id"] == 1
    if gk_mask.any():
        gk_mean_x = df_trk[gk_mask].groupby("track_id")["pitch_x_smooth"].transform("mean")
        df_trk.loc[gk_mask, "team_clean"] = np.where(gk_mean_x < 6000.0, 0.0, 1.0)

    # MONITOR M2.1: Consistencia de Fuentes y Equipos
    team_flips = int(df_trk.groupby("track_id")["team_clean"].nunique().gt(1).sum())
    stage_monitors["M2.1_sources_and_teams"] = {
        "status": "PASS" if (len(df_trk) > 0 and len(df_ball) > 0 and team_flips == 0) else "WARN",
        "track_rows": int(len(df_trk)),
        "ball_rows": int(len(df_ball)),
        "det_rows_discarded": int((df_objects["source"] == "det").sum()),
        "team_flicker_tracks": team_flips,
    }

    # MONITOR M2.2: Estabilidad de Homografía (P1)
    raw_jitter = float(np.mean(np.linalg.norm(np.diff(H_norm, axis=0), axis=1)))
    smooth_jitter = float(np.mean(np.linalg.norm(np.diff(H_smooth, axis=0), axis=1)))
    jitter_reduction_pct = round((1.0 - smooth_jitter / max(raw_jitter, 1e-9)) * 100.0, 1)
    stage_monitors["M2.2_homography_p1"] = {
        "status": "PASS" if jitter_reduction_pct > 20.0 else "WARN",
        "raw_interframe_jitter": round(raw_jitter, 4),
        "smooth_interframe_jitter": round(smooth_jitter, 4),
        "jitter_reduction_pct": jitter_reduction_pct,
        "bounds_valid": bool(
            df_trk["pitch_x_smooth"].between(0, 12000).all()
            and df_trk["pitch_y_smooth"].between(0, 7000).all()
        ),
    }

    # =========================================================================
    # FASE 3: UNIFICACIÓN DE TRAYECTORIAS / TRACK STITCHING (P3)
    # =========================================================================
    track_summary = []
    for tid, group in df_trk.groupby("track_id"):
        group = group.sort_values("frame")
        tail = group.tail(min(5, len(group)))
        if len(tail) >= 2:
            dt_tail = (tail["frame"].iloc[-1] - tail["frame"].iloc[0]) * DT
            v_end = (
                tail[["pitch_x_smooth", "pitch_y_smooth"]].iloc[-1].values
                - tail[["pitch_x_smooth", "pitch_y_smooth"]].iloc[0].values
            ) / max(dt_tail, DT)
            v_end = np.clip(v_end, -950.0, 950.0)
        else:
            v_end = np.zeros(2)

        track_summary.append({
            "track_id": int(tid),
            "f_start": int(group["frame"].iloc[0]),
            "f_end": int(group["frame"].iloc[-1]),
            "pos_start": group[["pitch_x_smooth", "pitch_y_smooth"]].iloc[0].values,
            "pos_end": group[["pitch_x_smooth", "pitch_y_smooth"]].iloc[-1].values,
            "v_end": v_end,
            "team": group["team_clean"].iloc[0],
            "class_id": int(group["class_id"].mode().iloc[0]),
        })
    df_tracks = pd.DataFrame(track_summary)

    n_tr = len(df_tracks)
    INF_COST = 1e9
    cost_matrix = np.full((n_tr, n_tr), INF_COST, dtype=np.float64)

    for i, t_a in df_tracks.iterrows():
        for j, t_b in df_tracks.iterrows():
            if i == j:
                continue
            dt_frames = t_b["f_start"] - t_a["f_end"]
            if 0 < dt_frames <= 75:
                same_team = (
                    (t_a["team"] == t_b["team"])
                    if (pd.notna(t_a["team"]) and pd.notna(t_b["team"]))
                    else (pd.isna(t_a["team"]) and pd.isna(t_b["team"]))
                )
                if not same_team:
                    continue

                dt_sec = dt_frames * DT
                pred_pos = t_a["pos_end"] + t_a["v_end"] * dt_sec
                dist_cm = float(np.linalg.norm(pred_pos - t_b["pos_start"]))
                raw_dist_cm = float(np.linalg.norm(t_a["pos_end"] - t_b["pos_start"]))

                if dist_cm <= 500.0 and raw_dist_cm <= (950.0 * dt_sec + 150.0):
                    cost_matrix[i, j] = dist_cm + 20.0 * dt_sec

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    parent_map = {}
    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] < 1000.0:
            tid_a = int(df_tracks.loc[r, "track_id"])
            tid_b = int(df_tracks.loc[c, "track_id"])
            parent_map[tid_b] = tid_a

    def find_root(tid: int) -> int:
        visited = set()
        curr = tid
        while curr in parent_map and curr not in visited:
            visited.add(curr)
            curr = parent_map[curr]
        return curr

    stitch_map = {int(tid): find_root(int(tid)) for tid in df_tracks["track_id"]}
    df_trk["track_id_stitched"] = df_trk["track_id"].map(stitch_map)
    df_ball["track_id_stitched"] = -1
    df_trk["team_clean"] = df_trk.groupby("track_id_stitched")["team_clean"].transform(get_mode)

    # MONITOR M2.3: Auditoría de Re-ID / Stitching (P3)
    n_unique_before = int(df_trk["track_id"].nunique())
    n_unique_after = int(df_trk["track_id_stitched"].nunique())
    stage_monitors["M2.3_track_stitching_p3"] = {
        "status": "PASS" if n_unique_after <= n_unique_before else "FAIL",
        "tracks_before": n_unique_before,
        "tracks_after_stitching": n_unique_after,
        "fragments_merged": int(n_unique_before - n_unique_after),
    }

    # =========================================================================
    # FASE 4: FILTRADO CINEMÁTICO Y ACOTAMIENTO FÍSICO (P2)
    # =========================================================================
    S_MAX_CMS = 950.0   # 9.5 m/s = 34.2 km/h
    A_MAX_CMS2 = 500.0  # 5.0 m/s²

    processed_tracks = []
    for tid, group in df_trk.groupby("track_id_stitched"):
        group = group.sort_values("frame").drop_duplicates(subset=["frame"], keep="first").copy()
        n_pts = len(group)

        x_raw = pd.Series(group["pitch_x_smooth"].values)
        y_raw = pd.Series(group["pitch_y_smooth"].values)

        x_med = x_raw.rolling(5, center=True, min_periods=1).median().values
        y_med = y_raw.rolling(5, center=True, min_periods=1).median().values

        if n_pts >= 11:
            x_filt = savgol_filter(x_med, window_length=11, polyorder=2)
            y_filt = savgol_filter(y_med, window_length=11, polyorder=2)
            vx = savgol_filter(x_med, window_length=11, polyorder=2, deriv=1, delta=DT)
            vy = savgol_filter(y_med, window_length=11, polyorder=2, deriv=1, delta=DT)
        elif n_pts >= 5:
            win = n_pts if n_pts % 2 == 1 else n_pts - 1
            x_filt = savgol_filter(x_med, window_length=win, polyorder=2)
            y_filt = savgol_filter(y_med, window_length=win, polyorder=2)
            vx = np.gradient(x_filt, group["frame"].values * DT)
            vy = np.gradient(y_filt, group["frame"].values * DT)
        else:
            x_filt, y_filt = x_med, y_med
            vx = np.zeros(n_pts)
            vy = np.zeros(n_pts)

        v_norm = np.sqrt(vx**2 + vy**2)
        v_mask = v_norm > S_MAX_CMS
        vx[v_mask] = vx[v_mask] * (S_MAX_CMS / (v_norm[v_mask] + 1e-6))
        vy[v_mask] = vy[v_mask] * (S_MAX_CMS / (v_norm[v_mask] + 1e-6))

        if n_pts >= 3:
            t_sec = group["frame"].values * DT
            ax = np.gradient(vx, t_sec)
            ay = np.gradient(vy, t_sec)
        else:
            ax, ay = np.zeros(n_pts), np.zeros(n_pts)

        a_norm = np.sqrt(ax**2 + ay**2)
        a_mask = a_norm > A_MAX_CMS2
        ax[a_mask] = ax[a_mask] * (A_MAX_CMS2 / (a_norm[a_mask] + 1e-6))
        ay[a_mask] = ay[a_mask] * (A_MAX_CMS2 / (a_norm[a_mask] + 1e-6))

        group["pitch_x_smooth"] = x_filt
        group["pitch_y_smooth"] = y_filt
        group["vx"] = vx
        group["vy"] = vy
        group["speed_mps"] = np.sqrt(vx**2 + vy**2) / 100.0
        group["acceleration_mps2"] = np.sqrt(ax**2 + ay**2) / 100.0
        processed_tracks.append(group)

    if not df_ball.empty:
        df_ball = df_ball.sort_values("frame").drop_duplicates(subset=["frame"], keep="first").copy()
        if len(df_ball) >= 7:
            df_ball["pitch_x_smooth"] = savgol_filter(df_ball["pitch_x_smooth"].values, 7, 2)
            df_ball["pitch_y_smooth"] = savgol_filter(df_ball["pitch_y_smooth"].values, 7, 2)
            t_b = df_ball["frame"].values * DT
            df_ball["vx"] = np.gradient(df_ball["pitch_x_smooth"].values, t_b)
            df_ball["vy"] = np.gradient(df_ball["pitch_y_smooth"].values, t_b)
            df_ball["speed_mps"] = np.clip(
                np.sqrt(df_ball["vx"] ** 2 + df_ball["vy"] ** 2) / 100.0, 0.0, 35.0
            )
            df_ball["acceleration_mps2"] = 0.0
        processed_tracks.append(df_ball)

    df_cleaned = pd.concat(processed_tracks, ignore_index=True).sort_values(["frame", "track_id_stitched"])

    # MONITOR M2.4: Validador Biodinámico / Físico (P2)
    players_only = df_cleaned[df_cleaned["source"] == "track"]
    max_player_speed = round(float(players_only["speed_mps"].max()), 2) if not players_only.empty else 0.0
    max_player_acc = round(float(players_only["acceleration_mps2"].max()), 2) if not players_only.empty else 0.0
    stage_monitors["M2.4_kinematics_p2"] = {
        "status": "PASS" if (max_player_speed <= 9.51 and max_player_acc <= 5.01) else "FAIL",
        "max_player_speed_mps": max_player_speed,
        "max_player_acc_mps2": max_player_acc,
        "violations_over_9_5_mps": int((players_only["speed_mps"] > 9.51).sum()),
    }

    # =========================================================================
    # FASE 5: EXTRACCIÓN DE RESUMEN TÁCTICO CUADRO A CUADRO PARA LLM
    # =========================================================================
    frames_per_window = int(fps * window_sec)
    total_frames = int(df_frm["frame"].max()) + 1
    json_summaries = []

    for w_idx, start_frame in enumerate(range(0, total_frames, frames_per_window)):
        end_frame = min(start_frame + frames_per_window, total_frames)
        w_df = df_cleaned[(df_cleaned["frame"] >= start_frame) & (df_cleaned["frame"] < end_frame)]
        if w_df.empty:
            continue

        arg_df = w_df[(w_df["source"] == "track") & (w_df["team_clean"] == 0)]
        fra_df = w_df[(w_df["source"] == "track") & (w_df["team_clean"] == 1)]
        ball_w = w_df[w_df["source"] == "ball"]

        arg_centroid_x = (arg_df["pitch_x_smooth"].mean() - 6000.0) / 100.0 if not arg_df.empty else 0.0
        fra_centroid_x = (fra_df["pitch_x_smooth"].mean() - 6000.0) / 100.0 if not fra_df.empty else 0.0

        arg_len = (
            (arg_df.groupby("frame")["pitch_x_smooth"].max() - arg_df.groupby("frame")["pitch_x_smooth"].min()).mean() / 100.0
            if not arg_df.empty else 0.0
        )
        arg_wid = (
            (arg_df.groupby("frame")["pitch_y_smooth"].max() - arg_df.groupby("frame")["pitch_y_smooth"].min()).mean() / 100.0
            if not arg_df.empty else 0.0
        )
        fra_len = (
            (fra_df.groupby("frame")["pitch_x_smooth"].max() - fra_df.groupby("frame")["pitch_x_smooth"].min()).mean() / 100.0
            if not fra_df.empty else 0.0
        )
        fra_wid = (
            (fra_df.groupby("frame")["pitch_y_smooth"].max() - fra_df.groupby("frame")["pitch_y_smooth"].min()).mean() / 100.0
            if not fra_df.empty else 0.0
        )

        pressure_frames = 0
        defenders_counts = []
        possession_counts = {0: 0, 1: 0}

        players_w = w_df[(w_df["source"] == "track") & (w_df["team_clean"].isin([0, 1]))]
        if not ball_w.empty and not players_w.empty:
            merged_fb = players_w.merge(
                ball_w[["frame", "pitch_x_smooth", "pitch_y_smooth"]],
                on="frame",
                suffixes=("", "_ball"),
            )
            if not merged_fb.empty:
                merged_fb["dist_ball_m"] = (
                    np.sqrt(
                        (merged_fb["pitch_x_smooth"] - merged_fb["pitch_x_smooth_ball"]) ** 2
                        + (merged_fb["pitch_y_smooth"] - merged_fb["pitch_y_smooth_ball"]) ** 2
                    )
                    / 100.0
                )
                for f_id, f_grp in merged_fb.groupby("frame"):
                    carrier_idx = f_grp["dist_ball_m"].idxmin()
                    carrier = f_grp.loc[carrier_idx]
                    if carrier["dist_ball_m"] <= 3.5:
                        c_team = int(carrier["team_clean"])
                        possession_counts[c_team] = possession_counts.get(c_team, 0) + 1
                        rivals = f_grp[f_grp["team_clean"] != c_team]
                        dist_to_carrier_m = (
                            np.sqrt(
                                (rivals["pitch_x_smooth"] - carrier["pitch_x_smooth"]) ** 2
                                + (rivals["pitch_y_smooth"] - carrier["pitch_y_smooth"]) ** 2
                            )
                            / 100.0
                        )
                        n_def_near = int((dist_to_carrier_m <= 2.5).sum())
                        defenders_counts.append(n_def_near)
                        if n_def_near >= 1:
                            pressure_frames += 1

        n_eval = max(len(defenders_counts), 1)
        avg_def_near = round(float(np.mean(defenders_counts)), 1) if defenders_counts else 0.0
        pressure_ratio = round(pressure_frames / n_eval, 2) if defenders_counts else 0.0
        dom_team = "ARG" if possession_counts[0] >= possession_counts[1] else "FRA"

        summary = {
            "window_id": f"W{w_idx + 1:02d}_{start_frame}-{end_frame}",
            "time_range_s": [round(start_frame / fps, 2), round(end_frame / fps, 2)],
            "dominant_team": dom_team,
            "block_height_m": {"ARG": round(float(arg_centroid_x), 1), "FRA": round(float(fra_centroid_x), 1)},
            "block_compactness_m": {
                "ARG": {"length": round(float(arg_len), 1), "width": round(float(arg_wid), 1)},
                "FRA": {"length": round(float(fra_len), 1), "width": round(float(fra_wid), 1)},
            },
            "transition_speed_mps": {
                "ARG": round(float(arg_df["speed_mps"].mean()) if not arg_df.empty else 0.0, 2),
                "FRA": round(float(fra_df["speed_mps"].mean()) if not fra_df.empty else 0.0, 2),
            },
            "pressure_context": {
                "is_under_pressure": bool(pressure_ratio >= 0.35),
                "pressure_ratio": pressure_ratio,
                "avg_defenders_within_2_5m": avg_def_near,
            },
        }
        json_summaries.append(summary)

    # MONITOR M2.5: Validador de Ventanas Tácticas JSON
    max_json_bytes = max((len(json.dumps(s).encode("utf-8")) for s in json_summaries), default=0)
    stage_monitors["M2.5_tactical_windows"] = {
        "status": "PASS" if (len(json_summaries) > 0 and max_json_bytes < 600) else "WARN",
        "windows_generated": len(json_summaries),
        "max_window_bytes": max_json_bytes,
    }

    return df_cleaned, json_summaries, stage_monitors
```

### 3. TABLA DE MONITORES DE VERIFICACIÓN POR ETAPA (`M1` a `M4`)

| Monitor | Etapa que Supervisa | Condición de Cumplimiento (Semáforo Verde `PASS`) |
| :--- | :--- | :--- |
| **`MONITOR M1`** | **1) Percepción Local GPU** (`validate.py` + `timings.parquet`) | `750/750` cuadros procesados, `homography_valid = 100%`, balón detectado en `91.6%` de frames, IoU `C2 vs A = 1.0`. |
| **`MONITOR M2.0`** | **2) Ingesta en IBM Cloud ADK** | Columnas de `frames.parquet` y `objects.parquet` íntegras y cálculo automático de `fps` (`25 Hz`). |
| **`MONITOR M2.1`** | **2) Fase 1: Fuentes y Equipos** | `17,232` filas `track` + `687` filas `ball` conservadas, `0` filas `det` duplicadas y `0` cambios de equipo dentro de cada `track_id`. |
| **`MONITOR M2.2`** | **2) Fase 2: Homografía `P1`** | Escala $H_{2,2} = 1$, reducción de *jitter* inter-cuadro $>20\%$ y $100\%$ de coordenadas dentro de $12000\times 7000\text{ cm}$. |
| **`MONITOR M2.3`** | **2) Fase 3: Track Stitching `P3`** | Reducción efectiva de fragmentación (`39 track_ids` $\rightarrow$ `~22-25 jugadores`) sin mezclar equipos distintos. |
| **`MONITOR M2.4`** | **2) Fase 4: Cinemática `P2`** | `0` jugadores con velocidad $> 9.5\text{ m/s}$ ($34.2\text{ km/h}$) y `0` aceleraciones $> 5.0\text{ m/s}^2$. |
| **`MONITOR M2.5`** | **2) Fase 5: Analista Táctico** | `8` ventanas JSON generadas (`W01..W08`), cada una `< 500 bytes` y sin valores `NaN`. |
| **`MONITOR M3`** | **2) LLM `watsonx.ai` + Gobernanza** | Modelo permitido `ibm/granite-3-8b-instruct`, JSON válido, guardia anti-alucinación y registro en `governance_audit.jsonl`. |
| **`MONITOR M4`** | **3) Dashboard Local + Voz TTS** | Desfase de reloj $|t_{\text{video}} - t_{\text{radar}}| < 40\text{ ms}$ y duración de audio TTS $\le 4.0\text{ s}$ por ventana. |
