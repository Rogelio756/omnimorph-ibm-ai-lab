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
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from implementacion import partido_config

PARTIDO = partido_config.activo()
CLEAN = ROOT / "data" / "clean"
AUDIO = ROOT / "data" / "audio"
CLIP_DIR = PARTIDO.percepcion_dir
ORIG_VIDEO = ROOT / PARTIDO.video_archivo

DASH = ROOT / "dashboard"
OUT_DATA = DASH / "data"
OUT_MEDIA = DASH / "media"

PITCH_W, PITCH_H = 12000.0, 7000.0   # cm
V_MAX = 9.5                           # m/s (M2.3)
MEDIANA_FRAMES = 31                   # 1 s a 30 fps
PASO_FRAMES = 30                      # medir cada 1 s
HUECO_MAX_FRAMES = 3                  # más separación corta el tramo


def _load_json(p: pathlib.Path):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _team_label(v) -> str:
    """Código del engine (actual o histórico ARG/FRA) -> código del equipo del partido activo."""
    e = PARTIDO.equipo_por_codigo(v)
    return e.codigo if e else v


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


def distancia_filtrada(fr: np.ndarray, x: np.ndarray, y: np.ndarray, fps: float) -> tuple:
    """Distancia en metros y segundos medidos, con la posición filtrada en ventanas de 1 s.

    La calibración salta en cada cuadro: una mediana móvil y un paso de 1 s evitan contar
    esos saltos como carrera. Los tramos de menos de 1 s no se miden.
    """
    dist, segundos = 0.0, 0.0
    cortes = np.where(np.diff(fr) > HUECO_MAX_FRAMES)[0] + 1
    for tramo in np.split(np.arange(len(fr)), cortes):
        if len(tramo) <= PASO_FRAMES:
            continue
        xm = pd.Series(x[tramo]).rolling(MEDIANA_FRAMES, center=True, min_periods=1).median().to_numpy()
        ym = pd.Series(y[tramo]).rolling(MEDIANA_FRAMES, center=True, min_periods=1).median().to_numpy()
        i = np.arange(0, len(tramo), PASO_FRAMES)
        dt = np.diff(fr[tramo][i]) / fps
        v = np.clip(np.hypot(np.diff(xm[i]), np.diff(ym[i])) / dt, 0, V_MAX)
        dist += float(np.sum(v * dt))
        segundos += float(np.sum(dt))
    return dist, segundos


def build_players(df_tr: pd.DataFrame, fps: float, dorsales: dict | None = None) -> list:
    """Por rastro: distancia aproximada, segundos medidos y mapa de calor 12×7."""
    players = []
    for tid, g in df_tr.groupby("track_id_stitched"):
        g = g.sort_values("frame")
        inb = g[(g.pitch_x_smooth.between(0, PITCH_W)) & (g.pitch_y_smooth.between(0, PITCH_H))]
        if len(inb) < 15:
            continue
        team = int(g["team_mode"].iloc[0]) if g["team_mode"].iloc[0] in (0, 1) else 2
        if (g["class_id"] == 3).mean() > 0.5:
            team = 2

        dist, segundos = distancia_filtrada(inb.frame.to_numpy(), inb.pitch_x.to_numpy() / 100.0,
                                            inb.pitch_y.to_numpy() / 100.0, fps)
        if segundos == 0:
            continue

        heat, _, _ = np.histogram2d(
            inb.pitch_x_smooth, inb.pitch_y_smooth,
            bins=[12, 7], range=[[0, PITCH_W], [0, PITCH_H]],
        )
        heat = (heat / heat.max()).round(2).tolist() if heat.max() > 0 else heat.tolist()

        jugador = {
            "id": int(tid),
            "team": team,
            "frames": int(len(inb)),
            "dist_m": round(dist, 1),
            "segundos": round(segundos, 1),
            "heat": heat,   # [12][7] normalizado 0..1
        }
        if dorsales and int(tid) in dorsales:
            jugador.update(dorsales[int(tid)])
        players.append(jugador)
    return players


def cargar_dorsales() -> dict:
    """Rastro -> {dorsal, jugador, certeza, validado} desde la identificación manual del partido activo.

    Usa rastros_dorsales.json (validado por el equipo de análisis) si existe; si no,
    rastros_dorsales_borrador.json, marcado como no validado.
    """
    for nombre, validado in (("rastros_dorsales.json", True), ("rastros_dorsales_borrador.json", False)):
        ruta = PARTIDO.datos_dir / nombre
        if not ruta.exists():
            continue
        datos = _load_json(ruta)
        mapa = {}
        for a in datos.get("asignados", []):
            for tid in a["rastros"]:
                mapa[int(tid)] = {
                    "dorsal": a["dorsal"],
                    "jugador": a["jugador"],
                    "certeza": a.get("certeza", "media"),
                    "validado": validado,
                }
        print(f"[OK] dorsales: {len(mapa)} rastros desde {ruta.name} ({'validado' if validado else 'por validar'})")
        return mapa
    return {}


