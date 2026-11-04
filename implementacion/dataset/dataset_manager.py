"""
implementacion/dataset/dataset_manager.py
==========================================
ETAPA 1 — Ingesta del dataset Omnimorph.

Funciones principales:
  - download_hf_parquets(dest_dir)        → descarga desde HuggingFace bajo demanda
  - load_local_parquets(raw_dir)          → carga archivos .parquet locales existentes
  - generate_sample_parquets(raw_dir)     → genera telemetría sintética realista (750 frames)
  - get_parquets(raw_dir, force_generate) → punto de entrada unificado

Esquemas exactos de las tablas:
  frames.parquet  : frame, t, n_det, n_track, ball_found, homography_valid,
                    homography_error, n_kp_visible, kp_x, kp_y, kp_conf, H
  objects.parquet : frame, t, source, track_id, class_id, class_name, team,
                    x1, y1, x2, y2, conf, pitch_x, pitch_y
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes de referencia
# ---------------------------------------------------------------------------
CLIP_NAME = "2e57b9_0.mp4"
N_FRAMES = 750
FPS = 25.0
PITCH_L_CM = 12_000   # largo de cancha en cm (eje X)
PITCH_W_CM = 7_000    # ancho de cancha en cm (eje Y)
HF_DATASET = "QimingLi/video_human_select_Soccer"
HF_DATA_DIR = "Soccer"

# Partido de referencia seleccionado para las pruebas del MVP:
# L6sbfskaTDQ -> Semifinal Mundial FIFA Brasil 2014 (Brasil vs. Alemania 1-7)
DEFAULT_HF_MATCH_PREFIX = "L6sbfskaTDQ"
DEFAULT_HF_RESOLUTION = "720"

HF_MATCH_CATALOG = {
    "L6sbfskaTDQ": {
        "match": "Brasil vs. Alemania (1-7)",
        "competition": "Mundial FIFA Brasil 2014 — Semifinal",
        "home": "BRA",
        "away": "GER",
        "home_kit": "Amarillo / Azul",
        "away_kit": "Negro / Rojo",
    },
    "7GL2KvcCrfk": {
        "match": "Seattle Sounders vs. Vancouver Whitecaps",
        "competition": "MLS Cup Playoffs 2017",
        "home": "SEA",
        "away": "VAN",
    },
    "HP3zxNuoWXE": {
        "match": "Costa Rica vs. San Cristóbal y Nieves",
        "competition": "Eliminatorias Mundial FIFA 2026",
        "home": "CRC",
        "away": "SKN",
    },
    "W7f7ZQEa9M4": {
        "match": "Islas Vírgenes Británicas vs. Guatemala",
        "competition": "Eliminatorias Mundial FIFA 2026",
        "home": "VGB",
        "away": "GUA",
    },
    "jBUiUnHV00s": {
        "match": "Alemania vs. Suecia",
        "competition": "Final Mundial Femenino FIFA 2003",
        "home": "GER",
        "away": "SWE",
    },
}

# Semilla fija para reproducibilidad
RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# 1. Descarga bajo demanda desde Hugging Face
# ---------------------------------------------------------------------------

def list_hf_soccer_videos(
    match_prefix: Optional[str] = DEFAULT_HF_MATCH_PREFIX,
    resolution: Optional[str] = DEFAULT_HF_RESOLUTION,
) -> list[dict]:
    """
    Lista los videos (.mp4) disponibles en la carpeta Soccer/ del dataset
    QimingLi/video_human_select_Soccer en HuggingFace, con su tamaño en MB.

    Por defecto filtra el partido del Mundial FIFA Brasil 2014 (L6sbfskaTDQ)
    en resolución 720p (15 clips). Pasa match_prefix=None para ver los 150.
    """
    try:
        from huggingface_hub import HfApi
    except ImportError:
        print("[dataset_manager] huggingface_hub no disponible.")
        return []

    api = HfApi()
    try:
        tree = api.list_repo_tree(
            repo_id=HF_DATASET,
            path_in_repo=HF_DATA_DIR,
            repo_type="dataset",
        )
        videos = []
        for item in tree:
            path = getattr(item, "path", getattr(item, "rfilename", ""))
            size = getattr(item, "size", 0) or 0
            if path.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                fname = pathlib.Path(path).name
                if match_prefix and not fname.startswith(match_prefix):
                    continue
                if resolution and f"-{resolution}-" not in fname:
                    continue
                prefix_id = fname.split("-")[0]
                meta = HF_MATCH_CATALOG.get(prefix_id, {})
                videos.append({
                    "path": path,
                    "filename": fname,
                    "size_mb": round(size / (1024 * 1024), 2),
                    "match_id": prefix_id,
                    "match": meta.get("match", "Desconocido"),
                    "competition": meta.get("competition", ""),
                })
        return videos
    except Exception as exc:
        print(f"[dataset_manager] Error listando videos en HF: {exc}")
        return []


def download_hf_soccer_videos(
    dest_dir: Optional[str] = None,
    max_videos: Optional[int] = None,
    filenames: Optional[list[str]] = None,
    match_prefix: Optional[str] = DEFAULT_HF_MATCH_PREFIX,
    resolution: Optional[str] = DEFAULT_HF_RESOLUTION,
    clean_other_matches: bool = False,
) -> list[pathlib.Path]:
    """
    Descarga los videos .mp4 de QimingLi/video_human_select_Soccer (carpeta Soccer/)
    hacia la carpeta de calidad correspondiente:
      - Alta calidad (720p HD): data/videos/mundial_2014_720p_hd/
      - Baja calidad (480p SD): data/videos/mundial_2014_480p_sd/
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[dataset_manager] huggingface_hub no disponible — saltando descarga de videos.")
        return []

    if dest_dir is None:
        if resolution == "480":
            dest_dir = "data/videos/mundial_2014_480p_sd"
        else:
            dest_dir = "data/videos/mundial_2014_720p_hd"

    dest = pathlib.Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    if clean_other_matches and match_prefix:
        removed = 0
        for f in dest.glob("*"):
            if f.is_file() and f.name not in (".gitignore", "CACHEDIR.TAG") and not f.name.startswith(match_prefix):
                try:
                    f.unlink()
                    removed += 1
                except Exception:
                    pass
        if removed:
            print(f"[dataset_manager] Limpiados {removed} archivos de otros partidos en {dest}")

    # Si se especifican filenames explícitos, no restringir por match_prefix/resolution
    eff_prefix = None if filenames else match_prefix
    eff_res = None if filenames else resolution

    videos = list_hf_soccer_videos(match_prefix=eff_prefix, resolution=eff_res)
    if not videos:
        print("[dataset_manager] No se encontraron videos en HF o sin conexión.")
        return []

    if filenames:
        target_set = set(filenames)
        videos = [v for v in videos if v["filename"] in target_set or v["path"] in target_set]

    if max_videos is not None:
        videos = videos[:max_videos]

    downloaded_paths: list[pathlib.Path] = []
    for i, v in enumerate(videos, 1):
        remote_path = v["path"]
        local_file = dest / v["filename"]
        if local_file.exists() and local_file.stat().st_size > 0:
            print(f"[dataset_manager] [{i}/{len(videos)}] Ya existe: {local_file} ({v['size_mb']} MB)")
            downloaded_paths.append(local_file)
            continue

        print(f"[dataset_manager] [{i}/{len(videos)}] Descargando {remote_path} ({v['size_mb']} MB) …")
        try:
            cached = hf_hub_download(
                repo_id=HF_DATASET,
                filename=remote_path,
                repo_type="dataset",
                local_dir=str(dest),
            )
            src = pathlib.Path(cached)
            if src.exists() and src.resolve() != local_file.resolve():
                import shutil
                shutil.move(str(src), str(local_file))
                # Limpiar subdirectorio Soccer/ vacío si hf_hub_download lo creó
                sub_dir = dest / HF_DATA_DIR
                if sub_dir.exists() and sub_dir.is_dir() and not any(sub_dir.iterdir()):
                    sub_dir.rmdir()
            downloaded_paths.append(local_file)
            print(f"[dataset_manager] Guardado → {local_file}")
        except Exception as exc:
            print(f"[dataset_manager] Error descargando {remote_path}: {exc}")

    return downloaded_paths


