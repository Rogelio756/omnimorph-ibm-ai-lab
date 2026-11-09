r"""
scripts/finalize_mvp_perception.py
===================================
Construye en segundos las salidas unificadas finales:
  - frames.parquet
  - objects.parquet
  - TELEMETRIA_UNIFICADA_COMPLETA.json
  - VIDEO_UNIFICADO_TODOS_JUNTOS.mp4

a partir de los 6 JSON ya generados en `json_por_modelo/` sin volver a correr los modelos en GPU.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import cv2
import numpy as np

import exp_common as ec


def _load_json(path: pathlib.Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data: dict, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ensambla el Video Unificado, JSON Unificado y Parquets desde json_por_modelo/"
    )
    parser.add_argument(
        "--source",
        default="data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4",
    )
    parser.add_argument(
        "--outdir",
        default="outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13",
    )
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument(
        "--team0-label",
        default="Brasil (Eq 0)",
        help="Etiqueta del equipo 0 (team_id=0) en la leyenda del video unificado",
    )
    parser.add_argument(
        "--team1-label",
        default="Alemania (Eq 1)",
        help="Etiqueta del equipo 1 (team_id=1) en la leyenda del video unificado",
    )
    parser.add_argument(
        "--match-label",
        default="Brasil vs. Alemania (1-7) — Semifinal",
        help="Nombre del partido para TELEMETRIA_UNIFICADA_COMPLETA.json",
    )
    parser.add_argument(
        "--project-label",
        default="Omnimorph MVP — Mundial FIFA Brasil 2014",
        help="Nombre del proyecto para TELEMETRIA_UNIFICADA_COMPLETA.json",
    )
    args = parser.parse_args()

    out_root = pathlib.Path(args.outdir)
    json_dir = out_root / "json_por_modelo"
    video_dir = out_root / "videos_por_modelo"

    import supervision as sv
    import main as soccer
    from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
    from sports.common.ball import BallAnnotator

    print("=" * 68)
    print("  ENSAMBLANDO SALIDAS UNIFICADAS DESDE json_por_modelo/ (SIN GPU)")
    print("=" * 68)

    t0 = time.perf_counter()
    j_pitch = _load_json(json_dir / "PITCH_DETECTION.json")
    j_player = _load_json(json_dir / "PLAYER_DETECTION.json")
    j_ball = _load_json(json_dir / "BALL_DETECTION.json")
    j_track = _load_json(json_dir / "PLAYER_TRACKING.json")
    j_team = _load_json(json_dir / "TEAM_CLASSIFICATION.json")
    j_radar = _load_json(json_dir / "RADAR.json")

    raw_info = sv.VideoInfo.from_video_path(args.source)
    n_available = len(j_pitch["frames"])
    n_frames_target = min(args.max_frames, n_available) if args.max_frames else n_available
    video_info = sv.VideoInfo(
        width=raw_info.width,
        height=raw_info.height,
        fps=raw_info.fps,
        total_frames=n_frames_target,
    )
    fps = float(video_info.fps)

    obj_cols = {
        k: []
        for k in [
            "frame", "t", "source", "track_id", "class_id", "class_name",
            "team", "x1", "y1", "x2", "y2", "conf", "pitch_x", "pitch_y",
        ]
    }
    frm_cols = {
        k: []
        for k in [
            "frame", "t", "n_det", "n_track", "ball_found",
            "homography_valid", "homography_error", "n_kp_visible",
            "kp_x", "kp_y", "kp_conf", "H",
        ]
    }

    def _add_obj(f_idx, src_name, bbox, cls_id, cls_name, conf_val, tid=None, team=None, pxy=None):
        obj_cols["frame"].append(f_idx)
        obj_cols["t"].append(round(f_idx / fps, 4))
        obj_cols["source"].append(src_name)
        obj_cols["track_id"].append(None if tid is None else int(tid))
        obj_cols["class_id"].append(int(cls_id))
        obj_cols["class_name"].append(str(cls_name))
        obj_cols["team"].append(team)
        obj_cols["x1"].append(float(bbox["x1"]))
        obj_cols["y1"].append(float(bbox["y1"]))
        obj_cols["x2"].append(float(bbox["x2"]))
        obj_cols["y2"].append(float(bbox["y2"]))
        obj_cols["conf"].append(None if conf_val is None else float(conf_val))
        obj_cols["pitch_x"].append(None if pxy is None else float(pxy[0]))
        obj_cols["pitch_y"].append(None if pxy is None else float(pxy[1]))

    unified_frames_json = []

    for idx in range(n_frames_target):
        fp = j_pitch["frames"][idx]
        fpl = j_player["frames"][idx]
        fb = j_ball["frames"][idx]
        ft = j_track["frames"][idx]
        ftm = j_team["frames"][idx]
        fr = j_radar["frames"][idx]

        team_by_tid = {e["track_id"]: e["team_id"] for e in ftm["entities"]}
        pxy_by_tid = {
            p["track_id"]: (p["pitch_x_cm"], p["pitch_y_cm"])
            for p in fr["projected_players"]
        }

        # 1. Detections
        for d in fpl["detections"]:
            _add_obj(
                idx,
                "det",
                d["bbox_px"],
                d["class_id"],
                d["class_name"],
                d["conf"],
            )

        # 2. Tracks
        for tr in ft["tracks"]:
            tid = tr["track_id"]
            _add_obj(
                idx,
                "track",
                tr["bbox_px"],
                tr["class_id"],
                tr["class_name"],
                tr["conf"],
                tid=tid,
                team=team_by_tid.get(tid),
                pxy=pxy_by_tid.get(tid),
            )

        # 3. Balls
        for b_i, b in enumerate(fb["balls"]):
            b_pxy = None
            if b_i < len(fr["projected_balls"]):
                pb = fr["projected_balls"][b_i]
                b_pxy = (pb["pitch_x_cm"], pb["pitch_y_cm"])
            _add_obj(
                idx,
                "ball",
                b["bbox_px"],
                0,
                "ball",
                b["conf"],
                pxy=b_pxy,
            )

        # 4. Frames parquet
        frm_cols["frame"].append(idx)
        frm_cols["t"].append(round(idx / fps, 4))
        frm_cols["n_det"].append(fpl["n_detections"])
        frm_cols["n_track"].append(ft["n_tracked"])
        frm_cols["ball_found"].append(fb["ball_found"])
        frm_cols["homography_valid"].append(fr["homography_valid"])
        frm_cols["homography_error"].append(fr["homography_error"])
        frm_cols["n_kp_visible"].append(fp["n_kp_visible"])
        frm_cols["kp_x"].append(fp["kp_x"])
        frm_cols["kp_y"].append(fp["kp_y"])
        frm_cols["kp_conf"].append(fp["kp_conf"])
        frm_cols["H"].append(fr["H"])

        unified_frames_json.append({
            "frame": idx,
            "t": round(idx / fps, 4),
            "pitch": {
                "n_kp_visible": fp["n_kp_visible"],
                "homography_valid": fr["homography_valid"],
                "homography_error": fr["homography_error"],
            },
            "counts": {
                "n_detections": fpl["n_detections"],
                "n_tracked": ft["n_tracked"],
                "ball_found": fb["ball_found"],
            },
            "ball": fr["projected_balls"][0] if fr["projected_balls"] else None,
            "players_tracked": fr["projected_players"],
        })

    ec.write_parquet(obj_cols, str(out_root / "objects.parquet"))
    ec.write_parquet(frm_cols, str(out_root / "frames.parquet"))
    print("  [OK] frames.parquet y objects.parquet guardados.")

    # Renderizar VIDEO_UNIFICADO_TODOS_JUNTOS.mp4
    print("  Renderizando VIDEO_UNIFICADO_TODOS_JUNTOS.mp4 ...")
    unified_video_path = out_root / "VIDEO_UNIFICADO_TODOS_JUNTOS.mp4"
    vertex_annotator = sv.VertexAnnotator(color=sv.Color.from_hex("#A020F0"), radius=6)
    uni_ball_annotator = BallAnnotator(radius=6, buffer_size=10)
    colors = [sv.Color.from_hex(c) for c in soccer.COLORS]
    legend = [
        (args.team0_label, colors[0]),
        (args.team1_label, colors[1]),
        ("Arbitro", colors[3]),
        ("Cancha (Keypoints)", sv.Color.from_hex("#A020F0")),
        ("Balon (Rastro)", sv.Color.from_hex("#FFFFFF")),
    ]

    gen = sv.get_video_frames_generator(source_path=args.source, end=n_frames_target)
    with sv.VideoSink(str(unified_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            img = frame.copy()
            fp = j_pitch["frames"][idx]
            fb = j_ball["frames"][idx]
            ftm = j_team["frames"][idx]
            fr = j_radar["frames"][idx]

            # 1. Keypoints visibles de cancha
            if fp["kp_x"]:
                xy = np.stack([fp["kp_x"], fp["kp_y"]], axis=1).astype(np.float32)
                vis = (xy[:, 0] > 1) & (xy[:, 1] > 1)
                if vis.any():
                    img = vertex_annotator.annotate(img, sv.KeyPoints(xy=xy[vis][None]))

            # 2. Jugadores / Porteros / Arbitros con equipo + track_id
            entities = ftm["entities"]
            if entities:
                dets = sv.Detections(
                    xyxy=np.array(
                        [[e["bbox_px"]["x1"], e["bbox_px"]["y1"], e["bbox_px"]["x2"], e["bbox_px"]["y2"]] for e in entities],
                        dtype=np.float32,
                    ),
                    class_id=np.array([e["class_id"] for e in entities], dtype=int),
                    tracker_id=np.array([e["track_id"] for e in entities], dtype=int),
                )
                lookup = np.array(
                    [e["team_id"] if e["team_id"] in (0, 1) else soccer.REFEREE_CLASS_ID for e in entities],
                    dtype=int,
                )
                labels = [str(e["track_id"]) for e in entities]
                img = soccer.ELLIPSE_ANNOTATOR.annotate(img, dets, custom_color_lookup=lookup)
                img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
                    img, dets, labels, custom_color_lookup=lookup
                )
            else:
                lookup = np.array([], dtype=int)

            # 3. Balon con rastro
            if fb["balls"]:
                ball_dets = sv.Detections(
                    xyxy=np.array(
                        [[b["bbox_px"]["x1"], b["bbox_px"]["y1"], b["bbox_px"]["x2"], b["bbox_px"]["y2"]] for b in fb["balls"]],
                        dtype=np.float32,
                    ),
                    class_id=np.zeros(len(fb["balls"]), dtype=int),
                )
            else:
                ball_dets = sv.Detections.empty()
            img = uni_ball_annotator.annotate(img, ball_dets)

            # 4. Radar Cenital 2D superpuesto abajo al centro
            h_f, w_f, _ = frame.shape
            if fr["homography_valid"] and fr["projected_players"]:
                radar_img = draw_pitch(config=soccer.CONFIG)
                pxy = np.array(
                    [[p["pitch_x_cm"], p["pitch_y_cm"]] for p in fr["projected_players"]],
                    dtype=np.float32,
                ).reshape(-1, 2)
                lk = np.array(
                    [p["team_id"] if p["team_id"] in (0, 1) else soccer.REFEREE_CLASS_ID for p in fr["projected_players"]],
                    dtype=int,
                )
                for c_idx in range(4):
                    pts = pxy[lk == c_idx] if len(pxy) > 0 else np.zeros((0, 2), np.float32)
                    radar_img = draw_points_on_pitch(
                        config=soccer.CONFIG,
                        xy=pts,
                        face_color=colors[c_idx],
                        radius=20,
                        pitch=radar_img,
                    )
                if fr["projected_balls"]:
                    bxy = np.array(
                        [[b["pitch_x_cm"], b["pitch_y_cm"]] for b in fr["projected_balls"]],
                        dtype=np.float32,
                    ).reshape(-1, 2)
                    radar_img = draw_points_on_pitch(
                        config=soccer.CONFIG,
                        xy=bxy,
                        face_color=sv.Color.WHITE,
                        edge_color=sv.Color.BLACK,
                        radius=14,
                        pitch=radar_img,
                    )
                rw_max = int(w_f * 0.25)
                radar_img = sv.resize_image(radar_img, (rw_max, h_f), keep_aspect_ratio=True)
                rh, rw, _ = radar_img.shape
                img = sv.draw_image(
                    img,
                    radar_img,
                    opacity=0.65,
                    rect=sv.Rect(x=w_f // 2 - rw // 2, y=h_f - rh - 10, width=rw, height=rh),
                )

            # 5. Leyenda y contador de cuadro en la esquina INFERIOR DERECHA
            box_w = 275
            box_h = 46 + 26 * len(legend)
            x1_box = w_f - box_w - 15
            y1_box = h_f - box_h - 15
            x2_box = w_f - 15
            y2_box = h_f - 15

            overlay = img.copy()
            cv2.rectangle(overlay, (x1_box, y1_box), (x2_box, y2_box), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.72, img, 0.28, 0, img)

            cv2.putText(
                img,
                f"Frame {idx + 1}/{n_frames_target} ({idx / fps:.1f}s)",
                (x1_box + 14, y1_box + 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
            )
            for l_i, (text, col) in enumerate(legend):
                y_pos = y1_box + 54 + 26 * l_i
                cv2.circle(img, (x1_box + 22, y_pos - 5), 7, col.as_bgr(), -1)
                cv2.putText(
                    img, text, (x1_box + 38, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 2
                )

            sink.write_frame(img)
            if (idx + 1) % 150 == 0 or (idx + 1) == n_frames_target:
                print(f"  [VIDEO UNIFICADO] frame {idx + 1}/{n_frames_target}", flush=True)

    # Transcodificar de mp4v (MPEG-4 Part 2) a H.264 (avc1 + faststart) para compatibilidad HTML5/Streamlit
    try:
        import av

        tmp_h264 = unified_video_path.with_suffix(".h264.mp4")
        with av.open(str(unified_video_path)) as inp:
            in_s = inp.streams.video[0]
            if in_s.codec_context.name != "h264":
                print("  [H.264] Transcodificando a H.264 (yuv420p, faststart) para navegadores web...")
                with av.open(str(tmp_h264), mode="w", options={"movflags": "faststart"}) as out_c:
                    out_s = out_c.add_stream("libx264", rate=int(round(fps)))
                    out_s.width = in_s.width
                    out_s.height = in_s.height
                    out_s.pix_fmt = "yuv420p"
                    out_s.options = {"preset": "veryfast", "crf": "23"}
                    for frm in inp.decode(video=0):
                        for pkt in out_s.encode(frm):
                            out_c.mux(pkt)
                    for pkt in out_s.encode():
                        out_c.mux(pkt)
        if tmp_h264.exists():
            tmp_h264.replace(unified_video_path)
    except Exception as e:
        print(f"  [WARN] No se pudo transcodificar a H.264 con PyAV: {e}")

    timings_seconds = {
        "PITCH_DETECTION_s": j_pitch.get("elapsed_s", 0),
        "PLAYER_DETECTION_s": j_player.get("elapsed_s", 0),
        "BALL_DETECTION_s": j_ball.get("elapsed_s", 0),
        "PLAYER_TRACKING_s": j_track.get("elapsed_s", 0),
        "TEAM_CLASSIFICATION_s": j_team.get("elapsed_s", 0),
        "RADAR_s": j_radar.get("elapsed_s", 0),
        "UNIFIED_EXPORT_s": round(time.perf_counter() - t0, 2),
    }

    unified_master_json = {
        "project": args.project_label,
        "match": args.match_label,
        "source_video": args.source,
        "resolution": f"{video_info.width}x{video_info.height}",
        "fps": fps,
        "frames_processed": n_frames_target,
        "timings_seconds": timings_seconds,
        "outputs": {
            "json_por_modelo_dir": str(json_dir),
            "videos_por_modelo_dir": str(video_dir),
            "unified_video": str(unified_video_path),
            "frames_parquet": str(out_root / "frames.parquet"),
            "objects_parquet": str(out_root / "objects.parquet"),
        },
        "summary_metrics": {
            "total_detections_rows": len(obj_cols["frame"]),
            "ball_found_frames": int(sum(frm_cols["ball_found"])),
            "homography_valid_frames": int(sum(frm_cols["homography_valid"])),
            "homography_valid_rate": round(sum(frm_cols["homography_valid"]) / max(n_frames_target, 1), 4),
        },
        "frames": unified_frames_json,
    }
    _save_json(unified_master_json, out_root / "TELEMETRIA_UNIFICADA_COMPLETA.json")

    print("\n" + "=" * 68)
    print("  PROCESO COMPLETADO CON EXITO (SIN REPETIR INFERENCIA GPU)")
    print("=" * 68)
    print(f"  1. JSONs por modelo   -> {json_dir}")
    print(f"  2. Videos por modelo  -> {video_dir}")
    print(f"  3. Video Unificado    -> {unified_video_path}")
    print(f"  4. JSON Unificado     -> {out_root / 'TELEMETRIA_UNIFICADA_COMPLETA.json'}")
    print(f"  5. Parquets Pipeline  -> {out_root / 'frames.parquet'} & objects.parquet")
    print("=" * 68)


if __name__ == "__main__":
    main()
