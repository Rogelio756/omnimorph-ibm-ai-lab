r"""
scripts/run_mvp_perception.py
=============================
Ejecuta los 6 modos de percepción del MVP de forma aislada y secuencial (modelo por modelo)
para evitar picos de VRAM/RAM y fallos entre etapas, y genera:

1. Carpeta `json_por_modelo/`:
   - `PITCH_DETECTION.json`       (keypoints de cancha por cuadro + métricas del modelo)
   - `PLAYER_DETECTION.json`      (bounding boxes crudos de jugadores/porteros/árbitros)
   - `BALL_DETECTION.json`        (detecciones y trayectoria del balón con InferenceSlicer)
   - `PLAYER_TRACKING.json`       (jugadores con track_id persistente de ByteTrack)
   - `TEAM_CLASSIFICATION.json`   (jugadores con team_id 0/1 vía SigLIP + UMAP + KMeans)
   - `RADAR.json`                 (matriz de homografía H y coordenadas cenitales pitch_x, pitch_y)

2. Carpeta `videos_por_modelo/`:
   - `PITCH_DETECTION.mp4`
   - `PLAYER_DETECTION.mp4`
   - `BALL_DETECTION.mp4`
   - `PLAYER_TRACKING.mp4`
   - `TEAM_CLASSIFICATION.mp4`
   - `RADAR.mp4`

3. Salidas Unificadas en la raíz de `--outdir`:
   - `TELEMETRIA_UNIFICADA_COMPLETA.json` (toda la información consolidada cuadro por cuadro y resumen de los 6 modelos)
   - `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4`   (video maestro con cancha + equipos + IDs + balón + radar cenital)
   - `frames.parquet` y `objects.parquet` (compatibles al 100% con `run_pipeline.py --use-real` y Monitores M1–M4)

Uso:
  .\.venv\Scripts\python.exe scripts/run_mvp_perception.py \
      --source data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4 \
      --outdir outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13 \
      --max-frames 750 --device cuda
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import pathlib
import sys
import time

import cv2
import numpy as np

import exp_common as ec

CLASS_NAMES = {0: "ball", 1: "goalkeeper", 2: "player", 3: "referee"}
MODES = [
    "PITCH_DETECTION",
    "PLAYER_DETECTION",
    "BALL_DETECTION",
    "PLAYER_TRACKING",
    "TEAM_CLASSIFICATION",
    "RADAR",
]


def _free_gpu() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _save_json(data: dict, path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _subset_video_info(video_info, max_frames: int | None):
    import supervision as sv
    total = video_info.total_frames
    if max_frames is not None and max_frames < total:
        total = max_frames
    return sv.VideoInfo(
        width=video_info.width,
        height=video_info.height,
        fps=video_info.fps,
        total_frames=total,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecución secuencial por modelo para el MVP Omnimorph (JSONs + Videos + Unificado)"
    )
    parser.add_argument(
        "--source",
        default="data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4",
        help="Ruta al video fuente .mp4",
    )
    parser.add_argument(
        "--outdir",
        default="outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13",
        help="Carpeta raíz de salida para esta prueba del MVP",
    )
    parser.add_argument("--device", default="cuda", help="Dispositivo (cuda o cpu)")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Número de frames a procesar (por defecto: None = video completo de 1800 frames / 60s)",
    )
    parser.add_argument("--seed", type=int, default=ec.SEED)
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
    out_root.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    import supervision as sv
    from ultralytics import YOLO
    import main as soccer
    from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
    from sports.common.ball import BallAnnotator, BallTracker
    from sports.common.view import ViewTransformer

    ec.seed_everything(args.seed)

    raw_info = sv.VideoInfo.from_video_path(args.source)
    video_info = _subset_video_info(raw_info, args.max_frames)
    fps = float(video_info.fps)
    n_frames_target = video_info.total_frames

    print("=" * 68)
    print("  OMNIMORPH MVP — PERCEPCION SECUENCIAL POR MODELO")
    print("=" * 68)
    print(f"  Video fuente : {args.source}")
    print(f"  Resolucion   : {video_info.width}x{video_info.height} @ {fps:.2f} FPS")
    print(f"  Frames a leer: {n_frames_target} (de {raw_info.total_frames} totales)")
    print(f"  Salida raiz  : {out_root}")
    print("=" * 68)

    # Estructuras en memoria para compartir resultados de cada etapa sin re-ejecutar GPU
    pitch_per_frame: list[dict] = []
    player_det_per_frame: list[sv.Detections] = []
    ball_det_per_frame: list[sv.Detections] = []
    tracked_per_frame: list[sv.Detections] = []
    team_per_frame: list[dict] = []
    radar_per_frame: list[dict] = []
    timings_per_stage: dict[str, float] = {}

    # =========================================================================
    # MODELO 1: PITCH_DETECTION (YOLOv8x-pose)
    # =========================================================================
    print("\n[1/6] Ejecutando PITCH_DETECTION (YOLOv8x-pose) ...")
    t0 = time.perf_counter()
    pitch_model = YOLO(soccer.PITCH_DETECTION_MODEL_PATH).to(device=args.device)
    pitch_video_path = video_dir / "PITCH_DETECTION.mp4"
    pitch_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(pitch_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            res = pitch_model(frame, verbose=False)[0]
            keypoints = sv.KeyPoints.from_ultralytics(res)
            if len(keypoints) == 0:
                kp_xy = np.zeros((0, 2), np.float32)
                kp_conf = np.zeros((0,), np.float32)
            else:
                kp_xy = keypoints.xy[0]
                kp_conf = (
                    keypoints.confidence[0]
                    if keypoints.confidence is not None
                    else np.full(len(kp_xy), np.nan, np.float32)
                )
            mask = (kp_xy[:, 0] > 1) & (kp_xy[:, 1] > 1)

            pitch_per_frame.append({
                "keypoints": keypoints,
                "kp_xy": kp_xy,
                "kp_conf": kp_conf,
                "kp_mask": mask,
            })

            pitch_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "n_kp_visible": int(mask.sum()),
                "kp_x": [round(float(v), 2) for v in kp_xy[:, 0]],
                "kp_y": [round(float(v), 2) for v in kp_xy[:, 1]],
                "kp_conf": [round(float(v), 4) for v in kp_conf],
            })

            annotated = soccer.VERTEX_LABEL_ANNOTATOR.annotate(
                frame.copy(), keypoints, soccer.CONFIG.labels
            )
            sink.write_frame(annotated)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [PITCH_DETECTION] frame {idx + 1}/{n_frames_target}", flush=True)

    del pitch_model
    _free_gpu()
    timings_per_stage["PITCH_DETECTION_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "PITCH_DETECTION",
            "source_video": args.source,
            "output_video": str(pitch_video_path),
            "frames_processed": len(pitch_json_frames),
            "elapsed_s": timings_per_stage["PITCH_DETECTION_s"],
            "frames": pitch_json_frames,
        },
        json_dir / "PITCH_DETECTION.json",
    )
    print(f"  -> Completado en {timings_per_stage['PITCH_DETECTION_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # MODELO 2: PLAYER_DETECTION (YOLOv8x imgsz=1280)
    # =========================================================================
    print("\n[2/6] Ejecutando PLAYER_DETECTION (YOLOv8x) ...")
    t0 = time.perf_counter()
    player_model = YOLO(soccer.PLAYER_DETECTION_MODEL_PATH).to(device=args.device)
    player_video_path = video_dir / "PLAYER_DETECTION.mp4"
    player_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(player_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            res = player_model(frame, imgsz=1280, verbose=False)[0]
            det = sv.Detections.from_ultralytics(res)
            player_det_per_frame.append(det)

            dets_list = []
            for k in range(len(det)):
                cid = int(det.class_id[k])
                x1, y1, x2, y2 = [round(float(v), 2) for v in det.xyxy[k]]
                conf = round(float(det.confidence[k]), 4) if det.confidence is not None else None
                dets_list.append({
                    "class_id": cid,
                    "class_name": CLASS_NAMES.get(cid, str(cid)),
                    "bbox_px": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "conf": conf,
                })

            player_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "n_detections": len(dets_list),
                "detections": dets_list,
            })

            img = soccer.BOX_ANNOTATOR.annotate(frame.copy(), det)
            img = soccer.BOX_LABEL_ANNOTATOR.annotate(img, det)
            sink.write_frame(img)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [PLAYER_DETECTION] frame {idx + 1}/{n_frames_target}", flush=True)

    del player_model
    _free_gpu()
    timings_per_stage["PLAYER_DETECTION_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "PLAYER_DETECTION",
            "source_video": args.source,
            "output_video": str(player_video_path),
            "frames_processed": len(player_json_frames),
            "elapsed_s": timings_per_stage["PLAYER_DETECTION_s"],
            "frames": player_json_frames,
        },
        json_dir / "PLAYER_DETECTION.json",
    )
    print(f"  -> Completado en {timings_per_stage['PLAYER_DETECTION_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # MODELO 3: BALL_DETECTION (YOLOv8x + InferenceSlicer 640x640)
    # =========================================================================
    print("\n[3/6] Ejecutando BALL_DETECTION (InferenceSlicer 640x640) ...")
    t0 = time.perf_counter()
    ball_model = YOLO(soccer.BALL_DETECTION_MODEL_PATH).to(device=args.device)

    def _ball_cb(image_slice):
        r = ball_model(image_slice, imgsz=640, verbose=False)[0]
        return sv.Detections.from_ultralytics(r)

    slicer = sv.InferenceSlicer(
        callback=_ball_cb,
        overlap_filter=sv.OverlapFilter.NONE,
        slice_wh=(640, 640),
    )
    ball_tracker = BallTracker(buffer_size=20)
    ball_annotator = BallAnnotator(radius=6, buffer_size=10)
    ball_video_path = video_dir / "BALL_DETECTION.mp4"
    ball_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(ball_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            ball = slicer(frame).with_nms(threshold=0.1)
            ball = ball_tracker.update(ball)
            ball_det_per_frame.append(ball)

            balls_list = []
            for k in range(len(ball)):
                x1, y1, x2, y2 = [round(float(v), 2) for v in ball.xyxy[k]]
                conf = round(float(ball.confidence[k]), 4) if ball.confidence is not None else None
                balls_list.append({
                    "bbox_px": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "conf": conf,
                })

            ball_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "ball_found": len(balls_list) > 0,
                "balls": balls_list,
            })

            annotated = ball_annotator.annotate(frame.copy(), ball)
            sink.write_frame(annotated)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [BALL_DETECTION] frame {idx + 1}/{n_frames_target}", flush=True)

    del ball_model, slicer
    _free_gpu()
    timings_per_stage["BALL_DETECTION_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "BALL_DETECTION",
            "source_video": args.source,
            "output_video": str(ball_video_path),
            "frames_processed": len(ball_json_frames),
            "elapsed_s": timings_per_stage["BALL_DETECTION_s"],
            "frames": ball_json_frames,
        },
        json_dir / "BALL_DETECTION.json",
    )
    print(f"  -> Completado en {timings_per_stage['BALL_DETECTION_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # MODELO 4: PLAYER_TRACKING (ByteTrack)
    # =========================================================================
    print("\n[4/6] Ejecutando PLAYER_TRACKING (ByteTrack) ...")
    t0 = time.perf_counter()
    tracker = sv.ByteTrack(minimum_consecutive_frames=3)
    tracking_video_path = video_dir / "PLAYER_TRACKING.mp4"
    tracking_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(tracking_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            det = player_det_per_frame[idx]
            tracked = tracker.update_with_detections(det)
            tracked_per_frame.append(tracked)

            tracks_list = []
            for k in range(len(tracked)):
                tid = int(tracked.tracker_id[k])
                cid = int(tracked.class_id[k])
                x1, y1, x2, y2 = [round(float(v), 2) for v in tracked.xyxy[k]]
                conf = round(float(tracked.confidence[k]), 4) if tracked.confidence is not None else None
                tracks_list.append({
                    "track_id": tid,
                    "class_id": cid,
                    "class_name": CLASS_NAMES.get(cid, str(cid)),
                    "bbox_px": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "conf": conf,
                })

            tracking_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "n_tracked": len(tracks_list),
                "tracks": tracks_list,
            })

            img = soccer.ELLIPSE_ANNOTATOR.annotate(frame.copy(), tracked)
            img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
                img, tracked, labels=[str(i) for i in tracked.tracker_id]
            )
            sink.write_frame(img)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [PLAYER_TRACKING] frame {idx + 1}/{n_frames_target}", flush=True)

    timings_per_stage["PLAYER_TRACKING_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "PLAYER_TRACKING",
            "source_video": args.source,
            "output_video": str(tracking_video_path),
            "frames_processed": len(tracking_json_frames),
            "elapsed_s": timings_per_stage["PLAYER_TRACKING_s"],
            "frames": tracking_json_frames,
        },
        json_dir / "PLAYER_TRACKING.json",
    )
    print(f"  -> Completado en {timings_per_stage['PLAYER_TRACKING_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # MODELO 5: TEAM_CLASSIFICATION (SigLIP + UMAP + KMeans)
    # =========================================================================
    print("\n[5/6] Ejecutando TEAM_CLASSIFICATION (SigLIP + UMAP + KMeans) ...")
    t0 = time.perf_counter()
    crops = []
    gen_stride = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    for idx, frame in enumerate(gen_stride):
        if idx % soccer.STRIDE == 0:
            det = player_det_per_frame[idx]
            crops += soccer.get_crops(frame, det[det.class_id == soccer.PLAYER_CLASS_ID])

    ec.seed_everything(args.seed)
    team_classifier = ec.make_seeded_team_classifier(args.seed)(device=args.device)
    team_classifier.fit(crops)
    del crops

    team_video_path = video_dir / "TEAM_CLASSIFICATION.mp4"
    team_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(team_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            tracked = tracked_per_frame[idx]
            players = tracked[tracked.class_id == soccer.PLAYER_PLAYER_ID if hasattr(soccer, "PLAYER_PLAYER_ID") else tracked.class_id == soccer.PLAYER_CLASS_ID]
            players_team_id = (
                team_classifier.predict(soccer.get_crops(frame, players))
                if len(players) > 0
                else np.array([], dtype=int)
            )
            goalkeepers = tracked[tracked.class_id == soccer.GOALKEEPER_CLASS_ID]
            goalkeepers_team_id = (
                soccer.resolve_goalkeepers_team_id(players, players_team_id, goalkeepers)
                if len(goalkeepers) > 0 and len(players) > 0
                else np.zeros(len(goalkeepers), dtype=int)
            )
            referees = tracked[tracked.class_id == soccer.REFEREE_CLASS_ID]
            merged = sv.Detections.merge([players, goalkeepers, referees])
            color_lookup = np.array(
                players_team_id.tolist()
                + goalkeepers_team_id.tolist()
                + [soccer.REFEREE_CLASS_ID] * len(referees),
                dtype=int,
            )

            team_by_tid = {}
            team_entries = []
            for k in range(len(merged)):
                tid = int(merged.tracker_id[k])
                cid = int(merged.class_id[k])
                lk = int(color_lookup[k])
                t_val = lk if lk in (0, 1) else None
                team_by_tid[tid] = t_val
                x1, y1, x2, y2 = [round(float(v), 2) for v in merged.xyxy[k]]
                team_entries.append({
                    "track_id": tid,
                    "class_id": cid,
                    "class_name": CLASS_NAMES.get(cid, str(cid)),
                    "team_id": t_val,
                    "bbox_px": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                })

            team_per_frame.append({
                "merged": merged,
                "color_lookup": color_lookup,
                "team_by_tid": team_by_tid,
            })

            team_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "n_entities": len(team_entries),
                "entities": team_entries,
            })

            labels = [str(i) for i in merged.tracker_id]
            img = soccer.ELLIPSE_ANNOTATOR.annotate(
                frame.copy(), merged, custom_color_lookup=color_lookup
            )
            img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
                img, merged, labels, custom_color_lookup=color_lookup
            )
            sink.write_frame(img)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [TEAM_CLASSIFICATION] frame {idx + 1}/{n_frames_target}", flush=True)

    del team_classifier
    _free_gpu()
    timings_per_stage["TEAM_CLASSIFICATION_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "TEAM_CLASSIFICATION",
            "source_video": args.source,
            "output_video": str(team_video_path),
            "frames_processed": len(team_json_frames),
            "elapsed_s": timings_per_stage["TEAM_CLASSIFICATION_s"],
            "frames": team_json_frames,
        },
        json_dir / "TEAM_CLASSIFICATION.json",
    )
    print(f"  -> Completado en {timings_per_stage['TEAM_CLASSIFICATION_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # MODELO 6: RADAR (Homografia ViewTransformer + Proyeccion 2D)
    # =========================================================================
    print("\n[6/6] Ejecutando RADAR (Homografia + Vista Cenital 2D) ...")
    t0 = time.perf_counter()
    radar_video_path = video_dir / "RADAR.mp4"
    radar_json_frames = []

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(radar_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            p_info = pitch_per_frame[idx]
            t_info = team_per_frame[idx]
            ball = ball_det_per_frame[idx]

            kp_xy = p_info["kp_xy"]
            mask = p_info["kp_mask"]
            merged = t_info["merged"]
            lookup = t_info["color_lookup"]

            H, h_error, merged_xy, ball_xy = None, None, None, None
            if len(kp_xy) == 0 or int(mask.sum()) < 4:
                h_error = "insufficient_keypoints"
            else:
                try:
                    transformer = ViewTransformer(
                        source=kp_xy[mask].astype(np.float32),
                        target=np.array(soccer.CONFIG.vertices)[mask].astype(np.float32),
                    )
                    H = transformer.m
                    if len(merged) > 0:
                        merged_xy = transformer.transform_points(
                            merged.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                        )
                    else:
                        merged_xy = np.zeros((0, 2), np.float32)
                    if len(ball) > 0:
                        ball_xy = transformer.transform_points(
                            ball.get_anchors_coordinates(sv.Position.BOTTOM_CENTER)
                        )
                    else:
                        ball_xy = np.zeros((0, 2), np.float32)
                except Exception as exc:
                    h_error = f"{type(exc).__name__}: {exc}".splitlines()[0][:160]

            pxy_by_tid = {}
            projected_players = []
            if merged_xy is not None:
                for k in range(len(merged)):
                    tid = int(merged.tracker_id[k])
                    px, py = float(merged_xy[k][0]), float(merged_xy[k][1])
                    pxy_by_tid[tid] = (px, py)
                    projected_players.append({
                        "track_id": tid,
                        "team_id": t_info["team_by_tid"].get(tid),
                        "pitch_x_cm": round(px, 2),
                        "pitch_y_cm": round(py, 2),
                    })

            projected_balls = []
            if ball_xy is not None and len(ball_xy) > 0:
                for k in range(len(ball_xy)):
                    projected_balls.append({
                        "pitch_x_cm": round(float(ball_xy[k][0]), 2),
                        "pitch_y_cm": round(float(ball_xy[k][1]), 2),
                    })

            radar_per_frame.append({
                "H": H,
                "h_error": h_error,
                "merged_xy": merged_xy,
                "ball_xy": ball_xy,
                "pxy_by_tid": pxy_by_tid,
                "projected_players": projected_players,
                "projected_balls": projected_balls,
            })

            radar_json_frames.append({
                "frame": idx,
                "t": round(idx / fps, 4),
                "homography_valid": H is not None,
                "homography_error": h_error,
                "H": [round(float(v), 6) for v in H.ravel()] if H is not None else None,
                "projected_players": projected_players,
                "projected_balls": projected_balls,
            })

            # Dibujar video RADAR
            labels = [str(i) for i in merged.tracker_id]
            img = soccer.ELLIPSE_ANNOTATOR.annotate(
                frame.copy(), merged, custom_color_lookup=lookup
            )
            img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
                img, merged, labels, custom_color_lookup=lookup
            )
            if H is not None and merged_xy is not None:
                radar_img = draw_pitch(config=soccer.CONFIG)
                for c_idx in range(4):
                    pts = merged_xy[lookup == c_idx] if len(merged_xy) > 0 else np.zeros((0, 2), np.float32)
                    radar_img = draw_points_on_pitch(
                        config=soccer.CONFIG,
                        xy=pts,
                        face_color=sv.Color.from_hex(soccer.COLORS[c_idx]),
                        radius=20,
                        pitch=radar_img,
                    )
                h_f, w_f, _ = frame.shape
                radar_img = sv.resize_image(radar_img, (w_f // 2, h_f // 2))
                rh, rw, _ = radar_img.shape
                rect = sv.Rect(x=w_f // 2 - rw // 2, y=h_f - rh, width=rw, height=rh)
                img = sv.draw_image(img, radar_img, opacity=0.5, rect=rect)

            sink.write_frame(img)
            if (idx + 1) % 100 == 0 or (idx + 1) == n_frames_target:
                print(f"  [RADAR] frame {idx + 1}/{n_frames_target}", flush=True)

    timings_per_stage["RADAR_s"] = round(time.perf_counter() - t0, 2)
    _save_json(
        {
            "mode": "RADAR",
            "source_video": args.source,
            "output_video": str(radar_video_path),
            "frames_processed": len(radar_json_frames),
            "elapsed_s": timings_per_stage["RADAR_s"],
            "frames": radar_json_frames,
        },
        json_dir / "RADAR.json",
    )
    print(f"  -> Completado en {timings_per_stage['RADAR_s']} s | JSON + MP4 guardados.")

    # =========================================================================
    # PASO FINAL: PARQUETS + JSON UNIFICADO + VIDEO UNIFICADO (TODOS JUNTOS)
    # =========================================================================
    print("\n[UNIFICADO] Generando Parquets, JSON Maestro y Video Unificado ...")
    t_uni = time.perf_counter()

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

    def _add_obj(f_idx, src_name, xyxy, cls_id, conf_val, tid=None, team=None, pxy=None):
        obj_cols["frame"].append(f_idx)
        obj_cols["t"].append(round(f_idx / fps, 4))
        obj_cols["source"].append(src_name)
        obj_cols["track_id"].append(None if tid is None else int(tid))
        obj_cols["class_id"].append(int(cls_id))
        obj_cols["class_name"].append(CLASS_NAMES.get(int(cls_id), str(cls_id)))
        obj_cols["team"].append(team)
        for col_name, val in zip(["x1", "y1", "x2", "y2"], xyxy):
            obj_cols[col_name].append(float(val))
        obj_cols["conf"].append(None if conf_val is None else float(conf_val))
        obj_cols["pitch_x"].append(None if pxy is None else float(pxy[0]))
        obj_cols["pitch_y"].append(None if pxy is None else float(pxy[1]))

    unified_frames_json = []

    for idx in range(n_frames_target):
        p_info = pitch_per_frame[idx]
        det = player_det_per_frame[idx]
        ball = ball_det_per_frame[idx]
        tracked = tracked_per_frame[idx]
        t_info = team_per_frame[idx]
        r_info = radar_per_frame[idx]

        # Poblar objects.parquet
        for k in range(len(det)):
            _add_obj(idx, "det", det.xyxy[k], det.class_id[k], det.confidence[k])

        for k in range(len(tracked)):
            tid = int(tracked.tracker_id[k])
            _add_obj(
                idx,
                "track",
                tracked.xyxy[k],
                tracked.class_id[k],
                tracked.confidence[k],
                tid=tid,
                team=t_info["team_by_tid"].get(tid),
                pxy=r_info["pxy_by_tid"].get(tid),
            )

        for k in range(len(ball)):
            b_pxy = r_info["ball_xy"][k] if (r_info["ball_xy"] is not None and k < len(r_info["ball_xy"])) else None
            _add_obj(
                idx,
                "ball",
                ball.xyxy[k],
                ball.class_id[k],
                None if ball.confidence is None else ball.confidence[k],
                pxy=b_pxy,
            )

        # Poblar frames.parquet
        H = r_info["H"]
        frm_cols["frame"].append(idx)
        frm_cols["t"].append(round(idx / fps, 4))
        frm_cols["n_det"].append(len(det))
        frm_cols["n_track"].append(len(tracked))
        frm_cols["ball_found"].append(len(ball) > 0)
        frm_cols["homography_valid"].append(H is not None)
        frm_cols["homography_error"].append(r_info["h_error"])
        frm_cols["n_kp_visible"].append(int(p_info["kp_mask"].sum()))
        frm_cols["kp_x"].append([float(v) for v in p_info["kp_xy"][:, 0]])
        frm_cols["kp_y"].append([float(v) for v in p_info["kp_xy"][:, 1]])
        frm_cols["kp_conf"].append([float(v) for v in p_info["kp_conf"]])
        frm_cols["H"].append(None if H is None else [float(v) for v in H.ravel()])

        # Poblar frame unificado JSON
        unified_frames_json.append({
            "frame": idx,
            "t": round(idx / fps, 4),
            "pitch": {
                "n_kp_visible": int(p_info["kp_mask"].sum()),
                "homography_valid": H is not None,
                "homography_error": r_info["h_error"],
            },
            "counts": {
                "n_detections": len(det),
                "n_tracked": len(tracked),
                "ball_found": len(ball) > 0,
            },
            "ball": r_info["projected_balls"][0] if r_info["projected_balls"] else None,
            "players_tracked": r_info["projected_players"],
        })

    # Guardar parquets en out_root
    ec.write_parquet(obj_cols, str(out_root / "objects.parquet"))
    ec.write_parquet(frm_cols, str(out_root / "frames.parquet"))

    # Renderizar VIDEO_UNIFICADO_TODOS_JUNTOS.mp4
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

    gen = sv.get_video_frames_generator(source_path=args.source, end=args.max_frames)
    with sv.VideoSink(str(unified_video_path), video_info) as sink:
        for idx, frame in enumerate(gen):
            img = frame.copy()
            p_info = pitch_per_frame[idx]
            t_info = team_per_frame[idx]
            r_info = radar_per_frame[idx]
            ball = ball_det_per_frame[idx]

            # 1. Keypoints visibles de cancha
            kp_xy = p_info["kp_xy"]
            mask = p_info["kp_mask"]
            if len(kp_xy) > 0 and mask.any():
                img = vertex_annotator.annotate(img, sv.KeyPoints(xy=kp_xy[mask][None]))

            # 2. Jugadores / Porteros / Arbitros con equipo + track_id
            merged = t_info["merged"]
            lookup = t_info["color_lookup"]
            if len(merged) > 0:
                labels = [str(t) for t in merged.tracker_id]
                img = soccer.ELLIPSE_ANNOTATOR.annotate(img, merged, custom_color_lookup=lookup)
                img = soccer.ELLIPSE_LABEL_ANNOTATOR.annotate(
                    img, merged, labels, custom_color_lookup=lookup
                )

            # 3. Balon con rastro
            img = uni_ball_annotator.annotate(img, ball)

            # 4. Radar Cenital 2D superpuesto abajo al centro
            h_f, w_f, _ = frame.shape
            if r_info["H"] is not None and r_info["merged_xy"] is not None:
                radar_img = draw_pitch(config=soccer.CONFIG)
                merged_xy = r_info["merged_xy"]
                for c_idx in range(4):
                    pts = merged_xy[lookup == c_idx] if len(merged_xy) > 0 else np.zeros((0, 2), np.float32)
                    radar_img = draw_points_on_pitch(
                        config=soccer.CONFIG,
                        xy=pts,
                        face_color=colors[c_idx],
                        radius=20,
                        pitch=radar_img,
                    )
                if r_info["ball_xy"] is not None and len(r_info["ball_xy"]) > 0:
                    radar_img = draw_points_on_pitch(
                        config=soccer.CONFIG,
                        xy=r_info["ball_xy"],
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

    timings_per_stage["UNIFIED_EXPORT_s"] = round(time.perf_counter() - t_uni, 2)

    unified_master_json = {
        "project": args.project_label,
        "match": args.match_label,
        "source_video": args.source,
        "resolution": f"{video_info.width}x{video_info.height}",
        "fps": fps,
        "frames_processed": n_frames_target,
        "timings_seconds": timings_per_stage,
        "outputs": {
            "json_por_modelo_dir": str(json_dir),
            "videos_por_modelo_dir": str(video_dir),
            "unified_video": str(unified_video_path),
            "frames_parquet": str(out_root / "frames.parquet"),
            "objects_parquet": str(out_root / "objects.parquet"),
        },
        "summary_metrics": {
            "total_detections_ rows": len(obj_cols["frame"]),
            "ball_found_frames": int(sum(frm_cols["ball_found"])),
            "homography_valid_frames": int(sum(frm_cols["homography_valid"])),
            "homography_valid_rate": round(sum(frm_cols["homography_valid"]) / max(n_frames_target, 1), 4),
        },
        "frames": unified_frames_json,
    }
    _save_json(unified_master_json, out_root / "TELEMETRIA_UNIFICADA_COMPLETA.json")

    print("\n" + "=" * 68)
    print("  PROCESO COMPLETADO CON EXITO")
    print("=" * 68)
    print(f"  1. JSONs por modelo   -> {json_dir}")
    print(f"  2. Videos por modelo  -> {video_dir}")
    print(f"  3. Video Unificado    -> {unified_video_path}")
    print(f"  4. JSON Unificado     -> {out_root / 'TELEMETRIA_UNIFICADA_COMPLETA.json'}")
    print(f"  5. Parquets Pipeline  -> {out_root / 'frames.parquet'} & objects.parquet")
    print("=" * 68)


if __name__ == "__main__":
    main()
