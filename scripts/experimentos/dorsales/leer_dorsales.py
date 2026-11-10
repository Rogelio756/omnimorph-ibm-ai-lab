"""
leer_dorsales.py  ·  Pasos 3–6 del experimento de dorsales
============================================================
Paso 3: Genera recortes de torso por cuadro y rastro del clip de TV.
Paso 4: Clasifica con YOLOv8-cls y vota por rastro.
Paso 5: Genera hoja_contactos.jpg con ejemplos por rastro.
Paso 6: Mide cobertura, precisión visual (ojo) y cruza números imposibles.

Credenciales en .env:
  ROBOFLOW_API_KEY, ROBOFLOW_NUBE_AUTORIZADA (opcional, = "si" para usar nube)

Uso:
    python scripts/experimentos/dorsales/leer_dorsales.py [--nube] [--max-recortes-nube N]
"""
import argparse
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from dotenv import load_dotenv


# ── rutas ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]
CLIP_PATH = ROOT / "data" / "videos" / "candidatos_720p" / "HP3zxNuoWXE-720-15.mp4"
PARQUET = ROOT / "data" / "clean" / "objects_cleaned.parquet"
TRAIN_DIR = ROOT / "outputs" / "experimentos" / "dorsales" / "entrenamiento"
RECORTES_DIR = ROOT / "outputs" / "experimentos" / "dorsales" / "recortes"
OUT_DIR = ROOT / "outputs" / "experimentos" / "dorsales"

FRAME_STEP = 5          # cada N cuadros
MIN_ALTURA_PX = 40      # caja mínima de alto en px
TORSO_TOP = 0.15        # inicio vertical del torso (% de altura de caja)
TORSO_BOT = 0.65        # fin vertical del torso
MARGEN = 0.10           # margen horizontal adicional
ESCALA = 4              # ×4 upscale con INTER_CUBIC
UMBRAL_CONFIANZA = 0.66
VOTOS_MIN = 3           # mínimo votos para asignar número
PROP_MIN = 0.60         # proporción mínima sobre total de recortes

# clases de "sin número" según Roboflow
SIN_NUMERO_CLASES = {"no number", "unreadble"}

# Clases que el dataset NO tiene (limitación conocida)
CLASES_IMPOSIBLES_1_23 = {"16", "19"}


def load_env():
    load_dotenv(ROOT / ".env")