def download_hf_parquets(dest_dir: str = "data/raw") -> bool:
    """
    Intenta descargar frames.parquet y objects.parquet desde el dataset
    QimingLi/video_human_select_Soccer (carpeta Soccer/) en HuggingFace.

    Devuelve True si tuvo éxito, False si el paquete no está disponible.
    Las credenciales de HF se leen de HF_TOKEN en el entorno (opcional).
    """
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[dataset_manager] huggingface_hub no disponible — saltando descarga HF.")
        return False

    dest = pathlib.Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    files_to_fetch = [
        (f"{HF_DATA_DIR}/frames.parquet", "frames.parquet"),
        (f"{HF_DATA_DIR}/objects.parquet", "objects.parquet"),
    ]

    try:
        for remote_path, local_name in files_to_fetch:
            local_file = dest / local_name
            if local_file.exists():
                print(f"[dataset_manager] Ya existe: {local_file}")
                continue
            print(f"[dataset_manager] Descargando {remote_path} desde HF …")
            downloaded = hf_hub_download(
                repo_id=HF_DATASET,
                filename=remote_path,
                repo_type="dataset",
                local_dir=str(dest),
            )
            # El archivo puede descargarse a una ruta de caché; moverlo
            src = pathlib.Path(downloaded)
            if src != local_file:
                import shutil
                shutil.move(str(src), str(local_file))
            print(f"[dataset_manager] Descargado → {local_file}")
        return True
    except Exception as exc:
        print(f"[dataset_manager] Error descargando desde HF: {exc}")
        return False


