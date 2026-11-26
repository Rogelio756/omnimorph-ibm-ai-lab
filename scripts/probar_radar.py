"""
scripts/probar_radar.py
=======================
Pruebas automáticas de C1b (Calibración por líneas):
1a. Los 23 puntos de `scripts/radar_puntos_a_mano.json` con la H de `data/raw/frames.parquet`:
    mediana <= 1 m y máximo <= 2 m (referencia: 0.2 y 1.4).
1b. `data/clean/radar_error.json`: mediana <= 3 m y método «área grande sin usarla para calibrar».
1c. Ninguna posición de rastro a más de 3 m fuera de la cancha (105 x 68 m), ni en `pitch_x`/`pitch_y`
    ni en `pitch_x_smooth`/`pitch_y_smooth`, y en los cuadros sin calibración (`homography_valid == False`)
    todas las posiciones son `NaN`.
2.  En los cuadros 30, 72, 719, 929 y 1064, la mediana de `pitch_x` y de `pitch_x_smooth`
    de todos los jugadores es menor que 6000.
3.  En el cuadro 300, la mediana de `pitch_x` y de `pitch_x_smooth` de CRC es mayor que 6000.
4.  Los pares `track_id -> track_id_stitched` son idénticos a los del respaldo y a
    `data/partidos/costa_rica_skn_eliminatorias_2026/mapa_rastros.json`.

Sale con código 0 si todas pasan, o 1 si alguna falla.
"""

from __future__ import annotations

import json
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RAW_DIR = ROOT / "data" / "raw"
CLEAN_DIR = ROOT / "data" / "clean"
PUNTOS_MANO_PATH = ROOT / "scripts" / "radar_puntos_a_mano.json"
RADAR_ERROR_PATH = CLEAN_DIR / "radar_error.json"
MAPA_RASTROS_PATH = (
    ROOT / "data" / "partidos" / "costa_rica_skn_eliminatorias_2026" / "mapa_rastros.json"
)
BACKUP_CLEAN = (
    ROOT / "backups" / "pre_recalibracion_2026-11-25" / "data" / "clean" / "objects_cleaned.parquet"
)

PITCH_L_CM = 12_000.0
PITCH_W_CM = 7_000.0
PITCH_L_M = 105.0
PITCH_W_M = 68.0
OUT_MARGIN_M = 3.0


def _medir_puntos_a_mano(df_frames: pd.DataFrame) -> tuple[float, float, int]:
    with open(PUNTOS_MANO_PATH, "r", encoding="utf-8") as f:
        datos = json.load(f)
    puntos = datos["puntos"]

    frames_by_id = df_frames.set_index("frame") if "frame" in df_frames.columns else df_frames
    errores_m: list[float] = []
    for p in puntos:
        cuadro = int(p["cuadro"])
        px, py = float(p["px"][0]), float(p["px"][1])
        mx, my = float(p["cancha_m"][0]), float(p["cancha_m"][1])

        fila = frames_by_id.loc[cuadro]
        raw_h = fila["H"]
        if raw_h is None or not bool(fila["homography_valid"]):
            errores_m.append(999.0)
            continue
        H = np.asarray(raw_h, dtype=np.float64).reshape(3, 3)
        pt = np.array([[[px, py]]], dtype=np.float32)
        proj = cv2.perspectiveTransform(pt, H)[0, 0]
        x_m = float(proj[0]) * (PITCH_L_M / PITCH_L_CM)
        y_m = float(proj[1]) * (PITCH_W_M / PITCH_W_CM)
        errores_m.append(float(np.hypot(x_m - mx, y_m - my)))

    errs = np.asarray(errores_m, dtype=np.float64)
    return float(np.median(errs)), float(np.max(errs)), len(errs)


