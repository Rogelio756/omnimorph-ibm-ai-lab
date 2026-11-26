"""
scripts/recalibrar_posiciones.py
================================
C1b · Recalibración del radar usando las matrices H por líneas de cancha
(`data/clean/calibracion_lineas.npz`, generadas por `scripts/calibrar_lineas.py`).

1. Lee `data/clean/calibracion_lineas.npz` (`H`, `valida`, `cobertura`). Si falta,
   termina con error claro. Ya no escribe `radar_error.json`.
2. Donde `valida` es falso (1074-1079, toma cerrada), las posiciones son `NaN`,
   `homography_valid` es falso y no se interpola ni se arrastra nada en esos cuadros.
3. Recalcula `pitch_x`, `pitch_y` de todas las filas con recuadro (también balón y árbitro)
   con el punto inferior central `((x1+x2)/2, y2)`.
4. Metros reales: la cancha es de 105 x 68 m (`x_m = pitch_x * 105/12000`, `y_m = pitch_y * 68/7000`).
   Posiciones a más de 3 m fuera de la cancha se ponen en `NaN`.
5. Guarda `data/partidos/costa_rica_skn_eliminatorias_2026/mapa_rastros.json` desde el
   respaldo si existe, y ejecuta las fases 1 a 4 del motor para dejar actualizados
   `data/clean/objects_cleaned.parquet` y `data/clean/frames_clean.parquet`.
"""

from __future__ import annotations

import json
import pathlib
import sys

import cv2
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementacion import partido_config
from implementacion.cloud_tool import omnimorph_engine

PITCH_L_CM = 12_000.0
PITCH_W_CM = 7_000.0
PITCH_L_M = 105.0
PITCH_W_M = 68.0
OUT_MARGIN_M = 3.0  # 3 m reales fuera de la cancha (105 x 68 m)

BACKUP_DIR = ROOT / "backups" / "pre_recalibracion_2026-11-25"
RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
NPZ_PATH = CLEAN_DIR / "calibracion_lineas.npz"
MAPA_RASTROS_CRC_PATH = (
    ROOT / "data" / "partidos" / "costa_rica_skn_eliminatorias_2026" / "mapa_rastros.json"
)