# ── utilidades ─────────────────────────────────────────────────────────────────
def mejor_modelo() -> Path:
    """Devuelve la ruta al best.pt más reciente de TRAIN_DIR."""
    candidatos = sorted(TRAIN_DIR.rglob("best.pt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidatos:
        raise FileNotFoundError(
            f"No se encontró best.pt en {TRAIN_DIR}. "
            "Ejecuta entrenar.py primero."
        )
    return candidatos[0]


def recortar_torso(frame_img: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray | None:
    """Recorta el torso (franja 15–65 %) de una caja de jugador y amplía ×4."""
    h_img, w_img = frame_img.shape[:2]
    bx1, by1, bx2, by2 = int(x1), int(y1), int(x2), int(y2)
    alto = by2 - by1
    if alto < MIN_ALTURA_PX:
        return None

    t_top = by1 + int(alto * TORSO_TOP)
    t_bot = by1 + int(alto * TORSO_BOT)
    margen_px = int((bx2 - bx1) * MARGEN)
    rx1 = max(0, bx1 - margen_px)
    rx2 = min(w_img, bx2 + margen_px)

    recorte = frame_img[t_top:t_bot, rx1:rx2]
    if recorte.size == 0:
        return None
    h_r = t_bot - t_top
    w_r = rx2 - rx1
    nuevo_h = h_r * ESCALA
    nuevo_w = w_r * ESCALA
    ampliado = cv2.resize(recorte, (nuevo_w, nuevo_h), interpolation=cv2.INTER_CUBIC)
    return ampliado


# ── paso 3 ──────────────────────────────────────────────────────────────────────
def generar_recortes() -> list[dict]:
    """Genera recortes de torso cada FRAME_STEP cuadros. Retorna lista de metadatos."""
    RECORTES_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_parquet(PARQUET)

    # filtrar árbitros (class_id == 3) y quedarnos solo con jugadores
    jugadores = df[df["class_id"] != 3].copy()

    cap = cv2.VideoCapture(str(CLIP_PATH))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_a_procesar = list(range(0, min(1080, total_frames), FRAME_STEP))

    metadatos = []
    tamanos_antes = []
    frame_idx_actual = -1
    frame_img = None

    print(f"[recortes] {len(frames_a_procesar)} cuadros a procesar (cada {FRAME_STEP})…")

    for fidx in frames_a_procesar:
        if fidx != frame_idx_actual:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fidx)
            ret, frame_img = cap.read()
            if not ret or frame_img is None:
                continue
            frame_idx_actual = fidx

        rows = jugadores[jugadores["frame"] == fidx]
        for _, row in rows.iterrows():
            tid = row.get("track_id_stitched")
            if pd.isna(tid):
                continue
            tid = int(tid)
            team = int(row["team"]) if not pd.isna(row.get("team")) else -1
            x1, y1, x2, y2 = row["x1"], row["y1"], row["x2"], row["y2"]
            alto = y2 - y1
            if alto < MIN_ALTURA_PX:
                continue

            recorte = recortar_torso(frame_img, x1, y1, x2, y2)
            if recorte is None:
                continue

            nombre = f"f{fidx}_t{tid}.png"
            cv2.imwrite(str(RECORTES_DIR / nombre), recorte)
            tamanos_antes.append((int(x2 - x1), int(y2 - y1)))
            metadatos.append({
                "frame": fidx,
                "track_id_stitched": tid,
                "team": team,
                "archivo": nombre,
            })

    cap.release()

    if tamanos_antes:
        w_med = int(np.median([t[0] for t in tamanos_antes]))
        h_med = int(np.median([t[1] for t in tamanos_antes]))
        print(f"[recortes] {len(metadatos)} recortes generados")
        print(f"  Tamaño mediano de caja ANTES de ampliar: {w_med} × {h_med} px")
    else:
        print("[recortes] No se generaron recortes.")
    return metadatos


# ── paso 4 ──────────────────────────────────────────────────────────────────────
def clasificar_y_votar(metadatos: list[dict]) -> tuple[list[dict], dict]:
    """Clasifica cada recorte y vota por rastro. Devuelve (predicciones, dorsales_por_rastro)."""
    from ultralytics import YOLO

    pt = mejor_modelo()
    print(f"[clasificacion] cargando {pt}")
    model = YOLO(str(pt))

    # inferencia en lotes
    pred_por_recorte = []
    print(f"[clasificacion] {len(metadatos)} recortes…")

    for meta in metadatos:
        img_path = RECORTES_DIR / meta["archivo"]
        if not img_path.exists():
            continue
        results = model.predict(str(img_path), verbose=False)
        if not results:
            continue
        r = results[0]
        # top-3
        probs = r.probs
        top3_idx = probs.top5[:3]
        top3 = {model.names[int(i)]: float(probs.data[i]) for i in top3_idx}
        top1_name = model.names[int(probs.top1)]
        top1_conf = float(probs.top1conf)

        # numero solo si cumple umbral y no es "sin número"
        if top1_conf >= UMBRAL_CONFIANZA and top1_name not in SIN_NUMERO_CLASES:
            numero = top1_name
        else:
            numero = None

        pred_por_recorte.append({
            "frame": meta["frame"],
            "track_id_stitched": meta["track_id_stitched"],
            "team": meta["team"],
            "top3": top3,
            "numero": numero,
        })

    # guardar predicciones
    out_pred = OUT_DIR / "predicciones_por_recorte.jsonl"
    with out_pred.open("w", encoding="utf-8") as f:
        for p in pred_por_recorte:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"[clasificacion] predicciones → {out_pred}")

    # votación por rastro
    # duración visible por rastro
    df = pd.read_parquet(PARQUET)
    jugadores = df[df["class_id"] != 3].copy()
    segundos_por_rastro = (
        jugadores.groupby("track_id_stitched")["t"].agg(lambda x: x.max() - x.min()).to_dict()
    )
    team_por_rastro = (
        jugadores.groupby("track_id_stitched")["team"].agg(
            lambda x: float(x.dropna().mode().iloc[0]) if len(x.dropna()) > 0 else -1.0
        ).to_dict()
    )

    from collections import Counter, defaultdict
    votos_map: dict[int, Counter] = defaultdict(Counter)
    n_recortes_map: dict[int, int] = defaultdict(int)

    for p in pred_por_recorte:
        tid = p["track_id_stitched"]
        n_recortes_map[tid] += 1
        if p["numero"] is not None:
            votos_map[tid][p["numero"]] += 1

    dorsales = {}
    for tid in set(n_recortes_map.keys()):
        total = n_recortes_map[tid]
        votos = dict(votos_map[tid])
        numero_ganador = None
        if votos:
            candidato, cnt = max(votos.items(), key=lambda x: x[1])
            if cnt >= VOTOS_MIN and cnt / total >= PROP_MIN:
                numero_ganador = candidato
        segundos = float(segundos_por_rastro.get(tid, 0.0))
        team = int(team_por_rastro.get(tid, -1)) if not math.isnan(float(team_por_rastro.get(tid, -1))) else -1
        dorsales[tid] = {
            "track_id_stitched": tid,
            "team": team,
            "numero": numero_ganador,
            "votos": votos,
            "n_recortes": total,
            "segundos_visible": round(segundos, 2),
        }

    out_dorsales = OUT_DIR / "dorsales_por_rastro.json"
    with out_dorsales.open("w", encoding="utf-8") as f:
        json.dump(list(dorsales.values()), f, indent=2, ensure_ascii=False)
    print(f"[votacion] dorsales → {out_dorsales}")

    return pred_por_recorte, dorsales


# ── paso 4 · nube Roboflow (opcional) ──────────────────────────────────────────
def clasificar_nube(metadatos: list[dict], max_recortes: int = 3000) -> list[dict]:
    """Usa inference-sdk para enviar recortes a la nube de Roboflow (max 3000)."""
    try:
        from inference_sdk import InferenceHTTPClient  # type: ignore
    except ImportError:
        print("[nube] inference-sdk no instalado. Instala con: pip install inference-sdk")
        return []

    api_key = os.environ.get("ROBOFLOW_API_KEY")
    project = os.environ.get("ROBOFLOW_PROJECT")
    version = os.environ.get("ROBOFLOW_VERSION")
    if not all([api_key, project, version]):
        print("[nube] Faltan variables de entorno para la nube.")
        return []

    client = InferenceHTTPClient(api_url="https://classify.roboflow.com", api_key=api_key)
    muestra = metadatos[:max_recortes]
    enviados = 0
    resultados = []

    print(f"[nube] enviando hasta {max_recortes} recortes…")
    for meta in muestra:
        img_path = RECORTES_DIR / meta["archivo"]
        if not img_path.exists():
            continue
        try:
            resp = client.infer(str(img_path), model_id=f"{project}/{version}")
            pred_label = resp.get("top", None)
            conf = resp.get("confidence", 0.0)
            numero = pred_label if conf >= UMBRAL_CONFIANZA and pred_label not in SIN_NUMERO_CLASES else None
            resultados.append({
                "frame": meta["frame"],
                "track_id_stitched": meta["track_id_stitched"],
                "team": meta["team"],
                "numero_nube": numero,
                "conf_nube": round(conf, 4),
                "label_nube": pred_label,
            })
            enviados += 1
        except Exception as e:
            print(f"[nube] error en {meta['archivo']}: {e}")

    out = OUT_DIR / "predicciones_nube.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for r in resultados:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[nube] {enviados} recortes enviados. Predicciones → {out}")
    return resultados


