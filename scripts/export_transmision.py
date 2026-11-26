"""
scripts/export_transmision.py
=============================
Genera dashboard/data/transmision.json con los datos de la página Transmisión
(video, narraciones, cajas de jugadores, balón, protagonista por cercanía, ficha).

Entrada:
  data/clean/objects_cleaned.parquet
  dashboard/data/mateo_data.json
  dashboard/data/partido/partido.json

Salida:
  dashboard/data/transmision.json

Uso:
  .venv/Scripts/python.exe scripts/export_transmision.py
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent

CLIP_INICIO_S = 63  # Dato del usuario (2026-11-21): el clip va del 1:03 al 1:39 del partido

PARQUET  = ROOT / "data" / "clean" / "objects_cleaned.parquet"
MATEO    = ROOT / "dashboard" / "data" / "mateo_data.json"
PARTIDO  = ROOT / "dashboard" / "data" / "partido" / "partido.json"
OUT      = ROOT / "dashboard" / "data" / "transmision.json"
CURIOSOS = ROOT / "dashboard" / "data" / "datos_curiosos.json"   # scripts/generar_datos_curiosos.py

VIDEO_W, VIDEO_H = 1280, 720   # resolución de las cajas en píxeles
DIST_MAX_PX      = 120         # distancia máxima para considerar "cerca" del balón (§4)
FRAMES_MINIMOS   = 15          # mínimo de cuadros cerca para ser protagonista (§4)


def _load(p: pathlib.Path) -> dict | list:
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _verificar_entradas() -> None:
    for p in (PARQUET, MATEO, PARTIDO):
        if not p.exists():
            print(f"[FALLA] falta {p.relative_to(ROOT)}")
            sys.exit(1)


def _etiqueta(jugador: dict, codigo_equipo: str) -> str:
    """Regla §4: etiqueta de un jugador."""
    certeza = jugador.get("certeza")
    nombre  = jugador.get("jugador")
    dorsal  = jugador.get("dorsal")
    team    = jugador.get("team")
    if team == 2:
        return "Árbitro"
    if certeza in ("alta", "media") and nombre:
        return f"{dorsal} · {nombre.title()}"
    if dorsal is not None:
        return f"#{dorsal} {codigo_equipo}"
    return f"Jugador {codigo_equipo}"


def _build_jugadores(players: list, meta: dict) -> dict:
    """Construye el mapa id→{team, etiqueta} según §4."""
    team_a_codigo = meta["team_a"]   # SKN
    team_b_codigo = meta["team_b"]   # CRC
    codigos = {0: team_a_codigo, 1: team_b_codigo, 2: "Árbitro"}
    result: dict[str, dict] = {}
    for p in players:
        pid   = p["id"]
        team  = p.get("team", 2)
        codigo = codigos.get(team, "?")
        result[str(pid)] = {
            "team": team,
            "etiqueta": _etiqueta(p, codigo),
        }
    return result


def _build_cuadros_y_balon(df: pd.DataFrame, players: list, meta: dict
                           ) -> tuple[list[list], list]:
    """Construye cuadros (cajas 5 elementos) y balon (cx, cy o null)."""
    n_frames = meta["n_frames"]

    # ── Mapa de rastros → id canónico ─────────────────────────────────────────
    canon: dict[int, int] = {}
    for p in players:
        rastros = p.get("rastros") or []
        if rastros:
            for tid in rastros:
                canon[int(tid)] = int(rastros[0])

    ids_en_players = {p["id"] for p in players}

    # ── Jugadores ─────────────────────────────────────────────────────────────
    mask_tr = (
        (df["source"] == "track")
        & (df["class_name"] == "player")
        & df["track_id_stitched"].notna()
    )
    df_tr = df[mask_tr].copy()
    df_tr["track_id_stitched"] = df_tr["track_id_stitched"].astype(int)
    df_tr["id_canon"] = df_tr["track_id_stitched"].map(lambda t: canon.get(t, t))
    df_tr = df_tr[df_tr["id_canon"].isin(ids_en_players)]
    df_tr = df_tr.drop_duplicates(["frame", "id_canon"], keep="first")

    cuadros: list[list] = [[] for _ in range(n_frames)]
    for row in df_tr.sort_values(["frame", "id_canon"]).itertuples(index=False):
        f = int(row.frame)
        if f >= n_frames:
            continue
        x1 = int(max(0, min(VIDEO_W - 1, row.x1)))
        y1 = int(max(0, min(VIDEO_H - 1, row.y1)))
        x2 = int(max(0, min(VIDEO_W - 1, row.x2)))
        y2 = int(max(0, min(VIDEO_H - 1, row.y2)))
        cuadros[f].append([row.id_canon, x1, y1, x2, y2])

    # ── Balón: primera fila del cuadro con source=="ball" ─────────────────────
    df_ball = df[df["source"] == "ball"].copy()
    # Una sola detección por cuadro (primera por frame)
    df_ball = df_ball.sort_values("frame").drop_duplicates("frame", keep="first")
    balon_map: dict[int, list[int]] = {}
    for row in df_ball.itertuples(index=False):
        f = int(row.frame)
        if f >= n_frames:
            continue
        cx = int((row.x1 + row.x2) / 2)
        cy = int((row.y1 + row.y2) / 2)
        cx = max(0, min(VIDEO_W - 1, cx))
        cy = max(0, min(VIDEO_H - 1, cy))
        balon_map[f] = [cx, cy]

    balon: list = [balon_map.get(f) for f in range(n_frames)]

    return cuadros, balon


def _build_jugadas(windows: list, cuadros: list, balon: list) -> list:
    """Construye jugadas con protagonista por cercanía al balón y frames_cerca."""
    jugadas = []
    for w in windows:
        f0, f1 = int(w["f0"]), int(w["f1"])

        # Contar cuadros en que cada id es el más cercano al balón (≤ DIST_MAX_PX)
        cerca: dict[int, int] = {}
        for f in range(f0, min(f1 + 1, len(cuadros))):
            b = balon[f]
            if b is None:
                continue
            bx, by = b[0], b[1]
            mejor_dist = float("inf")
            mejor_id   = None
            for caja in cuadros[f]:
                pid, x1, y1, x2, y2 = caja
                cx = (x1 + x2) / 2.0
                cy = float(y2)
                d  = math.hypot(cx - bx, cy - by)
                if d < mejor_dist or (d == mejor_dist and (mejor_id is None or pid < mejor_id)):
                    mejor_dist = d
                    mejor_id   = pid
            if mejor_id is not None and mejor_dist <= DIST_MAX_PX:
                cerca[mejor_id] = cerca.get(mejor_id, 0) + 1

        # Protagonista = id con más cuadros cerca (empate → id menor), mínimo 15
        if cerca:
            prot_id = min(cerca, key=lambda k: (-cerca[k], k))
            fc = cerca[prot_id]
            if fc >= FRAMES_MINIMOS:
                protagonista = prot_id
                frames_cerca = fc
            else:
                protagonista = None
                frames_cerca = 0
        else:
            protagonista = None
            frames_cerca = 0

        jugadas.append({
            "id":           w["id"],
            "t0":           w["t0"],
            "t1":           w["t1"],
            "f0":           f0,
            "f1":           f1,
            "texto":        w["narration"],
            "protagonista": protagonista,
            "frames_cerca": frames_cerca,
        })
    return jugadas


def _build_ficha(partido_d: dict, local_codigo: str, visita_codigo: str) -> dict:
    """Construye la ficha del partido (estadio, asistencia, esquemas, entrenadores)."""
    p   = partido_d.get("partido", {})
    eqs = partido_d.get("equipos", {})

    local_eq  = next((v for v in eqs.values() if v.get("codigo") == local_codigo),  {})
    visita_eq = next((v for v in eqs.values() if v.get("codigo") == visita_codigo), {})

    return {
        "estadio":    p.get("estadio", ""),
        "asistencia": p.get("asistencia", 0),
        "local": {
            "esquema":    local_eq.get("esquema_inicial", ""),
            "entrenador": local_eq.get("entrenador", ""),
        },
        "visita": {
            "esquema":    visita_eq.get("esquema_inicial", ""),
            "entrenador": visita_eq.get("entrenador", ""),
        },
    }


def _marcador(goles: list, local_nombre: str) -> list[int]:
    """Cuenta goles antes de CLIP_INICIO_S."""
    local_g, visita_g = 0, 0
    for g in goles:
        seg = g.get("segundo_oficial")
        if seg is None or seg >= CLIP_INICIO_S:
            continue
        if g.get("equipo_anotador") == local_nombre:
            local_g += 1
        else:
            visita_g += 1
    return [local_g, visita_g]


def _color_uniforme(partido_d: dict, codigo: str, fallback: str) -> str:
    """Devuelve el color principal del uniforme del equipo con ese código.

    Busca en partido.json → colores_uniforme (clave = clave del equipo en equipos_orden)
    cuyo equipo tenga ese código. Si no existe, usa el fallback de mateo_data.
    """
    eqs = partido_d.get("equipos", {})
    cu  = partido_d.get("colores_uniforme", {})
    for clave, eq in eqs.items():
        if eq.get("codigo") == codigo and clave in cu:
            return cu[clave]
    return fallback


def _build_paneles(partido_d: dict, windows: list, meta: dict) -> dict:
    """Paneles laterales: datos fijos del partido completo por equipo, medidas
    por tramo (las mismas de MATEO) y datos curiosos (Granite verificado o plantilla)."""
    tc = (partido_d.get("estadisticas", {}).get("resumen_comparativo", {})
          .get("tiempo_completo", {}))
    curiosos = _load(CURIOSOS).get("equipos", {}) if CURIOSOS.exists() else {}

    def equipo(codigo: str) -> dict:
        clave = next((k for k, e in partido_d.get("equipos", {}).items()
                      if e.get("codigo") == codigo), None)
        e = partido_d.get("equipos", {}).get(clave, {})
        dato = lambda k: (tc.get(k) or {}).get(clave)
        goles = [{"minuto": g["minuto"], "nombre": g["anotador"]["nombre"],
                  "marcador": g["marcador_momento"]}
                 for g in partido_d.get("goles", []) if g.get("equipo_anotador") == e.get("pais")]
        return {
            "codigo": codigo,
            "nombre": e.get("pais", codigo),
            "esquema": e.get("esquema_inicial"),
            "entrenador": e.get("entrenador"),
            "partido": {
                "goles": dato("goles"),
                "posesion_pct": dato("posesion_pct"),
                "tiros_totales": dato("tiros_totales"),
                "tiros_a_puerta": dato("tiros_a_puerta"),
                "corners": dato("corners"),
                "tarjetas_amarillas": dato("tarjetas_amarillas"),
            },
            "goles": goles,
            "curiosos": curiosos.get(codigo, []),
        }

    tramos = []
    for w in windows:
        eqs = w.get("equipos") or {}
        tramos.append({
            "t0": w.get("t0"), "t1": w.get("t1"),
            "territorio": w.get("territorio"),
            "equipos": {c: {k: eqs.get(c, {}).get(k) for k in
                            ("posicion_m", "pct_campo_rival", "largo_m", "ancho_m")}
                        for c in (meta["team_a"], meta["team_b"])},
        })
    return {
        "local": equipo(meta["team_b"]),
        "visita": equipo(meta["team_a"]),
        "tramos": tramos,
        "fuente_partido": "Estadísticas del partido completo, de fuentes públicas (página Partido).",
    }


def main() -> None:
    _verificar_entradas()

    mateo_d   = _load(MATEO)
    partido_d = _load(PARTIDO)
    meta      = mateo_d["meta"]
    players   = mateo_d["players"]
    windows   = mateo_d["windows"]
    frames    = mateo_d["frames"]
    media     = mateo_d["media"]

    df = pd.read_parquet(PARQUET)

    local_nombre = meta["team_b_name"]   # CRC
    goles_data   = partido_d.get("goles", [])

    local_color  = _color_uniforme(partido_d, meta["team_b"], meta["team_b_color"])
    visita_color = _color_uniforme(partido_d, meta["team_a"], meta["team_a_color"])

    datos: dict = {
        "version": 1,
        "partido": {
            "titulo":        meta["titulo"],
            "competicion":   "Eliminatorias Concacaf · Mundial 2026",
            "local":  {"team": 1, "codigo": meta["team_b"], "nombre": meta["team_b_name"],
                       "color": local_color},
            "visita": {"team": 0, "codigo": meta["team_a"], "nombre": meta["team_a_name"],
                       "color": visita_color},
            "marcador":        _marcador(goles_data, local_nombre),
            "reloj_inicio_s":  CLIP_INICIO_S,
        },
        "video": {
            "src":      media["original"],
            "ancho":    VIDEO_W,
            "alto":     VIDEO_H,
            "fps":      meta["fps"],
            "n_frames": meta["n_frames"],
        },
        "narracion": {
            "audio": media["audio"],
            "vtt":   media["vtt"],
        },
        "jugadores": _build_jugadores(players, meta),
    }

    cuadros, balon = _build_cuadros_y_balon(df, players, meta)
    datos["cuadros"] = cuadros
    datos["balon"]   = balon
    datos["cancha"]  = frames
    datos["jugadas"] = _build_jugadas(windows, cuadros, balon)
    datos["ficha"]   = _build_ficha(partido_d, meta["team_b"], meta["team_a"])
    datos["paneles"] = _build_paneles(partido_d, windows, meta)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    n_bytes = OUT.stat().st_size
    print(
        f"[OK] dashboard/data/transmision.json  "
        f"cuadros={len(cuadros)}  "
        f"jugadores={len(datos['jugadores'])}  "
        f"jugadas={len(datos['jugadas'])}  "
        f"bytes={n_bytes}"
    )


if __name__ == "__main__":
    main()
