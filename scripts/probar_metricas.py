"""
scripts/probar_metricas.py
==========================
Pruebas automáticas de C2 (Métricas de fase 5 y M2.1):
a. Espejo: intercambiar equipos, sentido de ataque y posiciones da el resultado espejo.
b. Umbral: diferencia de 20 exactos = "repartido"; 20.1 = gana.
c. Un rastro que cambia de equipo entre tramos recibe el equipo correcto en cada uno.
d. Un árbitro por moda no cuenta.
e. Con menos de 4 jugadores, largo y ancho en None; ningún NaN en el JSON (allow_nan=False).
f. M2.1 da FAIL con mediana 3.1 y PASS con 2.4.
g. Hueco de 16 cuadros queda entero en NaN y uno de 15 se rellena.
h. Con los datos reales, territorio W0-W7 = CRC, repartido, SKN, repartido, repartido, CRC, CRC, CRC.

Sale con código 0 si todas pasan, o 1 si alguna falla.
"""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
from dataclasses import dataclass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementacion.cloud_tool import omnimorph_engine as eng

CLEAN_DIR = ROOT / "data" / "clean"


@dataclass
class _EquipoDummy:
    team_id: int
    codigo: str
    ataca_hacia: str


def main() -> int:
    resultados: list[tuple[str, bool, str]] = []

    def registrar(nombre: str, ok: bool, detalle: str) -> None:
        resultados.append((nombre, ok, detalle))
        marca = "PASS" if ok else "FAIL"
        print(f"  [{marca}] {nombre} -> {detalle}")

    print("=" * 78)
    print("  PRUEBAS C2 · MÉTRICAS TÁCTICAS Y M2.1 (scripts/probar_metricas.py)")
    print("=" * 78)

    # ── a. Espejo: intercambiar equipos, sentido de ataque y posiciones ──────
    df_real = pd.read_parquet(str(CLEAN_DIR / "objects_cleaned.parquet"))
    df_tr_real = df_real[df_real["source"] == "track"].copy()

    eq_normal = (_EquipoDummy(0, "SKN", "+x"), _EquipoDummy(1, "CRC", "-x"))
    wins_orig = eng.phase5_tactical_windows(
        df_tr_real,
        equipos_override=eq_normal,
        total_frames_override=1080,
    )

    df_espejo = df_tr_real.copy()
    df_espejo["team"] = df_espejo["team"].map(lambda t: 1 - int(t) if pd.notna(t) and int(t) in (0, 1) else t)
    df_espejo["pitch_x_smooth"] = eng.PITCH_L_CM - df_espejo["pitch_x_smooth"]
    df_espejo["pitch_y_smooth"] = eng.PITCH_W_CM - df_espejo["pitch_y_smooth"]

    # En el espejo: team 0 pasa a ser CRC atacando hacia +x, y team 1 pasa a ser SKN atacando hacia -x
    eq_espejo = (_EquipoDummy(0, "CRC", "+x"), _EquipoDummy(1, "SKN", "-x"))
    wins_esp = eng.phase5_tactical_windows(
        df_espejo,
        equipos_override=eq_espejo,
        total_frames_override=1080,
    )

    espejo_ok = True
    for w_o, w_e in zip(wins_orig, wins_esp):
        if w_o["territorio"] != w_e["territorio"] or w_o["dominant_team"] != w_e["dominant_team"]:
            espejo_ok = False
            break
        for cod in ("SKN", "CRC"):
            if w_o["equipos"][cod] != w_e["equipos"][cod]:
                espejo_ok = False
                break
    registrar(
        "a. Espejo: intercambiar equipos, sentido de ataque y posiciones",
        espejo_ok,
        f"8/8 ventanas idénticas en territorio y métricas de SKN y CRC (coincide={espejo_ok})",
    )

    # ── b. Umbral: diferencia de 20 exactos = "repartido"; 20.1 = gana ───────
    t_20_a = eng.decidir_territorio("SKN", 60.0, "CRC", 40.0)
    t_20_b = eng.decidir_territorio("SKN", 40.0, "CRC", 60.0)
    t_201_a = eng.decidir_territorio("SKN", 60.1, "CRC", 40.0)
    t_201_b = eng.decidir_territorio("SKN", 40.0, "CRC", 60.1)
    t_none = eng.decidir_territorio("SKN", None, "CRC", 80.0)
    ok_b = (
        t_20_a == "repartido"
        and t_20_b == "repartido"
        and t_201_a == "SKN"
        and t_201_b == "CRC"
        and t_none == "repartido"
    )
    registrar(
        "b. Umbral territorio (diff=20 -> repartido; diff=20.1 -> gana; None -> repartido)",
        ok_b,
        f"diff=+20:{t_20_a}, diff=-20:{t_20_b}, diff=+20.1:{t_201_a}, diff=-20.1:{t_201_b}, None:{t_none}",
    )

    # ── c. Un rastro que cambia de equipo entre tramos recibe el equipo correcto ─
    filas_c = []
    # Tramo W0 (frames 0..9): track_id=29 tiene mayoría team=0 (SKN) en x=9000 cm
    for f in range(10):
        filas_c.append({
            "frame": f,
            "track_id": 29,
            "track_id_stitched": 29,
            "class_id": 2,
            "class_name": "player",
            "team": 0 if f < 8 else 1,
            "pitch_x_smooth": 9000.0,
            "pitch_y_smooth": 3500.0,
        })
    # Tramo W1 (frames 10..19): track_id=29 tiene mayoría team=1 (CRC) en x=3000 cm
    for f in range(10, 20):
        filas_c.append({
            "frame": f,
            "track_id": 29,
            "track_id_stitched": 29,
            "class_id": 2,
            "class_name": "player",
            "team": 1 if f < 18 else 0,
            "pitch_x_smooth": 3000.0,
            "pitch_y_smooth": 3500.0,
        })
    df_c = pd.DataFrame(filas_c)
    wins_c = eng.phase5_tactical_windows(
        df_c,
        equipos_override=eq_normal,
        total_frames_override=80,  # 8 ventanas de 10 frames
    )
    w0_c, w1_c = wins_c[0], wins_c[1]
    ok_c = (
        w0_c["n_arg"] == 10
        and w0_c["n_fra"] == 0
        and w0_c["equipos"]["SKN"]["posicion_m"] is not None
        and w0_c["equipos"]["CRC"]["posicion_m"] is None
        and w1_c["n_arg"] == 0
        and w1_c["n_fra"] == 10
        and w1_c["equipos"]["SKN"]["posicion_m"] is None
        and w1_c["equipos"]["CRC"]["posicion_m"] is not None
    )
    registrar(
        "c. Rastro que cambia de equipo entre tramos recibe el equipo por moda de cada tramo",
        ok_c,
        f"W0(n_SKN={w0_c['n_arg']}, n_CRC={w0_c['n_fra']}), W1(n_SKN={w1_c['n_arg']}, n_CRC={w1_c['n_fra']})",
    )

    # ── d. Un árbitro por moda no cuenta ─────────────────────────────────────
    filas_d = []
    for f in range(10):
        # Jugador real de SKN (track_id=1)
        filas_d.append({
            "frame": f,
            "track_id": 1,
            "track_id_stitched": 1,
            "class_id": 2,
            "class_name": "player",
            "team": 0,
            "pitch_x_smooth": 6000.0,
            "pitch_y_smooth": 3500.0,
        })
        # Árbitro por moda (8 frames referee, 2 frames player con team=0)
        filas_d.append({
            "frame": f,
            "track_id": 99,
            "track_id_stitched": 99,
            "class_id": 3 if f < 8 else 2,
            "class_name": "referee" if f < 8 else "player",
            "team": 0,
            "pitch_x_smooth": 11000.0,
            "pitch_y_smooth": 3500.0,
        })
    df_d = pd.DataFrame(filas_d)
    wins_d = eng.phase5_tactical_windows(
        df_d,
        equipos_override=eq_normal,
        total_frames_override=80,
    )
    w0_d = wins_d[0]
    ok_d = (w0_d["n_arg"] == 10) and (w0_d["equipos"]["SKN"]["posicion_m"] == 52.5)
    registrar(
        "d. Árbitro por moda dentro del tramo no cuenta en las métricas del equipo",
        ok_d,
        f"n_SKN={w0_d['n_arg']} (esperado 10, sin las 10 filas del árbitro), pos_SKN={w0_d['equipos']['SKN']['posicion_m']} m",
    )

    # ── e. Con menos de 4 jugadores, largo y ancho en None; allow_nan=False ─
    # En wins_d solo hay 1 jugador de SKN por cuadro y 0 de CRC
    eq_skn_d = w0_d["equipos"]["SKN"]
    eq_crc_d = w0_d["equipos"]["CRC"]
    json_str = json.dumps(wins_d, ensure_ascii=False, allow_nan=False)
    ok_e = (
        eq_skn_d["posicion_m"] == 52.5
        and eq_skn_d["largo_m"] is None
        and eq_skn_d["ancho_m"] is None
        and eq_crc_d["posicion_m"] is None
        and eq_crc_d["pct_campo_rival"] is None
        and eq_crc_d["largo_m"] is None
        and eq_crc_d["ancho_m"] is None
        and w0_d["centroid_fra_x_cm"] is None
        and "NaN" not in json_str
    )
    registrar(
        "e. < 4 jugadores -> largo_m y ancho_m en None; sin datos -> None; JSON allow_nan=False",
        ok_e,
        f"SKN(largo={eq_skn_d['largo_m']}, ancho={eq_skn_d['ancho_m']}), CRC={eq_crc_d}, centroid_CRC={w0_d['centroid_fra_x_cm']}",
    )

    # ── f. M2.1 da FAIL con mediana 3.1 y PASS con 2.4 ──────────────────────
    df_frm_clean = pd.read_parquet(str(CLEAN_DIR / "frames_clean.parquet"))
    df_obj_raw = pd.read_parquet(str(ROOT / "data" / "raw" / "objects.parquet"))
    df_tr_raw, df_ball_raw, tmap_raw = eng.phase1_separate_and_team(df_obj_raw)

    with tempfile.TemporaryDirectory() as tmpdir:
        p_fail = pathlib.Path(tmpdir) / "err_fail.json"
        p_pass = pathlib.Path(tmpdir) / "err_pass.json"
        p_miss = pathlib.Path(tmpdir) / "no_existe.json"
        p_fail.write_text(json.dumps({"mediana_m": 3.1, "p90_m": 4.0, "metodo": "área grande sin usarla para calibrar"}), encoding="utf-8")
        p_pass.write_text(json.dumps({"mediana_m": 2.4, "p90_m": 3.2, "metodo": "área grande sin usarla para calibrar"}), encoding="utf-8")

        rep_fail = eng.run_stage_monitors(
            df_frames=df_frm_clean,
            df_objects_orig=df_obj_raw,
            df_track=df_tr_raw,
            df_ball=df_ball_raw,
            df_track_clean=df_tr_real,
            tactical_windows=wins_orig,
            team_map=tmap_raw,
            radar_error_path=p_fail,
            output_dir=tmpdir,
        )
        rep_miss = eng.run_stage_monitors(
            df_frames=df_frm_clean,
            df_objects_orig=df_obj_raw,
            df_track=df_tr_raw,
            df_ball=df_ball_raw,
            df_track_clean=df_tr_real,
            tactical_windows=wins_orig,
            team_map=tmap_raw,
            radar_error_path=p_miss,
            output_dir=tmpdir,
        )
        rep_pass = eng.run_stage_monitors(
            df_frames=df_frm_clean,
            df_objects_orig=df_obj_raw,
            df_track=df_tr_raw,
            df_ball=df_ball_raw,
            df_track_clean=df_tr_real,
            tactical_windows=wins_orig,
            team_map=tmap_raw,
            radar_error_path=p_pass,
            output_dir=tmpdir,
        )

    m21_fail = rep_fail["checks"]["M2.1"]["pass"]
    m21_miss = rep_miss["checks"]["M2.1"]["pass"]
    m21_pass = rep_pass["checks"]["M2.1"]["pass"]
    ok_f = (not m21_fail) and (not m21_miss) and m21_pass
    registrar(
        "f. M2.1 da FAIL con mediana 3.1 (o si falta archivo) y PASS con 2.4",
        ok_f,
        f"mediana=3.1 -> pass={m21_fail}, archivo_faltante -> pass={m21_miss}, mediana=2.4 -> pass={m21_pass}",
    )

    # ── g. Hueco de 16 cuadros queda entero en NaN y uno de 15 se rellena ────
    frames_15 = pd.Series(list(range(17)))
    vals_15 = pd.Series([100.0] + [np.nan] * 15 + [260.0])
    out_15 = eng._interpolar_serie_huecos(frames_15, vals_15, max_hueco=15)

    frames_16 = pd.Series(list(range(18)))
    vals_16 = pd.Series([100.0] + [np.nan] * 16 + [270.0])
    out_16 = eng._interpolar_serie_huecos(frames_16, vals_16, max_hueco=15)

    ok_g = (int(out_15.isna().sum()) == 0) and (int(out_16.iloc[1:-1].isna().sum()) == 16)
    registrar(
        "g. Hueco de 16 cuadros queda entero en NaN y hueco de 15 se rellena",
        ok_g,
        f"hueco_15_nans={int(out_15.isna().sum())}/15, hueco_16_nans={int(out_16.iloc[1:-1].isna().sum())}/16",
    )

    # ── h. Datos reales: territorio W0-W7 = CRC, repartido, SKN, repartido, repartido, CRC, CRC, CRC
    esperado_h = ["CRC", "repartido", "SKN", "repartido", "repartido", "CRC", "CRC", "CRC"]
    observado_h = [w["territorio"] for w in wins_orig]
    ok_h = observado_h == esperado_h
    registrar(
        "h. Territorio W0-W7 en datos reales",
        ok_h,
        f"observado={observado_h}",
    )

    print("-" * 78)
    n_ok = sum(1 for _, ok, _ in resultados if ok)
    n_total = len(resultados)
    print(f"  Resultado: {n_ok}/{n_total} pruebas superadas")
    print("=" * 78)
    return 0 if n_ok == n_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