def _contar_fuera_3m(df: pd.DataFrame, col_x: str, col_y: str) -> int:
    sub = df.dropna(subset=[col_x, col_y])
    if len(sub) == 0:
        return 0
    x_m = sub[col_x].to_numpy(dtype=float) * (PITCH_L_M / PITCH_L_CM)
    y_m = sub[col_y].to_numpy(dtype=float) * (PITCH_W_M / PITCH_W_CM)
    fuera = (
        (x_m < -OUT_MARGIN_M)
        | (x_m > PITCH_L_M + OUT_MARGIN_M)
        | (y_m < -OUT_MARGIN_M)
        | (y_m > PITCH_W_M + OUT_MARGIN_M)
    )
    return int(fuera.sum())


def main() -> int:
    resultados: list[tuple[str, bool, str]] = []

    def registrar(nombre: str, ok: bool, detalle: str) -> None:
        resultados.append((nombre, ok, detalle))
        marca = "PASS" if ok else "FAIL"
        print(f"  [{marca}] {nombre} -> {detalle}")

    print("=" * 76)
    print("  PRUEBAS C1b · RADAR POR LÍNEAS (scripts/probar_radar.py)")
    print("=" * 76)

    df_frames = pd.read_parquet(str(RAW_DIR / "frames.parquet"))
    df_objects = pd.read_parquet(str(RAW_DIR / "objects.parquet"))
    df_clean = pd.read_parquet(str(CLEAN_DIR / "objects_cleaned.parquet"))

    # 1a. 23 puntos de scripts/radar_puntos_a_mano.json con la H de data/raw/frames.parquet
    med_mano, max_mano, n_mano = _medir_puntos_a_mano(df_frames)
    ok_1a = (n_mano == 23) and (med_mano <= 1.0) and (max_mano <= 2.0)
    registrar(
        "1a. 23 puntos a mano con H de frames.parquet (mediana <= 1.0 m, max <= 2.0 m)",
        ok_1a,
        f"n={n_mano}, mediana={med_mano:.2f} m, max={max_mano:.2f} m",
    )

    # 1b. radar_error.json: mediana <= 3 m y método «área grande sin usarla para calibrar»
    with open(RADAR_ERROR_PATH, "r", encoding="utf-8") as f:
        err_json = json.load(f)
    med_err = float(err_json.get("mediana_m", 999.0))
    metodo_err = err_json.get("metodo", "")
    ok_1b = (med_err <= 3.0) and (metodo_err == "área grande sin usarla para calibrar")
    registrar(
        "1b. radar_error.json (mediana <= 3.0 m y método área grande)",
        ok_1b,
        f"mediana_m={med_err} m, p90_m={err_json.get('p90_m')} m, cuadros={err_json.get('cuadros')}, metodo='{metodo_err}'",
    )

    # 1c. Ninguna posición de rastro a más de 3 m fuera (y NaN donde homography_valid es falso)
    df_tr_raw = df_objects[df_objects["source"] == "track"]
    df_tr_clean = df_clean[df_clean["source"] == "track"]
    fuera_raw = _contar_fuera_3m(df_tr_raw, "pitch_x", "pitch_y")
    fuera_clean_raw = _contar_fuera_3m(df_tr_clean, "pitch_x", "pitch_y")
    fuera_clean_smooth = _contar_fuera_3m(df_tr_clean, "pitch_x_smooth", "pitch_y_smooth")

    cuadros_inv = set(df_frames.loc[~df_frames["homography_valid"].astype(bool), "frame"].astype(int))
    n_no_nan_inv = int(
        df_objects.loc[df_objects["frame"].isin(cuadros_inv), ["pitch_x", "pitch_y"]].notna().any(axis=1).sum()
        + df_clean.loc[
            df_clean["frame"].isin(cuadros_inv),
            ["pitch_x", "pitch_y", "pitch_x_smooth", "pitch_y_smooth"],
        ].notna().any(axis=1).sum()
    )
    ok_1c = (
        fuera_raw == 0
        and fuera_clean_raw == 0
        and fuera_clean_smooth == 0
        and len(cuadros_inv) == 6
        and n_no_nan_inv == 0
    )
    registrar(
        "1c. Ninguna posición de rastro a > 3 m fuera de la cancha (105x68 m)",
        ok_1c,
        f"fuera_raw={fuera_raw}, fuera_clean={fuera_clean_raw}, fuera_smooth={fuera_clean_smooth}, "
        f"cuadros_invalidos={sorted(cuadros_inv)}, no_nan_en_invalidos={n_no_nan_inv}",
    )

    # 2. Cuadros 30, 72, 719, 929 y 1064: mediana de pitch_x y pitch_x_smooth de todos los jugadores < 6000
    for cuadro in (30, 72, 719, 929, 1064):
        sub_raw = df_tr_raw[(df_tr_raw["frame"] == cuadro) & (df_tr_raw["class_name"].isin(["player", "goalkeeper"]))]
        sub_cln = df_tr_clean[(df_tr_clean["frame"] == cuadro) & (df_tr_clean["class_name"].isin(["player", "goalkeeper"]))]
        med_px = float(sub_raw["pitch_x"].median())
        med_smooth = float(sub_cln["pitch_x_smooth"].median())
        ok_c = (med_px < 6000.0) and (med_smooth < 6000.0)
        registrar(
            f"2. Cuadro {cuadro}: mediana pitch_x y pitch_x_smooth jugadores < 6000",
            ok_c,
            f"pitch_x={med_px:.1f} cm ({med_px * 105 / 12000:.1f} m), "
            f"pitch_x_smooth={med_smooth:.1f} cm ({med_smooth * 105 / 12000:.1f} m)",
        )

    # 3. Cuadro 300: mediana de pitch_x y pitch_x_smooth de CRC (team == 1) > 6000
    sub300_raw = df_tr_raw[(df_tr_raw["frame"] == 300) & (df_tr_raw["team"] == 1)]
    sub300_cln = df_tr_clean[(df_tr_clean["frame"] == 300) & (df_tr_clean["team"] == 1)]
    med300_px = float(sub300_raw["pitch_x"].median())
    med300_smooth = float(sub300_cln["pitch_x_smooth"].median())
    ok_300 = (med300_px > 6000.0) and (med300_smooth > 6000.0)
    registrar(
        "3. Cuadro 300: mediana pitch_x y pitch_x_smooth de CRC > 6000",
        ok_300,
        f"pitch_x={med300_px:.1f} cm ({med300_px * 105 / 12000:.1f} m), "
        f"pitch_x_smooth={med300_smooth:.1f} cm ({med300_smooth * 105 / 12000:.1f} m)",
    )

    # 4. Pares track_id -> track_id_stitched idénticos al respaldo y a mapa_rastros.json
    with open(MAPA_RASTROS_PATH, "r", encoding="utf-8") as f:
        mapa_json = json.load(f)
    pares_mapa = {(int(k), int(v)) for k, v in mapa_json.items()}

    tr_act = df_tr_clean.dropna(subset=["track_id", "track_id_stitched"])
    pares_act = set(zip(tr_act["track_id"].astype(int), tr_act["track_id_stitched"].astype(int)))

    if BACKUP_CLEAN.exists():
        df_bak = pd.read_parquet(str(BACKUP_CLEAN))
        tr_bak = df_bak[df_bak["source"] == "track"].dropna(subset=["track_id", "track_id_stitched"])
        pares_bak = set(zip(tr_bak["track_id"].astype(int), tr_bak["track_id_stitched"].astype(int)))
        iguales = (pares_act == pares_bak) and (pares_act == pares_mapa)
    else:
        iguales = pares_act == pares_mapa

    n_orig = len({k for k, _ in pares_act})
    n_stitch = len({v for _, v in pares_act})
    registrar(
        "4. Pares track_id -> track_id_stitched idénticos al respaldo y mapa_rastros.json",
        iguales,
        f"{n_orig} -> {n_stitch} rastros ({len(pares_act)} pares, coincide={iguales})",
    )

    print("-" * 76)
    n_ok = sum(1 for _, ok, _ in resultados if ok)
    n_total = len(resultados)
    print(f"  Resultado: {n_ok}/{n_total} pruebas superadas")
    print("=" * 76)
    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
