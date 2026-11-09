r"""
scripts/render_post_engine_video.py
===================================
Renderiza:
  1. `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4`: El video final POST-MATEMÁTICA OMNIMORPH
     CON las marcas matemáticas (Moda de Equipo M2.0, Keypoints EMA M2.1, IDs Cosidos M2.2,
     Velocidad Savitzky-Golay M2.3 y HUD de Ventana Táctica M2.4), SIN el radar superpuesto
     (para no tapar la cancha) y CON la pista de audio TTS integrada.
  2. `VIDEO_RADAR_POST_MATEMATICA.mp4`: El video exclusivo del Radar Cenital 2D suavizado
     (Savitzky-Golay + estelas + balón) para visualizarse en el Panel 2 (al lado del video).
  3. `data/audio/NARRACION_COMPLETA_60S.wav` y `data/clean/narrations_es.vtt`: Audio maestro
     continuo y subtítulos WebVTT sincronizados con cada ventana táctica.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time
import wave
from typing import Dict, Tuple

import av
import cv2
import numpy as np
import pandas as pd
import supervision as sv

from sports.annotators.soccer import draw_pitch, draw_points_on_pitch
from sports.configs.soccer import SoccerPitchConfiguration

import sys
import unicodedata

_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from implementacion import partido_config


def _ascii(texto: str) -> str:
    """cv2.putText no dibuja acentos: 'San Cristóbal' -> 'San Cristobal'."""
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")


REFEREE_CLASS_ID = 3
CONFIG = SoccerPitchConfiguration()
COLORS = ["#FF1493", "#00BFFF", "#FF6347", "#FFD700"]

ELLIPSE_ANNOTATOR = sv.EllipseAnnotator(
    color=sv.ColorPalette.from_hex(COLORS),
    thickness=2,
)
ELLIPSE_LABEL_ANNOTATOR = sv.LabelAnnotator(
    color=sv.ColorPalette.from_hex(COLORS),
    text_color=sv.Color.from_hex("#FFFFFF"),
    text_padding=5,
    text_thickness=1,
    text_position=sv.Position.BOTTOM_CENTER,
)


def _format_vtt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def build_master_audio_and_vtt(
    clean_dir: pathlib.Path,
    audio_dir: pathlib.Path,
    total_duration_s: float = 60.0,
) -> Tuple[pathlib.Path | None, pathlib.Path | None]:
    """Construye el audio continuo de 60s y el archivo WebVTT de transcripción."""
    narr_path = clean_dir / "narrations.json"
    if not narr_path.exists():
        return None, None

    with open(narr_path, "r", encoding="utf-8") as f:
        narrations = json.load(f)

    # 1. Generar archivo WebVTT (.vtt)
    vtt_path = clean_dir / "narrations_es.vtt"
    vtt_lines = ["WEBVTT", ""]
    for idx, n in enumerate(narrations, start=1):
        t0 = float(n.get("t0", 0.0))
        t1 = float(n.get("t1", t0 + 4.0))
        wid = n.get("window_id", f"W{idx-1}")
        text = n.get("narracion_es", "").strip()
        if text:
            vtt_lines.append(str(idx))
            vtt_lines.append(f"{_format_vtt_time(t0)} --> {_format_vtt_time(t1)}")
            vtt_lines.append(f"[{wid}] {text}")
            vtt_lines.append("")
    vtt_path.write_text("\n".join(vtt_lines), encoding="utf-8")

    # 2. Ensamblar WAV maestro de 60s posicionando cada W*.wav en su t0
    sample_rate = 22050
    total_samples = int(round(total_duration_s * sample_rate))
    master_pcm = np.zeros(total_samples, dtype=np.int16)
    any_audio = False

    for n in narrations:
        wid = n.get("window_id", "")
        t0 = float(n.get("t0", 0.0))
        wav_path = audio_dir / f"{wid}.wav"
        if not wav_path.exists():
            continue
        with wave.open(str(wav_path), "rb") as wf:
            sr = wf.getframerate()
            n_ch = wf.getnchannels()
            raw = wf.readframes(wf.getnframes())
            samples = np.frombuffer(raw, dtype=np.int16)
            if n_ch > 1:
                samples = samples[::n_ch]
            if sr != sample_rate and len(samples) > 0:
                new_len = int(round(len(samples) * sample_rate / sr))
                samples = np.interp(
                    np.linspace(0, len(samples) - 1, new_len),
                    np.arange(len(samples)),
                    samples,
                ).astype(np.int16)
            start_idx = int(round(t0 * sample_rate))
            end_idx = min(start_idx + len(samples), total_samples)
            if start_idx < total_samples and end_idx > start_idx:
                master_pcm[start_idx:end_idx] = samples[: end_idx - start_idx]
                any_audio = True

    if not any_audio:
        return None, vtt_path

    audio_dir.mkdir(parents=True, exist_ok=True)
    master_wav_path = audio_dir / "NARRACION_COMPLETA_60S.wav"
    with wave.open(str(master_wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(master_pcm.tobytes())

    return master_wav_path, vtt_path


def mux_wav_into_mp4(video_path: pathlib.Path, wav_path: pathlib.Path) -> None:
    """Incrusta la pista de audio WAV (codificada en AAC) dentro del MP4 H.264."""
    tmp_out = video_path.with_suffix(".mux.mp4")
    with av.open(str(video_path)) as v_in, av.open(str(wav_path)) as a_in:
        v_stream_in = v_in.streams.video[0]
        a_stream_in = a_in.streams.audio[0]
        fps = v_stream_in.average_rate  # fracción exacta (p. ej. 30000/1001), no un entero redondeado

        with av.open(str(tmp_out), mode="w", options={"movflags": "faststart"}) as out:
            # Copiar frames de video re-empacados o recodificados rápidos
            v_out = out.add_stream("libx264", rate=fps)
            v_out.width = v_stream_in.width
            v_out.height = v_stream_in.height
            v_out.pix_fmt = "yuv420p"
            v_out.options = {"preset": "veryfast", "crf": "23"}

            a_out = out.add_stream("aac", rate=a_stream_in.rate)
            a_out.layout = "mono"

            for frm in v_in.decode(video=0):
                for pkt in v_out.encode(frm):
                    out.mux(pkt)
            for pkt in v_out.encode():
                out.mux(pkt)

            for afrm in a_in.decode(audio=0):
                afrm.pts = None
                for pkt in a_out.encode(afrm):
                    out.mux(pkt)
            for pkt in a_out.encode():
                out.mux(pkt)

    if tmp_out.exists():
        tmp_out.replace(video_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Renderiza el video estabilizado POST-MATEMATICA (sin radar superpuesto) y el video del Radar 2D"
    )
    parser.add_argument(
        "--source",
        default=partido_config.activo().video_archivo,
    )
    parser.add_argument(
        "--clean-dir",
        default="data/clean",
    )
    parser.add_argument(
        "--outdir",
        default=str(partido_config.activo().percepcion_dir),
    )
    parser.add_argument(
        "--overlay-radar",
        action="store_true",
        help="Si se especifica, incrusta también el radar en la parte inferior del video con marcas",
    )
    args = parser.parse_args()

    clean_dir = pathlib.Path(args.clean_dir)
    audio_dir = clean_dir.parent / "audio"
    out_root = pathlib.Path(args.outdir)
    json_dir = out_root / "json_por_modelo"

    objects_clean_path = clean_dir / "objects_cleaned.parquet"
    frames_clean_path = clean_dir / "frames_clean.parquet"
    tactical_path = clean_dir / "tactical_summaries.json"

    if not objects_clean_path.exists() or not frames_clean_path.exists():
        raise FileNotFoundError(
            "No se encontraron objects_cleaned.parquet o frames_clean.parquet en data/clean/."
        )

    print("=" * 70)
    print("  RENDERIZANDO VIDEO CON MARCAS (SIN RADAR) + VIDEO RADAR 2D + AUDIO TTS")
    print("=" * 70)
    t0 = time.perf_counter()

    df_obj = pd.read_parquet(objects_clean_path)
    df_frm = pd.read_parquet(frames_clean_path)
    with open(tactical_path, "r", encoding="utf-8") as f:
        tactical_windows = json.load(f)

    j_pitch_path = json_dir / "PITCH_DETECTION.json"
    j_pitch = None
    if j_pitch_path.exists():
        with open(j_pitch_path, "r", encoding="utf-8") as f:
            j_pitch = json.load(f)

    df_tracks = df_obj[df_obj["source"] == "track"].copy()
    df_balls = df_obj[df_obj["source"] == "ball"].copy()

    orig_team_mode: Dict[int, int] = {}
    for tid, grp in df_tracks.groupby("track_id"):
        if pd.isna(tid):
            continue
        t_vals = grp["team"].dropna()
        if len(t_vals) > 0:
            orig_team_mode[int(tid)] = int(t_vals.mode().iloc[0])

    df_tracks = df_tracks.sort_values(["track_id", "frame"]).reset_index(drop=True)
    bbox_alpha = 0.55
    for col in ["x1", "y1", "x2", "y2"]:
        df_tracks[f"{col}_ema"] = (
            df_tracks.groupby("track_id")[col]
            .transform(lambda s: s.ewm(alpha=bbox_alpha, adjust=False).mean())
        )

    ball_by_frame: Dict[int, Tuple[float, float, float, float, float, float]] = {}
    if len(df_balls) > 0:
        df_balls_best = (
            df_balls.sort_values(["frame", "conf"], ascending=[True, False])
            .drop_duplicates(subset=["frame"], keep="first")
            .set_index("frame")
        )
        full_idx = pd.Index(range(len(df_frm)), name="frame")
        df_b_interp = df_balls_best[["x1", "y1", "x2", "y2", "pitch_x_smooth", "pitch_y_smooth"]].reindex(full_idx)
        df_b_interp = df_b_interp.interpolate(method="linear", limit=10)
        for f_idx, row in df_b_interp.dropna().iterrows():
            ball_by_frame[int(f_idx)] = (
                float(row["x1"]),
                float(row["y1"]),
                float(row["x2"]),
                float(row["y2"]),
                float(row["pitch_x_smooth"]),
                float(row["pitch_y_smooth"]),
            )

    tracks_by_frame = {f_idx: grp for f_idx, grp in df_tracks.groupby("frame")}
    frm_by_idx = df_frm.set_index("frame").to_dict(orient="index")

    raw_info = sv.VideoInfo.from_video_path(args.source)
    n_frames_target = len(df_frm)
    # supervision trunca los fps a entero (29.97 -> 29) y desfasa el video del audio y los subtítulos.
    with av.open(args.source) as _src:
        fps_exacto = _src.streams.video[0].average_rate
    fps = float(fps_exacto)

    # Construir audio maestro 60s y subtítulos WebVTT
    master_wav, vtt_path = build_master_audio_and_vtt(
        clean_dir, audio_dir, total_duration_s=n_frames_target / fps
    )
    if master_wav:
        print(f"  [AUDIO] Audio maestro generado -> {master_wav}")
    if vtt_path:
        print(f"  [VTT]   Subtítulos WebVTT      -> {vtt_path}")

    out_video_path = out_root / "VIDEO_OMNIMORPH_POST_MATEMATICA.mp4"
    out_radar_path = out_root / "VIDEO_RADAR_POST_MATEMATICA.mp4"

    vertex_annotator = sv.VertexAnnotator(color=sv.Color.from_hex("#A020F0"), radius=6)
    colors = [sv.Color.from_hex(c) for c in COLORS]

    eq0, eq1 = partido_config.activo().equipos
    legend = [
        (f"{_ascii(eq0.nombre)} (Moda M2.0)", colors[0]),
        (f"{_ascii(eq1.nombre)} (Moda M2.0)", colors[1]),
        ("Arbitro", colors[3]),
        ("Homografia EMA (M2.1)", sv.Color.from_hex("#A020F0")),
        ("Balon Suavizado (M2.3)", sv.Color.from_hex("#FFA500")),
    ]

    radar_trail_history: list[Tuple[np.ndarray, np.ndarray]] = []
    ball_screen_trail: list[Tuple[int, int]] = []

    base_pitch = draw_pitch(config=CONFIG)
    rad_h, rad_w, _ = base_pitch.shape
    # Asegurar dimensiones pares para H.264 yuv420p
    rad_w_even = (rad_w // 2) * 2
    rad_h_even = (rad_h // 2) * 2

    gen = sv.get_video_frames_generator(source_path=args.source, end=n_frames_target)
    with (
        av.open(str(out_video_path), mode="w", options={"movflags": "faststart"}) as v_container,
        av.open(str(out_radar_path), mode="w", options={"movflags": "faststart"}) as r_container,
    ):
        v_stream = v_container.add_stream("libx264", rate=fps_exacto)
        v_stream.width = raw_info.width
        v_stream.height = raw_info.height
        v_stream.pix_fmt = "yuv420p"
        v_stream.options = {"preset": "veryfast", "crf": "23"}

        r_stream = r_container.add_stream("libx264", rate=fps_exacto)
        r_stream.width = rad_w_even
        r_stream.height = rad_h_even
        r_stream.pix_fmt = "yuv420p"
        r_stream.options = {"preset": "veryfast", "crf": "23"}

        for idx, frame in enumerate(gen):
            img = frame.copy()
            h_f, w_f, _ = img.shape
            f_meta = frm_by_idx.get(idx, {})
            is_wide_shot = bool(f_meta.get("homography_valid", False))

            # 1. Keypoints visibles (solo en toma abierta válida)
            if is_wide_shot and j_pitch is not None and idx < len(j_pitch["frames"]):
                fp = j_pitch["frames"][idx]
                if fp["kp_x"]:
                    xy = np.stack([fp["kp_x"], fp["kp_y"]], axis=1).astype(np.float32)
                    vis = (xy[:, 0] > 1) & (xy[:, 1] > 1)
                    if vis.any():
                        img = vertex_annotator.annotate(img, sv.KeyPoints(xy=xy[vis][None]))

            # 2. Jugadores con cajas EMA + Equipo estabilizado (M2.0) + ID Cosido (M2.2) + Velocidad (M2.3)
            grp = tracks_by_frame.get(idx)
            lookup = np.array([], dtype=int)
            if grp is not None and len(grp) > 0:
                xyxy_arr = grp[["x1_ema", "y1_ema", "x2_ema", "y2_ema"]].to_numpy(dtype=np.float32)
                cls_arr = grp["class_id"].to_numpy(dtype=int)
                stitched_arr = grp["track_id_stitched"].fillna(grp["track_id"]).to_numpy(dtype=int)

                lookup_list = []
                labels_list = []
                for _, r in grp.iterrows():
                    orig_tid = int(r["track_id"]) if pd.notna(r["track_id"]) else -1
                    stid = int(r["track_id_stitched"]) if pd.notna(r["track_id_stitched"]) else orig_tid
                    cls_id = int(r["class_id"])
                    if cls_id == REFEREE_CLASS_ID:
                        t_clean = REFEREE_CLASS_ID
                    else:
                        t_clean = orig_team_mode.get(orig_tid, r.get("team"))
                        if pd.isna(t_clean) or t_clean not in (0, 1):
                            t_clean = 0
                        else:
                            t_clean = int(t_clean)
                    lookup_list.append(t_clean)
                    # Sin velocidad por jugador: la homografía salta entre cuadros y la
                    # velocidad instantánea sale topada en 9.5 m/s (diagnóstico en la sesión 13).
                    labels_list.append(f"#{stid}")

                dets = sv.Detections(
                    xyxy=xyxy_arr,
                    class_id=cls_arr,
                    tracker_id=stitched_arr,
                )
                lookup = np.array(lookup_list, dtype=int)
                img = ELLIPSE_ANNOTATOR.annotate(img, dets, custom_color_lookup=lookup)
                img = ELLIPSE_LABEL_ANNOTATOR.annotate(
                    img, dets, labels_list, custom_color_lookup=lookup
                )

            # 3. Balón interpolado con estela suave
            if idx in ball_by_frame and is_wide_shot:
                bx1, by1, bx2, by2, bpx, bpy = ball_by_frame[idx]
                bcx, bcy = int((bx1 + bx2) / 2), int((by1 + by2) / 2)
                ball_screen_trail.append((bcx, bcy))
                if len(ball_screen_trail) > 12:
                    ball_screen_trail.pop(0)
                for t_i, (tx, ty) in enumerate(ball_screen_trail):
                    rad = max(2, int(2 + (t_i / len(ball_screen_trail)) * 5))
                    cv2.circle(img, (tx, ty), rad, (0, 165, 255), -1)
                cv2.circle(img, (bcx, bcy), 8, (0, 255, 255), 2)
            else:
                if len(ball_screen_trail) > 0:
                    ball_screen_trail.pop(0)

            # 4. Radar Cenital 2D Post-Savitzky-Golay (para el video independiente del Panel 2)
            radar_img = base_pitch.copy()
            if grp is not None and len(grp) > 0 and is_wide_shot:
                pxy = grp[["pitch_x_smooth", "pitch_y_smooth"]].to_numpy(dtype=np.float32)
                in_bounds = (
                    (pxy[:, 0] >= 0) & (pxy[:, 0] <= 12000) &
                    (pxy[:, 1] >= 0) & (pxy[:, 1] <= 7000)
                )
                pxy_valid = pxy[in_bounds]
                lk_valid = lookup[in_bounds]

                radar_trail_history.append((pxy_valid.copy(), lk_valid.copy()))
                if len(radar_trail_history) > 8:
                    radar_trail_history.pop(0)

                for past_pxy, past_lk in radar_trail_history[:-1]:
                    for c_idx in range(4):
                        pts_past = past_pxy[past_lk == c_idx]
                        if len(pts_past) > 0:
                            radar_img = draw_points_on_pitch(
                                config=CONFIG,
                                xy=pts_past,
                                face_color=colors[c_idx],
                                edge_color=colors[c_idx],
                                radius=9,
                                pitch=radar_img,
                            )

                for c_idx in range(4):
                    pts = pxy_valid[lk_valid == c_idx]
                    if len(pts) > 0:
                        radar_img = draw_points_on_pitch(
                            config=CONFIG,
                            xy=pts,
                            face_color=colors[c_idx],
                            radius=20,
                            pitch=radar_img,
                        )

                if idx in ball_by_frame:
                    _, _, _, _, bpx, bpy = ball_by_frame[idx]
                    if 0 <= bpx <= 12000 and 0 <= bpy <= 7000:
                        bxy = np.array([[bpx, bpy]], dtype=np.float32)
                        radar_img = draw_points_on_pitch(
                            config=CONFIG,
                            xy=bxy,
                            face_color=sv.Color.WHITE,
                            edge_color=sv.Color.BLACK,
                            radius=15,
                            pitch=radar_img,
                        )
            elif len(radar_trail_history) > 0:
                last_pxy, last_lk = radar_trail_history[-1]
                for c_idx in range(4):
                    pts = last_pxy[last_lk == c_idx]
                    if len(pts) > 0:
                        radar_img = draw_points_on_pitch(
                            config=CONFIG,
                            xy=pts,
                            face_color=colors[c_idx],
                            radius=18,
                            pitch=radar_img,
                        )

            t_cur = idx / fps
            cam_tag = "TOMA ABIERTA (H_ema ACTIVA)" if is_wide_shot else "TOMA CERRADA / REPLAY (HOLD EMA)"
            tag_col = (50, 220, 100) if is_wide_shot else (0, 180, 255)

            # Encabezado en el video independiente del Radar 2D
            radar_frame = radar_img[:rad_h_even, :rad_w_even].copy()
            cv2.rectangle(radar_frame, (10, 10), (620, 48), (15, 23, 42), -1)
            cv2.putText(
                radar_frame,
                f"Frame {idx + 1}/{n_frames_target} ({t_cur:.1f}s) | {cam_tag}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.62,
                tag_col,
                2,
            )

            # Solo incrustar en el video principal si se pidió explícitamente --overlay-radar
            if args.overlay_radar:
                rw_max = int(w_f * 0.25)
                radar_small = sv.resize_image(radar_img, (rw_max, h_f), keep_aspect_ratio=True)
                rh, rw, _ = radar_small.shape
                rx1 = w_f // 2 - rw // 2
                ry1 = h_f - rh - 10
                img = sv.draw_image(
                    img,
                    radar_small,
                    opacity=0.72,
                    rect=sv.Rect(x=rx1, y=ry1, width=rw, height=rh),
                )

            # 5. Panel de Ventana Táctica (arriba a la derecha, compacto)
            active_w = next((w for w in tactical_windows if w["t0"] <= t_cur < w["t1"]), tactical_windows[-1])
            w_box_w, w_box_h = 295, 78
            wx1, wy1 = w_f - w_box_w - 15, 15
            overlay_top = img.copy()
            cv2.rectangle(overlay_top, (wx1, wy1), (wx1 + w_box_w, wy1 + w_box_h), (15, 23, 42), -1)
            cv2.addWeighted(overlay_top, 0.72, img, 0.28, 0, img)
            cv2.putText(
                img,
                f"Omnimorph Engine | Ventana {active_w['window_id']}",
                (wx1 + 12, wy1 + 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (100, 220, 255),
                1,
            )
            cv2.putText(
                img,
                f"Altura bloque: {active_w['block_height_m']:.1f} m | Compac: {active_w['block_compactness_m']:.1f} m",
                (wx1 + 12, wy1 + 48),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.44,
                (255, 255, 255),
                1,
            )
            cv2.putText(
                img,
                f"Presion: {active_w['pressure_context']} | ventana {active_w['t0']:.1f}-{active_w['t1']:.1f} s",
                (wx1 + 12, wy1 + 68),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (180, 255, 180),
                1,
            )

            # 6. Leyenda en la esquina INFERIOR DERECHA
            box_w = 285
            box_h = 46 + 26 * len(legend)
            x1_box = w_f - box_w - 15
            y1_box = h_f - box_h - 15
            x2_box = w_f - 15
            y2_box = h_f - 15

            overlay = img.copy()
            cv2.rectangle(overlay, (x1_box, y1_box), (x2_box, y2_box), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)

            cv2.putText(
                img,
                f"Frame {idx + 1}/{n_frames_target} ({t_cur:.1f}s) [POST-MATH]",
                (x1_box + 12, y1_box + 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.50,
                (255, 255, 255),
                2,
            )
            for l_i, (text, col) in enumerate(legend):
                y_pos = y1_box + 54 + 26 * l_i
                cv2.circle(img, (x1_box + 22, y_pos - 5), 7, col.as_bgr(), -1)
                cv2.putText(
                    img, text, (x1_box + 38, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2
                )

            v_frame = av.VideoFrame.from_ndarray(img, format="bgr24")
            for pkt in v_stream.encode(v_frame):
                v_container.mux(pkt)

            r_frame = av.VideoFrame.from_ndarray(radar_frame, format="bgr24")
            for pkt in r_stream.encode(r_frame):
                r_container.mux(pkt)

            if (idx + 1) % 300 == 0 or (idx + 1) == n_frames_target:
                print(f"  [POST-MATH & RADAR] frame {idx + 1}/{n_frames_target}", flush=True)

        for pkt in v_stream.encode():
            v_container.mux(pkt)
        for pkt in r_stream.encode():
            r_container.mux(pkt)

    # Incrustar el audio maestro TTS dentro del video principal con marcas
    if master_wav and master_wav.exists():
        print("  [AUDIO MUX] Incrustando narración TTS en VIDEO_OMNIMORPH_POST_MATEMATICA.mp4...")
        mux_wav_into_mp4(out_video_path, master_wav)

    elapsed = round(time.perf_counter() - t0, 2)
    print("\n" + "=" * 70)
    print(f"  VIDEOS Y AUDIO GENERADOS EN {elapsed} s")
    print(f"  Video con Marcas (sin radar) -> {out_video_path}")
    print(f"  Video Radar 2D               -> {out_radar_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