# ── paso 5 ──────────────────────────────────────────────────────────────────────
def generar_hoja_contactos(pred_por_recorte: list[dict], dorsales: dict):
    """Genera hoja_contactos.jpg: hasta 6 recortes por rastro con número predicho."""
    from collections import defaultdict

    # agrupar por rastro
    por_rastro: dict[int, list] = defaultdict(list)
    for p in pred_por_recorte:
        por_rastro[p["track_id_stitched"]].append(p)

    # ordenar rastros por segundos visible (descendente)
    rastros_ordenados = sorted(
        por_rastro.keys(),
        key=lambda t: dorsales.get(t, {}).get("segundos_visible", 0),
        reverse=True,
    )[:30]  # máximo 30 rastros en la hoja

    MAX_POR_RASTRO = 6
    THUMB_W, THUMB_H = 96, 96
    COLS = MAX_POR_RASTRO + 1  # +1 para la etiqueta
    ROWS = len(rastros_ordenados)

    if ROWS == 0:
        print("[hoja] Sin rastros para mostrar.")
        return

    CELL_W, CELL_H = THUMB_W + 2, THUMB_H + 20
    img_out = np.full(
        (ROWS * CELL_H + 30, COLS * CELL_W + 80, 3), 245, dtype=np.uint8
    )

    for row_i, tid in enumerate(rastros_ordenados):
        recortes = por_rastro[tid][:MAX_POR_RASTRO]
        info = dorsales.get(tid, {})
        numero_votado = info.get("numero") or "?"
        team = info.get("team", -1)
        team_label = "SKN" if team == 0 else "CRC" if team == 1 else "?"

        y_off = row_i * CELL_H + 30

        # etiqueta del rastro
        label_txt = f"T{tid} {team_label} #{numero_votado}"
        cv2.putText(
            img_out, label_txt, (4, y_off + THUMB_H // 2),
            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (30, 30, 30), 1, cv2.LINE_AA,
        )

        for col_i, p in enumerate(recortes):
            img_path = RECORTES_DIR / f"f{p['frame']}_t{p['track_id_stitched']}.png"
            if not img_path.exists():
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            thumb = cv2.resize(img, (THUMB_W, THUMB_H))
            x_off = 80 + col_i * CELL_W
            img_out[y_off: y_off + THUMB_H, x_off: x_off + THUMB_W] = thumb

            # número predicho encima
            pred_n = p.get("numero") or "-"
            cv2.putText(
                img_out, str(pred_n),
                (x_off + 2, y_off + 11),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                (0, 200, 0) if pred_n != "-" else (180, 180, 180),
                1, cv2.LINE_AA,
            )

    out_path = OUT_DIR / "hoja_contactos.jpg"
    cv2.imwrite(str(out_path), img_out, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f"[hoja] → {out_path}")


# ── paso 6 ──────────────────────────────────────────────────────────────────────
def medir(pred_por_recorte: list[dict], dorsales: dict):
    """Calcula cobertura y métricas básicas."""
    # cobertura de recortes
    total_recortes = len(pred_por_recorte)
    con_numero = sum(1 for p in pred_por_recorte if p.get("numero") is not None)
    cobertura_recortes = con_numero / total_recortes if total_recortes else 0.0

    # rastros con más tiempo (top 20)
    rastros_sorted = sorted(
        dorsales.values(),
        key=lambda d: d["segundos_visible"],
        reverse=True,
    )[:20]
    con_dorsal = sum(1 for d in rastros_sorted if d["numero"] is not None)
    cobertura_rastros_top20 = con_dorsal / len(rastros_sorted) if rastros_sorted else 0.0

    print("\n" + "═" * 60)
    print("MÉTRICAS — PASO 6")
    print("═" * 60)
    print(f"  Total recortes:               {total_recortes}")
    print(f"  Con número (conf ≥ 0.66):     {con_numero}  ({cobertura_recortes:.1%})")
    print(f"  Top-20 rastros con número:    {con_dorsal}/{len(rastros_sorted)}  ({cobertura_rastros_top20:.1%})")
    print()
    print("  Top-20 rastros:")
    for d in rastros_sorted:
        n = d["numero"] or "(sin número)"
        print(f"    T{d['track_id_stitched']:>3}  team={d['team']}  {n:>12}  {d['n_recortes']:>4} recortes  {d['segundos_visible']:.1f}s")

    # números imposibles (16, 19 no existen en el dataset)
    imposibles = [d for d in rastros_sorted if d["numero"] in CLASES_IMPOSIBLES_1_23]
    if imposibles:
        print(f"\n  ⚠️  Dorsales imposibles (no en dataset): {[d['numero'] for d in imposibles]}")

    # guardar resumen
    resumen = {
        "total_recortes": total_recortes,
        "recortes_con_numero": con_numero,
        "cobertura_recortes_pct": round(cobertura_recortes * 100, 1),
        "top20_rastros_con_numero": con_dorsal,
        "top20_total": len(rastros_sorted),
        "cobertura_top20_pct": round(cobertura_rastros_top20 * 100, 1),
        "criterio_parada_activado": cobertura_rastros_top20 < 0.10,
    }
    out = OUT_DIR / "metricas_paso6.json"
    out.write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"\n[metricas] → {out}")

    if cobertura_rastros_top20 < 0.10:
        print(
            "\n⚠️  CRITERIO DE PARADA: menos del 10 % de los 20 rastros principales obtiene número.\n"
            "   Ajustar parámetros en bucle no está recomendado. Reportar y proponer IBM Granite Vision."
        )

    return resumen


