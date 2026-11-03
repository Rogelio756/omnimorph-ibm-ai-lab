"""
Omnimorph Engine — Custom Python Tool para IBM watsonx Orchestrate ADK.
Ejecuta las 5 fases de post-procesamiento matemático (Equipos, P1 Homografía,
P3 Track Stitching Húngaro, P2 Cinemática Savitzky-Golay y Fase 5 Ventanas Tácticas)
junto con los Monitores de Observabilidad por Etapa (M2.0 a M2.5).
"""

import json
from pathlib import Path
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
    H_stack = np.vstack(df_frm["H"].values).astype(np.float64)
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
    S_MAX_CMS = 950.0
    A_MAX_CMS2 = 500.0

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


def process_parquet_files(
    frames_parquet_path: str,
    objects_parquet_path: str,
    output_dir: str = "data/clean",
) -> dict:
    """
    Punto de entrada para watsonx Orchestrate ADK Tool o ejecución CLI.
    Lee frames.parquet y objects.parquet, ejecuta las 5 fases + monitores,
    guarda objects_cleaned.parquet, tactical_summaries.json y stage_monitors.json.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    df_frames = pd.read_parquet(frames_parquet_path)
    df_objects = pd.read_parquet(objects_parquet_path)

    df_cleaned, json_summaries, stage_monitors = run_omnimorph_engine(df_frames, df_objects)

    cleaned_parquet = out_path / "objects_cleaned.parquet"
    summaries_json = out_path / "tactical_summaries.json"
    monitors_json = out_path / "stage_monitors.json"

    df_cleaned.to_parquet(cleaned_parquet, index=False)
    summaries_json.write_text(json.dumps(json_summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    monitors_json.write_text(json.dumps(stage_monitors, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "stage_monitors": stage_monitors,
        "tactical_summaries": json_summaries,
        "cleaned_parquet_path": str(cleaned_parquet),
    }
