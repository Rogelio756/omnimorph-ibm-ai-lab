r"""
scripts/export_dashboard_data.py
================================
Exporta los artefactos limpios del pipeline (data/clean/, data/audio/, videos H.264)
al frontend estático `dashboard/`, dejándolo AUTOCONTENIDO para:
  - servirlo localmente (python -m http.server)
  - desplegarlo en IBM Cloud Code Engine (contenedor estático)
  - desplegarlo después en Vercel (portafolio)

Salidas:
  dashboard/data/mateo_data.json   ← JSON compacto que consume pages/mateo.html
  dashboard/media/*.mp4|.wav|.vtt  ← videos H.264, audio maestro TTS y subtítulos

Uso:
    .\.venv\Scripts\python.exe scripts/export_dashboard_data.py
    .\.venv\Scripts\python.exe scripts/export_dashboard_data.py --no-media   (solo JSON)
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
AUDIO = ROOT / "data" / "audio"
CLIP_DIR = ROOT / "outputs" / "mvp_pruebas" / "mundial_2014_brasil_alemania" / "clip_13"
ORIG_VIDEO = ROOT / "data" / "videos" / "mundial_2014_720p_hd" / "L6sbfskaTDQ-720-13.mp4"

DASH = ROOT / "dashboard"
OUT_DATA = DASH / "data"
OUT_MEDIA = DASH / "media"

PITCH_W, PITCH_H = 12000.0, 7000.0   # cm
V_MAX = 9.5                           # m/s (M2.3)
SPRINT_V = 7.0                        # m/s umbral de sprint
SPRINT_MIN_FRAMES = 10                # ≥ 0.33 s a 30 fps


def _load_json(p: pathlib.Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _team_label(v) -> str:
    return {"ARG": "BRA", "FRA": "GER"}.get(v, v)


def build_frames(df_tr: pd.DataFrame, df_ball: pd.DataFrame, n_frames: int) -> list:
    """Por frame: [[track_id, team(0/1/2=ref), x_dm, y_dm], ...] + balón. Coordenadas en decímetros (int)."""
    frames: list = [{"p": [], "b": None} for _ in range(n_frames)]

    for f_idx, grp in df_tr.groupby("frame"):
        if f_idx >= n_frames:
            continue
        rows = []
        for r in grp.itertuples(index=False):
            x, y = r.pitch_x_smooth, r.pitch_y_smooth
            if not (0 <= x <= PITCH_W and 0 <= y <= PITCH_H):
                continue
            team = 2 if r.class_id == 3 else (int(r.team_mode) if r.team_mode in (0, 1) else 2)
            rows.append([int(r.track_id_stitched), team, int(round(x / 10)), int(round(y / 10))])
        frames[int(f_idx)]["p"] = rows

    if len(df_ball) > 0:
        best = (df_ball.sort_values(["frame", "conf"], ascending=[True, False])
                .drop_duplicates("frame").set_index("frame"))
        idx = pd.Index(range(n_frames), name="frame")
        b = best[["pitch_x_smooth", "pitch_y_smooth"]].reindex(idx).interpolate(limit=10)
        for f_idx, row in b.dropna().iterrows():
            x, y = row["pitch_x_smooth"], row["pitch_y_smooth"]
            if 0 <= x <= PITCH_W and 0 <= y <= PITCH_H:
                frames[int(f_idx)]["b"] = [int(round(x / 10)), int(round(y / 10))]
    return frames


def build_players(df_tr: pd.DataFrame, fps: float) -> list:
    """Estadísticas por jugador cosido (M2.2): distancia, v. máx, sprints y mapa de calor 12×7."""
    players = []
    for tid, g in df_tr.groupby("track_id_stitched"):
        g = g.sort_values("frame")
        inb = g[(g.pitch_x_smooth.between(0, PITCH_W)) & (g.pitch_y_smooth.between(0, PITCH_H))]
        if len(inb) < 15:
            continue
        team = int(g["team_mode"].iloc[0]) if g["team_mode"].iloc[0] in (0, 1) else 2
        if (g["class_id"] == 3).mean() > 0.5:
            team = 2

        x = inb.pitch_x_smooth.to_numpy() / 100.0   # m
        y = inb.pitch_y_smooth.to_numpy() / 100.0
        fr = inb.frame.to_numpy()
        dt = np.diff(fr) / fps
        step = np.hypot(np.diff(x), np.diff(y))
        contiguous = (np.diff(fr) <= 3) & (dt > 0)
        v = np.zeros_like(step)
        v[contiguous] = step[contiguous] / dt[contiguous]
        v = np.clip(v, 0, V_MAX)
        dist = float(np.sum(v[contiguous] * dt[contiguous]))
        vmax = float(v.max()) if len(v) else 0.0

        sprints, run = 0, 0
        for is_fast in (v >= SPRINT_V):
            run = run + 1 if is_fast else 0
            if run == SPRINT_MIN_FRAMES:
                sprints += 1

        heat, _, _ = np.histogram2d(
            inb.pitch_x_smooth, inb.pitch_y_smooth,
            bins=[12, 7], range=[[0, PITCH_W], [0, PITCH_H]],
        )
        heat = (heat / heat.max()).round(2).tolist() if heat.max() > 0 else heat.tolist()

        players.append({
            "id": int(tid),
            "team": team,
            "frames": int(len(inb)),
            "dist_m": round(dist, 1),
            "vmax_mps": round(vmax, 2),
            "sprints": int(sprints),
            "heat": heat,   # [12][7] normalizado 0..1
        })
    return players


PARTIDO_SRC = ROOT / "data" / "partidos" / "brasil_alemania_2014"
OUT_PARTIDO = OUT_DATA / "partido"


def export_partido() -> None:
    """
    Copia los datos de Brasil 1-7 Alemania (data/partidos/) al frontend.
    Genera dashboard/data/partido/partido.json y copia los SVG y PROCEDENCIA.md.
    """
    if not PARTIDO_SRC.exists():
        print(f"[!!] Falta {PARTIDO_SRC}")
        return
    contexto = _load_json(PARTIDO_SRC / "partido" / "contexto_partido.json")
    data = {
        "partido": contexto["partido_info"],
        "equipos": contexto["equipos"],
        "estadisticas": _load_json(PARTIDO_SRC / "partido" / "estadisticas_partido.json"),
        "goles": _load_json(PARTIDO_SRC / "partido" / "cronologia_goles.json"),
        "gol_muller": _load_json(PARTIDO_SRC / "gol_muller" / "gol_muller_min11.json"),
    }
    OUT_PARTIDO.mkdir(parents=True, exist_ok=True)
    out = OUT_PARTIDO / "partido.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    for origen in (
        PARTIDO_SRC / "assets" / "mapa_8_goles.svg",
        PARTIDO_SRC / "assets" / "radar_gol_muller.svg",
        PARTIDO_SRC / "PROCEDENCIA.md",
    ):
        shutil.copy2(origen, OUT_PARTIDO / origen.name)
    print(f"[OK] {out}  ({out.stat().st_size / 1024:.0f} KB) + 2 SVG + PROCEDENCIA.md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-media", action="store_true", help="No copiar videos/audio")
    ap.add_argument("--solo-partido", action="store_true",
                    help="Exportar solo los datos del partido (no recalcula frames ni copia media)")
    args = ap.parse_args()

    OUT_DATA.mkdir(parents=True, exist_ok=True)
    export_partido()
    if args.solo_partido:
        return

    df = pd.read_parquet(CLEAN / "objects_cleaned.parquet")
    df_frm = pd.read_parquet(CLEAN / "frames_clean.parquet")
    n_frames = int(len(df_frm))
    fps = 30.0 if n_frames > 1000 else 25.0

    df_tr = df[df.source == "track"].copy()
    df_tr = df_tr[df_tr.track_id_stitched.notna()]
    df_tr["track_id_stitched"] = df_tr["track_id_stitched"].astype(int)
    # Moda de equipo por jugador cosido (M2.0) → sin parpadeos de color
    mode = (df_tr.dropna(subset=["team"]).groupby("track_id_stitched")["team"]
            .agg(lambda s: int(s.mode().iloc[0])))
    df_tr["team_mode"] = df_tr["track_id_stitched"].map(mode).fillna(-1).astype(int)
    df_ball = df[df.source == "ball"].copy()

    tactical = _load_json(CLEAN / "tactical_summaries.json")
    narrations = _load_json(CLEAN / "narrations.json")
    narr_by_w = {n["window_id"]: n for n in narrations}

    windows = []
    for w in tactical:
        n = narr_by_w.get(w["window_id"], {})
        windows.append({
            "id": w["window_id"],
            "t0": w["t0"], "t1": w["t1"],
            "f0": w.get("frame_start"), "f1": w.get("frame_end"),
            "block_height_m": w.get("block_height_m"),
            "compactness_m": w.get("block_compactness_m"),
            "transition_mps": w.get("transition_speed_mps"),
            "pressure": w.get("pressure_context"),
            "dominant": _team_label(w.get("dominant_team")),
            "n_a": w.get("n_arg"), "n_b": w.get("n_fra"),
            "centroid_a_m": round(w.get("centroid_arg_x_cm", 0) / 100, 1),
            "centroid_b_m": round(w.get("centroid_fra_x_cm", 0) / 100, 1),
            "narration": n.get("narracion_es", ""),
            "analysis": n.get("analisis_tactico", ""),
            "latency_ms": n.get("latency_ms"),
            "tokens_in": n.get("tokens_in"),
            "tokens_out": n.get("tokens_out"),
            "mode": n.get("mode"),
        })

    monitors = {}
    for key in ["m1", "m2", "m3", "m4"]:
        p = CLEAN / f"monitor_{key}.json"
        if p.exists():
            m = _load_json(p)
            monitors[key.upper()] = m.get("status")
            if key == "m2":
                for ck, cv in m.get("checks", {}).items():
                    monitors[ck] = "PASS" if cv.get("pass") else "FAIL"
    summary = _load_json(CLEAN / "pipeline_summary.json") if (CLEAN / "pipeline_summary.json").exists() else {}

    media_names = {
        "marked": "VIDEO_OMNIMORPH_POST_MATEMATICA.mp4",
        "radar": "VIDEO_RADAR_POST_MATEMATICA.mp4",
        "raw": "VIDEO_UNIFICADO_TODOS_JUNTOS.mp4",
        "original": "ORIGINAL_L6sbfskaTDQ-720-13.mp4",
        "audio": "NARRACION_COMPLETA_60S.wav",
        "vtt": "narrations_es.vtt",
    }

    data = {
        "meta": {
            "match": "BRA vs GER · Mundial 2014 · Semifinal",
            "team_a": "BRA", "team_b": "GER",
            "fps": fps, "n_frames": n_frames, "duration_s": round(n_frames / fps, 2),
            "pitch_cm": [PITCH_W, PITCH_H],
            "coord_unit": "dm",
            "model": "ibm/granite-4-h-small",
            "all_pass": summary.get("all_pass"),
        },
        "media": {k: f"../media/{v}" for k, v in media_names.items()},
        "monitors": monitors,
        "windows": windows,
        "players": build_players(df_tr, fps),
        "frames": build_frames(df_tr, df_ball, n_frames),
    }

    out_json = OUT_DATA / "mateo_data.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[OK] {out_json}  ({out_json.stat().st_size / 1024:.0f} KB)  "
          f"frames={n_frames} players={len(data['players'])} windows={len(windows)}")

    if not args.no_media:
        OUT_MEDIA.mkdir(parents=True, exist_ok=True)
        sources = {
            media_names["marked"]: CLIP_DIR / media_names["marked"],
            media_names["radar"]: CLIP_DIR / media_names["radar"],
            media_names["raw"]: CLIP_DIR / media_names["raw"],
            media_names["original"]: ORIG_VIDEO,
            media_names["audio"]: AUDIO / media_names["audio"],
            media_names["vtt"]: CLEAN / media_names["vtt"],
        }
        for name, src in sources.items():
            if src.exists():
                shutil.copy2(src, OUT_MEDIA / name)
                print(f"[OK] media/{name}  ({src.stat().st_size / (1024 * 1024):.1f} MB)")
            else:
                print(f"[!!] Falta: {src}")


if __name__ == "__main__":
    main()