# ── punto de entrada ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Pasos 3–6 del experimento de dorsales")
    parser.add_argument(
        "--nube", action="store_true",
        help="Usar API de Roboflow en la nube (requiere ROBOFLOW_NUBE_AUTORIZADA=si en .env)"
    )
    parser.add_argument("--max-recortes-nube", type=int, default=3000)
    args = parser.parse_args()

    load_env()

    print("=== Paso 3: generando recortes ===")
    metadatos = generar_recortes()
    if not metadatos:
        print("[error] No se generaron recortes. Verificar clip y parquet.")
        return

    print("\n=== Paso 4: clasificando y votando ===")
    pred_por_recorte, dorsales = clasificar_y_votar(metadatos)

    # nube opcional
    if args.nube:
        autorizada = os.environ.get("ROBOFLOW_NUBE_AUTORIZADA", "").strip().lower()
        if autorizada == "si":
            print("\n=== Paso 4b: clasificación en la nube (autorizada) ===")
            clasificar_nube(metadatos, max_recortes=args.max_recortes_nube)
        else:
            print("[nube] ROBOFLOW_NUBE_AUTORIZADA no es 'si'. Saltando clasificación en la nube.")

    print("\n=== Paso 5: hoja de contactos ===")
    generar_hoja_contactos(pred_por_recorte, dorsales)

    print("\n=== Paso 6: métricas ===")
    medir(pred_por_recorte, dorsales)

    print("\n✅ Pasos 3–6 completados.")


if __name__ == "__main__":
    main()