def _guardar_mapa_rastros_desde_respaldo() -> None:
    """
    Guarda data/partidos/costa_rica_skn_eliminatorias_2026/mapa_rastros.json
    desde el objects_cleaned.parquet del respaldo si este existe.
    """
    bak_clean = BACKUP_DIR / "data" / "clean" / "objects_cleaned.parquet"
    if not bak_clean.exists():
        if not MAPA_RASTROS_CRC_PATH.exists():
            raise FileNotFoundError(
                f"No existe el respaldo {bak_clean} ni {MAPA_RASTROS_CRC_PATH}."
            )
        return

    df_bak = pd.read_parquet(str(bak_clean))
    tr = df_bak[df_bak["source"] == "track"].dropna(subset=["track_id", "track_id_stitched"])
    pares = sorted({(int(a), int(b)) for a, b in zip(tr["track_id"], tr["track_id_stitched"])})
    mapa = {str(a): int(b) for a, b in pares}

    MAPA_RASTROS_CRC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MAPA_RASTROS_CRC_PATH, "w", encoding="utf-8") as f:
        json.dump(mapa, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def recalibrar() -> None:
    if not NPZ_PATH.exists():
        raise FileNotFoundError(
            f"Falta {NPZ_PATH}. Corre primero scripts/calibrar_lineas.py."
        )

    _guardar_mapa_rastros_desde_respaldo()

    # Leer desde el respaldo si existe para garantizar idempotencia sobre los datos crudos
    src_frames = BACKUP_DIR / "data" / "raw" / "frames.parquet"
    src_objects = BACKUP_DIR / "data" / "raw" / "objects.parquet"
    if not src_frames.exists():
        src_frames = RAW_DIR / "frames.parquet"
    if not src_objects.exists():
        src_objects = RAW_DIR / "objects.parquet"

    df_frames = pd.read_parquet(str(src_frames)).copy()
    df_objects = pd.read_parquet(str(src_objects)).copy()

    npz = np.load(str(NPZ_PATH))
    H_arr = np.asarray(npz["H"], dtype=np.float64)
    valida_arr = np.asarray(npz["valida"], dtype=bool)

    if len(H_arr) != len(df_frames) or len(valida_arr) != len(df_frames):
        raise ValueError(
            f"Dimensiones de {NPZ_PATH} ({len(H_arr)}) no coinciden con frames.parquet ({len(df_frames)})."
        )

    valid_list: list[bool] = []
    err_list: list[str | None] = []
    h_list: list[list[float] | None] = []

    for idx in range(len(df_frames)):
        es_val = bool(valida_arr[idx]) and bool(np.isfinite(H_arr[idx]).all())
        valid_list.append(es_val)
        if es_val:
            err_list.append(None)
            h_list.append([round(float(v), 6) for v in H_arr[idx].ravel()])
        else:
            err_list.append("toma_cerrada_sin_calibracion")
            h_list.append(None)

    df_frames["homography_valid"] = valid_list
    df_frames["homography_error"] = err_list
    df_frames["H"] = h_list

    # Proyectar todas las filas con recuadro usando el punto inferior central ((x1+x2)/2, y2)
    has_bbox = (
        df_objects["x1"].notna()
        & df_objects["x2"].notna()
        & df_objects["y2"].notna()
    )
    bx = (df_objects["x1"].astype(float) + df_objects["x2"].astype(float)) / 2.0
    by = df_objects["y2"].astype(float)
    frames_arr = df_objects["frame"].astype(int).to_numpy()

    px = np.full(len(df_objects), np.nan, dtype=np.float64)
    py = np.full(len(df_objects), np.nan, dtype=np.float64)

    for f_idx in range(len(df_frames)):
        if not valid_list[f_idx]:
            # Donde valida es falso (1074-1079, toma cerrada), las posiciones son NaN
            continue
        m = (frames_arr == f_idx) & has_bbox.to_numpy()
        if not m.any():
            continue
        pts = np.column_stack([bx.to_numpy()[m], by.to_numpy()[m]]).reshape(-1, 1, 2).astype(np.float32)
        proj = cv2.perspectiveTransform(pts, H_arr[f_idx]).reshape(-1, 2)
        px[m] = proj[:, 0]
        py[m] = proj[:, 1]

    # Metros reales (105 x 68 m): posiciones a más de 3 m fuera de la cancha -> NaN
    x_m = px * (PITCH_L_M / PITCH_L_CM)
    y_m = py * (PITCH_W_M / PITCH_W_CM)
    fuera = (
        (x_m < -OUT_MARGIN_M)
        | (x_m > PITCH_L_M + OUT_MARGIN_M)
        | (y_m < -OUT_MARGIN_M)
        | (y_m > PITCH_W_M + OUT_MARGIN_M)
    )
    px[fuera] = np.nan
    py[fuera] = np.nan

    df_objects["pitch_x"] = np.where(np.isnan(px), np.nan, np.round(px, 2))
    df_objects["pitch_y"] = np.where(np.isnan(py), np.nan, np.round(py, 2))

    # Guardar en data/raw/
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df_frames.to_parquet(str(RAW_DIR / "frames.parquet"), index=False)
    df_objects.to_parquet(str(RAW_DIR / "objects.parquet"), index=False)

    # Sincronizar también en percepcion_dir del partido activo si coincide
    partido = partido_config.activo()
    if partido.percepcion_dir.exists() and len(df_frames) == partido.n_frames:
        df_frames.to_parquet(str(partido.percepcion_dir / "frames.parquet"), index=False)
        df_objects.to_parquet(str(partido.percepcion_dir / "objects.parquet"), index=False)

    # Ejecutar fases 1 a 4 del motor para dejar objects_cleaned.parquet y frames_clean.parquet al día
    df_track, df_ball, team_map = omnimorph_engine.phase1_separate_and_team(df_objects)

    # Asegurar que donde valida es falso (1074-1079) no quede ninguna posición interpolada ni arrastrada
    cuadros_invalidos = {idx for idx, v in enumerate(valid_list) if not v}
    if cuadros_invalidos:
        if len(df_track) > 0:
            m_inv_tr = df_track["frame"].isin(cuadros_invalidos)
            df_track.loc[m_inv_tr, ["pitch_x", "pitch_y"]] = np.nan
        if len(df_ball) > 0:
            m_inv_b = df_ball["frame"].isin(cuadros_invalidos)
            df_ball.loc[m_inv_b, ["pitch_x", "pitch_y"]] = np.nan

    df_frames_h = omnimorph_engine.phase4_homography_ema(df_frames)
    df_track_stitched = omnimorph_engine.phase3_track_stitching(df_track, team_map)
    df_track_clean = omnimorph_engine.phase2_kinematics(df_track_stitched)

    if cuadros_invalidos and len(df_track_clean) > 0:
        m_inv_clean = df_track_clean["frame"].isin(cuadros_invalidos)
        df_track_clean.loc[
            m_inv_clean,
            ["pitch_x", "pitch_y", "pitch_x_smooth", "pitch_y_smooth", "vx_mps", "vy_mps", "v_mps", "v_clipped"],
        ] = np.nan

    df_ball_out = df_ball.copy()
    if len(df_ball_out) > 0:
        df_ball_out["track_id_stitched"] = pd.Series([None] * len(df_ball_out), index=df_ball_out.index, dtype="Int64")
        df_ball_out["pitch_x_smooth"] = df_ball_out["pitch_x"]
        df_ball_out["pitch_y_smooth"] = df_ball_out["pitch_y"]
        df_combined_out = pd.concat([df_track_clean, df_ball_out], ignore_index=True)
    else:
        df_combined_out = df_track_clean

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    df_combined_out.to_parquet(str(CLEAN_DIR / "objects_cleaned.parquet"), index=False)
    df_frames_h.to_parquet(str(CLEAN_DIR / "frames_clean.parquet"), index=False)

    n_valid = sum(valid_list)
    print(f"[OK] frames recalibrados desde calibracion_lineas.npz: {n_valid}/{len(df_frames)} válidos ({len(df_frames) - n_valid} toma cerrada -> NaN)")
    print(f"[OK] objetos proyectados: {len(df_objects)} filas ({int(fuera.sum())} a > 3 m fuera de cancha -> NaN)")
    print(f"[OK] mapa_rastros.json verificado en {MAPA_RASTROS_CRC_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    recalibrar()