def recortar_video(src: pathlib.Path, dst: pathlib.Path, n_frames: int) -> None:
    """Copia los primeros n_frames del video (H.264) y el mismo tramo de su audio (AAC).

    El audio original es el que suena en los modos "Audio original" y "Narrador MATEO" del tablero.
    """
    import av
    tmp = dst.with_suffix(".tmp.mp4")
    with av.open(str(src)) as inp, av.open(str(src)) as inp_audio, \
            av.open(str(tmp), "w", options={"movflags": "+faststart"}) as out:
        v_in = inp.streams.video[0]
        # Las dos pistas se declaran antes de escribir el primer paquete
        v_out = out.add_stream("libx264", rate=v_in.average_rate)
        v_out.width, v_out.height = v_in.codec_context.width, v_in.codec_context.height
        v_out.pix_fmt = "yuv420p"
        v_out.options = {"crf": "20", "preset": "veryfast"}
        a_in = inp_audio.streams.audio[0] if inp_audio.streams.audio else None
        if a_in is not None:
            sr = a_in.codec_context.sample_rate
            a_out = out.add_stream("aac", rate=sr)
            a_out.layout = "stereo"
            remuestreo = av.AudioResampler(format="fltp", layout="stereo", rate=sr)

        for i, frame in enumerate(inp.decode(v_in)):
            if i >= n_frames:
                break
            for pkt in v_out.encode(frame):
                out.mux(pkt)
        for pkt in v_out.encode():
            out.mux(pkt)

        if a_in is not None:
            limite = int(n_frames / float(v_in.average_rate) * sr)
            muestras = 0
            for frame in inp_audio.decode(a_in):
                if muestras >= limite:
                    break
                frame.pts = None
                for f in remuestreo.resample(frame):
                    f.pts = muestras
                    muestras += f.samples
                    for pkt in a_out.encode(f):
                        out.mux(pkt)
            for pkt in a_out.encode():
                out.mux(pkt)
    tmp.replace(dst)


PARTIDO_SRC = PARTIDO.datos_dir
OUT_PARTIDO = OUT_DATA / "partido"


def export_partido() -> None:
    """
    Copia los datos de Brasil 1-7 Alemania (data/partidos/) al frontend.
    Genera dashboard/data/partido/partido.json y copia los SVG y PROCEDENCIA.md.
    """
    OUT_PARTIDO.mkdir(parents=True, exist_ok=True)
    out = OUT_PARTIDO / "partido.json"
    if not (PARTIDO_SRC / "partido" / "contexto_partido.json").exists():
        # Aún no llegan los datos verificados del partido: la página lo dice en vez de mostrar otro partido.
        data = {"pendiente": True, "id": PARTIDO.id, "titulo": PARTIDO.titulo,
                "competicion": PARTIDO.competicion, "etiqueta": PARTIDO.etiqueta_corta}
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        for viejo in ("mapa_8_goles.svg", "radar_gol_muller.svg", "PROCEDENCIA.md"):
            (OUT_PARTIDO / viejo).unlink(missing_ok=True)
        print(f"[OK] {out}  (pendiente: faltan los datos verificados de {PARTIDO.id})")
        return
    contexto = _load_json(PARTIDO_SRC / "partido" / "contexto_partido.json")
    data = {
        "partido": contexto["partido_info"],
        "equipos": contexto["equipos"],
        "estadisticas": _load_json(PARTIDO_SRC / "partido" / "estadisticas_partido.json"),
        "goles": _load_json(PARTIDO_SRC / "partido" / "cronologia_goles.json"),
        "gol_muller": _load_json(PARTIDO_SRC / "gol_muller" / "gol_muller_min11.json"),
    }
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
    fps = PARTIDO.fps

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
        "original": f"ORIGINAL_{PARTIDO.video_dataset_id}",
        "audio": "NARRACION_COMPLETA_60S.wav",
        "vtt": "narrations_es.vtt",
    }

    data = {
        "meta": {
            "match": f"{PARTIDO.equipo(0).codigo} vs {PARTIDO.equipo(1).codigo} · {PARTIDO.competicion}",
            "partido_id": PARTIDO.id,
            "titulo": PARTIDO.titulo,
            "team_a": PARTIDO.equipo(0).codigo, "team_b": PARTIDO.equipo(1).codigo,
            "team_a_name": PARTIDO.equipo(0).nombre, "team_b_name": PARTIDO.equipo(1).nombre,
            "team_a_color": PARTIDO.equipo(0).color_ui, "team_b_color": PARTIDO.equipo(1).color_ui,
            "etiqueta": PARTIDO.etiqueta_corta,
            "fps": fps, "n_frames": n_frames, "duration_s": round(n_frames / fps, 2),
            "pitch_cm": [PITCH_W, PITCH_H],
            "coord_unit": "dm",
            "model": "ibm/granite-4-h-small",
            "all_pass": summary.get("all_pass"),
        },
        "media": {k: f"../media/{v}" for k, v in media_names.items()},
        "monitors": monitors,
        "windows": windows,
        "players": build_players(df_tr, fps, cargar_dorsales()),
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
            if name == media_names["original"] and src.exists():
                recortar_video(src, OUT_MEDIA / name, n_frames)
                print(f"[OK] media/{name}  (primeros {n_frames} cuadros del original)")
                continue
            if src.exists():
                shutil.copy2(src, OUT_MEDIA / name)
                print(f"[OK] media/{name}  ({src.stat().st_size / (1024 * 1024):.1f} MB)")
            else:
                print(f"[!!] Falta: {src}")


if __name__ == "__main__":
    main()