# ---------------------------------------------------------------------------
# 2. Carga de parquets locales
# ---------------------------------------------------------------------------

def load_local_parquets(
    raw_dir: str = "data/raw",
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Carga frames.parquet y objects.parquet desde raw_dir.
    Devuelve (df_frames, df_objects) o (None, None) si no existen.
    """
    frames_path = pathlib.Path(raw_dir) / "frames.parquet"
    objects_path = pathlib.Path(raw_dir) / "objects.parquet"

    if not frames_path.exists() or not objects_path.exists():
        return None, None

    try:
        df_frames = pd.read_parquet(str(frames_path))
        df_objects = pd.read_parquet(str(objects_path))
        print(f"[dataset_manager] Parquets cargados: {len(df_frames)} frames, "
              f"{len(df_objects)} objetos.")
        return df_frames, df_objects
    except Exception as exc:
        print(f"[dataset_manager] Error cargando parquets: {exc}")
        return None, None


# ---------------------------------------------------------------------------
# 3. Generador de telemetría sintética realista (750 frames)
# ---------------------------------------------------------------------------

def generate_sample_parquets(raw_dir: str = "data/raw") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Genera frames.parquet y objects.parquet con telemetría sintética realista.
    Cubre el caso testigo track_id=19 en el frame 300 y fragmentación de tracks.

    frames.parquet — 750 filas con columnas:
      frame, t, n_det, n_track, ball_found, homography_valid, homography_error,
      n_kp_visible, kp_x, kp_y, kp_conf, H

    objects.parquet — múltiples filas con columnas:
      frame, t, source [det|track|ball], track_id, class_id, class_name,
      team, x1, y1, x2, y2, conf, pitch_x, pitch_y
    """
    dest = pathlib.Path(raw_dir)
    dest.mkdir(parents=True, exist_ok=True)

    print("[dataset_manager] Generando telemetría sintética (750 frames) …")

    frames_rows = []
    objects_rows = []

    # Número de jugadores "reales" por equipo (10 de campo + 1 portero)
    n_arg = 11  # team_id=0
    n_fra = 11  # team_id=1
    n_ref = 1   # árbitro

    # Posiciones iniciales realistas en cm (cancha 12000×7000)
    # ARG empieza en mitad propia (x < 6000)
    arg_positions = np.array([
        [1000, 3500],   # GK ARG
        [2500, 1500], [2500, 5500],   # defensas
        [3500, 2000], [3500, 3500], [3500, 5000],  # mediocampistas defensivos
        [4500, 2500], [4500, 4500],   # medios
        [5500, 2000], [5500, 4000], [5500, 5500],  # delanteros
    ], dtype=float)

    fra_positions = np.array([
        [11000, 3500],  # GK FRA
        [9500, 1500], [9500, 5500],  # defensas FRA
        [8500, 2000], [8500, 3500], [8500, 5000],  # medios defensivos
        [7500, 2500], [7500, 4500],  # medios
        [6500, 2000], [6500, 4000], [6500, 5500],  # delanteros FRA
    ], dtype=float)

    ref_pos = np.array([[6000, 1200]], dtype=float)  # árbitro centro

    # track_ids fijos base (simula ByteTrack con IDs desde 1)
    # ARG: ids 1–11, FRA: ids 12–22, árbitro: 23
    # Fragmentación: en el frame 150, track_id=5 (ARG) se rompe y nace track_id=25
    # En frame 400, track_id=20 (FRA) se rompe → track_id=28
    arg_ids = list(range(1, 12))   # 1..11
    fra_ids = list(range(12, 23))  # 12..22
    ref_id = 23

    # class_ids: 0=player, 1=goalkeeper, 2=referee
    arg_class_ids = [1] + [0] * 10      # ARG: GK + 10 jugadores
    fra_class_ids = [1] + [0] * 10      # FRA: GK + 10 jugadores
    ref_class_ids = [2]

    # Velocidades base en cm/frame (movimiento browniano en cancha)
    arg_vel = RNG.uniform(-30, 30, (n_arg, 2))
    fra_vel = RNG.uniform(-30, 30, (n_fra, 2))
    ref_vel = RNG.uniform(-10, 10, (n_ref, 2))

    # Balón — trayectoria paramétrica
    ball_x0, ball_y0 = 6000.0, 3500.0
    ball_vx, ball_vy = 150.0, 80.0  # cm/frame

    # Homografía base (identidad escalada para 1920×1080 → 12000×7000)
    H_base = np.array([
        [PITCH_L_CM / 1920, 0, 0],
        [0, PITCH_W_CM / 1080, 0],
        [0, 0, 1],
    ], dtype=float)

    for frame in range(N_FRAMES):
        t = frame / FPS

        # --- Mover jugadores (movimiento browniano con rebote en bordes) ---
        arg_vel += RNG.normal(0, 5, (n_arg, 2))
        arg_vel = np.clip(arg_vel, -60, 60)
        arg_positions += arg_vel
        arg_positions[:, 0] = np.clip(arg_positions[:, 0], 50, PITCH_L_CM - 50)
        arg_positions[:, 1] = np.clip(arg_positions[:, 1], 50, PITCH_W_CM - 50)

        fra_vel += RNG.normal(0, 5, (n_fra, 2))
        fra_vel = np.clip(fra_vel, -60, 60)
        fra_positions += fra_vel
        fra_positions[:, 0] = np.clip(fra_positions[:, 0], 50, PITCH_L_CM - 50)
        fra_positions[:, 1] = np.clip(fra_positions[:, 1], 50, PITCH_W_CM - 50)

        ref_vel += RNG.normal(0, 2, (n_ref, 2))
        ref_vel = np.clip(ref_vel, -20, 20)
        ref_pos += ref_vel
        ref_pos[:, 0] = np.clip(ref_pos[:, 0], 50, PITCH_L_CM - 50)
        ref_pos[:, 1] = np.clip(ref_pos[:, 1], 50, PITCH_W_CM - 50)

        # --- Balón ---
        bx = ball_x0 + ball_vx * frame + 400 * np.sin(frame * 0.05)
        by = ball_y0 + ball_vy * np.sin(frame * 0.03) * 30
        bx = float(np.clip(bx % PITCH_L_CM, 200, PITCH_L_CM - 200))
        by = float(np.clip(by, 200, PITCH_W_CM - 200))
        ball_found = True
        if frame > 500 and frame % 17 == 0:  # simula pérdida ocasional
            ball_found = False

        # Homografía con ligero ruido
        H = H_base.copy()
        H += RNG.normal(0, 0.0001, H.shape)
        H[2, 2] = 1.0  # normalizar
        homography_valid = True
        homography_error = float(RNG.uniform(0.5, 2.5))
        n_kp_visible = int(RNG.integers(18, 33))

        # kp_x, kp_y, kp_conf (32 keypoints)
        kp_x = list(RNG.uniform(0, 1920, 32).round(2))
        kp_y = list(RNG.uniform(0, 1080, 32).round(2))
        kp_conf = list(RNG.uniform(0.5, 1.0, 32).round(3))
        # Keypoints fuera de cancha (simulación de puntos no visibles)
        for ki in range(n_kp_visible, 32):
            kp_conf[ki] = 0.0

        n_det = n_arg + n_fra + n_ref + (1 if ball_found else 0)
        n_track = n_arg + n_fra  # árbitro no se trackea por ID en ByteTrack típico

        frames_rows.append({
            "frame": frame,
            "t": round(t, 4),
            "n_det": n_det,
            "n_track": n_track,
            "ball_found": ball_found,
            "homography_valid": homography_valid,
            "homography_error": round(homography_error, 4),
            "n_kp_visible": n_kp_visible,
            "kp_x": kp_x,
            "kp_y": kp_y,
            "kp_conf": kp_conf,
            "H": list(H.flatten().round(6)),
        })

        # --- Construir filas de objects ---
        def _pitch_to_px(px_cm: float, py_cm: float):
            """Proyección inversa simple para BBox en píxeles."""
            px = px_cm / PITCH_L_CM * 1920
            py = py_cm / PITCH_W_CM * 1080
            return float(np.clip(px, 0, 1920)), float(np.clip(py, 0, 1080))

        def add_player_rows(
            pos_arr, vel_arr, ids, class_ids, team_id, source_label="track"
        ):
            for i, (tid, cid) in enumerate(zip(ids, class_ids)):
                # Simula fragmentación: track_id=5 → 25 en frame 150
                # track_id=20 → 28 en frame 400
                effective_tid = tid
                if tid == 5 and frame >= 150:
                    effective_tid = 25
                if tid == 20 and frame >= 400:
                    effective_tid = 28

                px_cm = float(pos_arr[i, 0])
                py_cm = float(pos_arr[i, 1])
                bx_px, by_px = _pitch_to_px(px_cm, py_cm)
                w, h = 30.0, 60.0  # tamaño aprox de BBox en píxeles
                conf = float(RNG.uniform(0.85, 0.96))
                class_name = "player" if cid == 0 else ("goalkeeper" if cid == 1 else "referee")

                # Caso testigo: track_id=19 en frame 300
                if tid == 19 - 11 + 12 and frame == 300:  # tid=19 es FRA índice 7
                    # Forzar posición exacta del caso testigo
                    px_cm = 7877.0
                    py_cm = 6540.7
                    bx_px, by_px = _pitch_to_px(px_cm, py_cm)

                # det row
                objects_rows.append({
                    "frame": frame, "t": round(t, 4),
                    "source": "det",
                    "track_id": None,
                    "class_id": cid, "class_name": class_name,
                    "team": team_id,
                    "x1": round(bx_px - w/2, 1), "y1": round(by_px - h/2, 1),
                    "x2": round(bx_px + w/2, 1), "y2": round(by_px + h/2, 1),
                    "conf": round(conf, 4),
                    "pitch_x": round(px_cm, 2),
                    "pitch_y": round(py_cm, 2),
                })
                # track row
                objects_rows.append({
                    "frame": frame, "t": round(t, 4),
                    "source": source_label,
                    "track_id": effective_tid,
                    "class_id": cid, "class_name": class_name,
                    "team": team_id,
                    "x1": round(bx_px - w/2, 1), "y1": round(by_px - h/2, 1),
                    "x2": round(bx_px + w/2, 1), "y2": round(by_px + h/2, 1),
                    "conf": round(conf, 4),
                    "pitch_x": round(px_cm, 2),
                    "pitch_y": round(py_cm, 2),
                })

        add_player_rows(arg_positions, arg_vel, arg_ids, arg_class_ids, team_id=0)
        add_player_rows(fra_positions, fra_vel, fra_ids, fra_class_ids, team_id=1)

        # Árbitro (solo det, sin team)
        ref_px_cm = float(ref_pos[0, 0])
        ref_py_cm = float(ref_pos[0, 1])
        rbx_px, rby_px = _pitch_to_px(ref_px_cm, ref_py_cm)
        objects_rows.append({
            "frame": frame, "t": round(t, 4),
            "source": "det",
            "track_id": None,
            "class_id": 2, "class_name": "referee",
            "team": None,
            "x1": round(rbx_px - 15, 1), "y1": round(rby_px - 30, 1),
            "x2": round(rbx_px + 15, 1), "y2": round(rby_px + 30, 1),
            "conf": round(float(RNG.uniform(0.82, 0.92)), 4),
            "pitch_x": round(ref_px_cm, 2),
            "pitch_y": round(ref_py_cm, 2),
        })
        objects_rows.append({
            "frame": frame, "t": round(t, 4),
            "source": "track",
            "track_id": ref_id,
            "class_id": 2, "class_name": "referee",
            "team": None,
            "x1": round(rbx_px - 15, 1), "y1": round(rby_px - 30, 1),
            "x2": round(rbx_px + 15, 1), "y2": round(rby_px + 30, 1),
            "conf": round(float(RNG.uniform(0.82, 0.92)), 4),
            "pitch_x": round(ref_px_cm, 2),
            "pitch_y": round(ref_py_cm, 2),
        })

        # Balón
        if ball_found:
            bbx_px, bby_px = _pitch_to_px(bx, by)
            objects_rows.append({
                "frame": frame, "t": round(t, 4),
                "source": "ball",
                "track_id": None,
                "class_id": 32, "class_name": "ball",
                "team": None,
                "x1": round(bbx_px - 8, 1), "y1": round(bby_px - 8, 1),
                "x2": round(bbx_px + 8, 1), "y2": round(bby_px + 8, 1),
                "conf": round(float(RNG.uniform(0.75, 0.95)), 4),
                "pitch_x": round(bx, 2),
                "pitch_y": round(by, 2),
            })

    df_frames = pd.DataFrame(frames_rows)
    df_objects = pd.DataFrame(objects_rows)

    # Guardar
    frames_path = dest / "frames.parquet"
    objects_path = dest / "objects.parquet"
    df_frames.to_parquet(str(frames_path), index=False)
    df_objects.to_parquet(str(objects_path), index=False)

    print(f"[dataset_manager] Generado: {frames_path} ({len(df_frames)} filas)")
    print(f"[dataset_manager] Generado: {objects_path} ({len(df_objects)} filas)")
    print(f"[dataset_manager] Caso testigo track_id=19 en frame 300: "
          f"pitch_x≈{df_objects[(df_objects.source == 'track') & (df_objects.track_id == 19) & (df_objects.frame == 300)]['pitch_x'].values}")

    return df_frames, df_objects


# ---------------------------------------------------------------------------
# 4. Punto de entrada unificado
# ---------------------------------------------------------------------------

def get_parquets(
    raw_dir: str = "data/raw",
    force_generate: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Política de ingesta:
    1. Si force_generate=True → genera sintético y devuelve.
    2. Si existen los parquets reales de visión en outputs/experiment/C_data/ → los sincroniza a raw_dir y los carga.
    3. Si los parquets locales en raw_dir existen → los carga.
    4. Si no existen → intenta descargar de HuggingFace.
    5. Si la descarga falla → genera datos sintéticos de respaldo.
    """
    if force_generate:
        print("[dataset_manager] Forzando generación sintética …")
        return generate_sample_parquets(raw_dir)

    # Priorizar los parquets reales del MVP (clip_13 Mundial 2014) o en su defecto C_data
    root_dir = pathlib.Path(__file__).parent.parent.parent
    candidate_dirs = [
        root_dir / "outputs" / "mvp_pruebas" / "mundial_2014_brasil_alemania" / "clip_13",
        root_dir / "outputs" / "experiment" / "C_data",
    ]
    for cand_dir in candidate_dirs:
        cand_frames = cand_dir / "frames.parquet"
        cand_objects = cand_dir / "objects.parquet"
        if cand_frames.exists() and cand_objects.exists():
            import shutil
            dest = pathlib.Path(raw_dir)
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(cand_frames), str(dest / "frames.parquet"))
            shutil.copy2(str(cand_objects), str(dest / "objects.parquet"))
            print(f"[dataset_manager] Sincronizados parquets reales desde {cand_dir} → {dest}")
            break

    df_frames, df_objects = load_local_parquets(raw_dir)
    if df_frames is not None:
        return df_frames, df_objects

    print("[dataset_manager] Parquets locales no encontrados. Intentando HuggingFace …")
    ok = download_hf_parquets(raw_dir)
    if ok:
        df_frames, df_objects = load_local_parquets(raw_dir)
        if df_frames is not None:
            return df_frames, df_objects

    print("[dataset_manager] Usando generador sintético de respaldo …")
    return generate_sample_parquets(raw_dir)


# ---------------------------------------------------------------------------
# CLI de prueba y gestión de dataset HF
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Gestor de Dataset Omnimorph (HuggingFace Soccer videos & Parquets)"
    )
    parser.add_argument(
        "--list-videos",
        action="store_true",
        help="Listar los videos disponibles en QimingLi/video_human_select_Soccer (por defecto: Mundial 2014 720p)",
    )
    parser.add_argument(
        "--all-matches",
        action="store_true",
        help="Incluir todos los partidos y resoluciones al listar/descargar (en vez de solo Brasil vs Alemania 2014 720p)",
    )
    parser.add_argument(
        "--match-prefix",
        type=str,
        default=DEFAULT_HF_MATCH_PREFIX,
        help=f"Prefijo de partido a usar (default: {DEFAULT_HF_MATCH_PREFIX} = Mundial FIFA Brasil 2014)",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default=DEFAULT_HF_RESOLUTION,
        help=f"Resolución a usar: 720 o 480 (default: {DEFAULT_HF_RESOLUTION})",
    )
    parser.add_argument(
        "--clean-other-matches",
        action="store_true",
        help="Eliminar videos descargados previamente que pertenezcan a otros partidos",
    )
    parser.add_argument(
        "--download-videos",
        action="store_true",
        help="Descargar videos de QimingLi/video_human_select_Soccer (Soccer/) hacia --video-dir",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Número máximo de videos a descargar (por defecto: todos los del partido)",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Nombres específicos de archivos .mp4 a descargar",
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        default=None,
        help="Directorio destino (por defecto: data/videos/mundial_2014_720p_hd o mundial_2014_480p_sd)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directorio de parquets crudos (default: data/raw)",
    )
    parser.add_argument(
        "--use-real",
        action="store_true",
        help="Cargar/sincronizar parquets reales en lugar de forzar sintéticos",
    )

    args = parser.parse_args()

    eff_prefix = None if args.all_matches else args.match_prefix
    eff_res = None if args.all_matches else args.resolution

    if args.list_videos:
        vids = list_hf_soccer_videos(match_prefix=eff_prefix, resolution=eff_res)
        print(f"\nVideos en {HF_DATASET}/{HF_DATA_DIR} ({len(vids)} encontrados):")
        total_mb = sum(v["size_mb"] for v in vids)
        for idx, v in enumerate(vids, 1):
            print(f"  {idx:3d}. {v['filename']:<28} | {v['size_mb']:>6.2f} MB | {v['match']} ({v['competition']})")
        print(f"Total aproximado: {total_mb:.2f} MB\n")
    elif args.download_videos:
        paths = download_hf_soccer_videos(
            dest_dir=args.video_dir,
            max_videos=args.max_videos,
            filenames=args.files,
            match_prefix=eff_prefix,
            resolution=eff_res,
            clean_other_matches=args.clean_other_matches,
        )
        print(f"\nTotal videos listos en '{args.video_dir}': {len(paths)}")
    else:
        df_f, df_o = get_parquets(raw_dir=args.raw_dir, force_generate=not args.use_real)
        print(f"\nframes.parquet  shape: {df_f.shape}")
        print(f"objects.parquet shape: {df_o.shape}")
        print(f"sources únicos: {df_o.source.unique()}")
        print(f"track_ids únicos: {df_o[df_o.source=='track'].track_id.nunique()}")
        print("\nPrimeras filas de frames.parquet:")
        print(df_f[["frame", "t", "n_det", "n_track", "ball_found", "homography_valid"]].head())
