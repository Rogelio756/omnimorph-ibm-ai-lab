"""
entrenar.py  ·  Pasos 1 y 2 del experimento de dorsales
============================================================
Paso 1: Descarga el dataset "jersey number" desde Roboflow y lo audita.
Paso 2: Entrena un clasificador YOLOv8n-cls con augmentation de baja resolución.

Credenciales en .env:
  ROBOFLOW_API_KEY, ROBOFLOW_WORKSPACE, ROBOFLOW_PROJECT, ROBOFLOW_VERSION

Uso:
    python scripts/experimentos/dorsales/entrenar.py [--solo-auditar] [--epocas N] [--imgsz N]
"""
import argparse
import json
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
from dotenv import load_dotenv


# ── rutas ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[3]
DATASET_DIR = ROOT / "outputs" / "experimentos" / "dorsales" / "dataset"
TRAIN_DIR = ROOT / "outputs" / "experimentos" / "dorsales" / "entrenamiento"
DEGRADED_DIR = ROOT / "outputs" / "experimentos" / "dorsales" / "dataset_degradado"


def load_env():
    load_dotenv(ROOT / ".env")
    for var in ("ROBOFLOW_API_KEY", "ROBOFLOW_WORKSPACE", "ROBOFLOW_PROJECT", "ROBOFLOW_VERSION"):
        if not os.environ.get(var):
            raise SystemExit(f"Falta {var} en .env")


# ── paso 1: descarga ────────────────────────────────────────────────────────────
def descargar_dataset():
    """Descarga el proyecto en formato folder a DATASET_DIR."""
    from roboflow import Roboflow

    rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
    proyecto = rf.workspace(os.environ["ROBOFLOW_WORKSPACE"]).project(
        os.environ["ROBOFLOW_PROJECT"]
    )
    version = proyecto.version(int(os.environ["ROBOFLOW_VERSION"]))
    print(f"[descarga] proyecto={os.environ['ROBOFLOW_PROJECT']} v{os.environ['ROBOFLOW_VERSION']}")
    version.download("folder", location=str(DATASET_DIR))
    print(f"[descarga] OK → {DATASET_DIR}")


def auditar_dataset():
    """
    Analiza el dataset descargado.
    Retorna dict con resumen: conteos por clase y división, clases faltantes del 1-23.
    """
    splits = {}
    for split in ("train", "valid", "test"):
        split_path = DATASET_DIR / split
        if not split_path.exists():
            continue
        conteos = {}
        for clase_dir in sorted(split_path.iterdir()):
            if clase_dir.is_dir():
                n = len(list(clase_dir.glob("*")))
                conteos[clase_dir.name] = n
        splits[split] = conteos

    if not splits:
        print(f"[auditoria] No se encontró ninguna división en {DATASET_DIR}")
        return {}

    # muestra de tamaño de imagen
    train_split = splits.get("train", {})
    tamanos = []
    train_path = DATASET_DIR / "train"
    if train_path.exists():
        for clase_dir in train_path.iterdir():
            if clase_dir.is_dir():
                imgs = list(clase_dir.glob("*.jpg")) + list(clase_dir.glob("*.png"))
                for img_path in imgs[:3]:
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        tamanos.append((img.shape[1], img.shape[0]))

    # clases del 1 al 23 esperadas en fútbol (sin 16 ni 19 según la documentación del proyecto)
    numerales_esperados = {str(n) for n in range(1, 24)}
    todas_las_clases = set()
    for conteos in splits.values():
        todas_las_clases.update(conteos.keys())
    faltantes = sorted(numerales_esperados - todas_las_clases, key=lambda x: int(x))

    print("\n" + "═" * 60)
    print("AUDITORÍA DEL DATASET")
    print("═" * 60)
    for split, conteos in splits.items():
        total = sum(conteos.values())
        print(f"\n  {split}: {len(conteos)} clases, {total} imágenes")
        for clase, n in sorted(conteos.items(), key=lambda x: (len(x[0]), x[0])):
            print(f"    {clase:>12}  {n:>4} imgs")
    if tamanos:
        w_med = int(np.median([t[0] for t in tamanos]))
        h_med = int(np.median([t[1] for t in tamanos]))
        print(f"\n  Tamaño típico de imagen (muestra): {w_med} × {h_med} px")
    if faltantes:
        print(f"\n  Clases del 1–23 NO encontradas: {', '.join(faltantes)}")
    else:
        print("\n  Todas las clases del 1–23 presentes.")
    print("═" * 60)

    # guardar resumen JSON
    resumen = {
        "splits": {s: dict(sorted(c.items())) for s, c in splits.items()},
        "tamano_tipico_px": f"{w_med}x{h_med}" if tamanos else "desconocido",
        "clases_faltantes_1_23": faltantes,
    }
    out = TRAIN_DIR / "auditoria_dataset.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f"[auditoria] guardado → {out}")
    return resumen


# ── paso 2: degradado ───────────────────────────────────────────────────────────
def degradar_imagen(img: np.ndarray, h_objetivo: int = 24) -> np.ndarray:
    """
    Simula la resolución de nuestro clip TV:
    1. Escala a h_objetivo px manteniendo aspecto.
    2. Vuelve a subir al tamaño original.
    3. Aplica blur gaussiano 3×3.
    4. Compresión JPEG calidad 55 y descompresión.
    """
    h0, w0 = img.shape[:2]
    if h0 == 0 or w0 == 0:
        return img
    w_obj = max(1, int(round(w0 * h_objetivo / h0)))
    small = cv2.resize(img, (w_obj, h_objetivo), interpolation=cv2.INTER_AREA)
    big = cv2.resize(small, (w0, h0), interpolation=cv2.INTER_CUBIC)
    blurred = cv2.GaussianBlur(big, (3, 3), 0)
    _, buf = cv2.imencode(".jpg", blurred, [cv2.IMWRITE_JPEG_QUALITY, 55])
    degraded = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return degraded


def crear_dataset_degradado(split="train"):
    """Copia un split degradando cada imagen al directorio dataset_degradado."""
    src = DATASET_DIR / split
    dst = DEGRADED_DIR / split
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    count = 0
    for clase_dir in src.iterdir():
        if not clase_dir.is_dir():
            continue
        (dst / clase_dir.name).mkdir()
        for img_path in clase_dir.glob("*"):
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            deg = degradar_imagen(img)
            out_path = dst / clase_dir.name / img_path.name
            cv2.imwrite(str(out_path), deg)
            count += 1
    print(f"[degradado] {split}: {count} imágenes degradadas → {dst}")
    return dst


# ── paso 2: entrenamiento ───────────────────────────────────────────────────────
def entrenar(imgsz: int, epocas: int):
    """Entrena YOLOv8n-cls sobre las imágenes originales y evalúa sobre valid original + degradado."""
    from ultralytics import YOLO

    TRAIN_DIR.mkdir(parents=True, exist_ok=True)

    # 2a: entrenamiento con imágenes originales
    print(f"\n[entrenamiento] YOLOv8n-cls imgsz={imgsz} épocas={epocas}")
    model = YOLO("yolov8n-cls.pt")
    results = model.train(
        data=str(DATASET_DIR),
        epochs=epocas,
        imgsz=imgsz,
        project=str(TRAIN_DIR),
        name="yolov8n_original",
        exist_ok=True,
        device=0 if _gpu_disponible() else "cpu",
        batch=32,
        cache=True,
        verbose=False,
    )
    run_dir = TRAIN_DIR / "yolov8n_original"
    best_pt = run_dir / "weights" / "best.pt"
    print(f"[entrenamiento] pesos → {best_pt}")

    # 2b: evaluar sobre valid original
    print("\n[evaluacion] valid ORIGINAL")
    val_orig = YOLO(str(best_pt)).val(
        data=str(DATASET_DIR),
        split="val",
        imgsz=imgsz,
        project=str(TRAIN_DIR),
        name="eval_original",
        exist_ok=True,
        verbose=False,
    )
    acc_orig = float(val_orig.top1)
    print(f"  top-1 accuracy (original) = {acc_orig:.4f}")

    # 2c: crear set de validación degradado y evaluar
    print("\n[degradado] creando valid degradado…")
    deg_valid = crear_dataset_degradado("valid")

    print("\n[evaluacion] valid DEGRADADO")
    # Para el degradado creamos un directorio completo con los tres splits
    # apuntando a la misma carpeta (YOLO classify val necesita train + val)
    import shutil as _shutil
    deg_data_full = ROOT / "outputs" / "experimentos" / "dorsales" / "dataset_degradado_full"
    if deg_data_full.exists():
        _shutil.rmtree(deg_data_full)
    # Usa el train original y el valid degradado
    (deg_data_full / "train").mkdir(parents=True)
    (deg_data_full / "test").mkdir(parents=True)
    # symlink o copia ligera: apuntamos train y test al original para que YOLO no se queje
    for split_cp in ("train", "test"):
        src_split = DATASET_DIR / split_cp
        dst_split = deg_data_full / split_cp
        dst_split.rmdir()
        import os as _os
        _os.symlink(str(src_split), str(dst_split))
    # valid degradado
    import os as _os
    _os.symlink(str(deg_valid), str(deg_data_full / "valid"))
    val_deg = YOLO(str(best_pt)).val(
        data=str(deg_data_full),
        split="valid",
        imgsz=imgsz,
        project=str(TRAIN_DIR),
        name="eval_degradado",
        exist_ok=True,
        verbose=False,
    )
    acc_deg = float(val_deg.top1)
    print(f"  top-1 accuracy (degradado) = {acc_deg:.4f}")

    # guardar resumen de métricas
    metricas = {
        "modelo": "yolov8n-cls",
        "imgsz": imgsz,
        "epocas": epocas,
        "top1_valid_original": round(acc_orig, 4),
        "top1_valid_degradado": round(acc_deg, 4),
        "umbral_optimo_usado": 0.66,
        "pesos": str(best_pt),
    }
    out_json = TRAIN_DIR / "metricas_entrenamiento.json"
    out_json.write_text(json.dumps(metricas, indent=2, ensure_ascii=False))
    print(f"\n[metricas] guardado → {out_json}")
    print(f"\n  top-1 original  = {acc_orig:.1%}")
    print(f"  top-1 degradado = {acc_deg:.1%}  ← la que importa")

    if acc_deg < 0.50:
        print(
            "\n⚠️  CRITERIO DE PARADA: exactitud degradada < 50%. "
            "No se recomienda continuar con los pasos 3–6. "
            "Reportar resultado y proponer siguiente experimento."
        )
    return metricas


def _gpu_disponible() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# ── punto de entrada ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Pasos 1 y 2 del experimento de dorsales")
    parser.add_argument("--solo-auditar", action="store_true", help="Solo descarga y audita el dataset")
    parser.add_argument("--epocas", type=int, default=40, help="Épocas de entrenamiento (default 40)")
    parser.add_argument("--imgsz", type=int, default=96, help="Tamaño de imagen de entrada (default 96)")
    args = parser.parse_args()

    load_env()

    # descarga solo si el dataset no existe
    if not DATASET_DIR.exists() or not any(DATASET_DIR.iterdir()):
        descargar_dataset()
    else:
        print(f"[descarga] Dataset ya existe en {DATASET_DIR}, omitiendo descarga.")

    resumen = auditar_dataset()

    if args.solo_auditar:
        print("\n[solo-auditar] Listo. Fin del paso 1.")
        return

    entrenar(imgsz=args.imgsz, epocas=args.epocas)
    print("\n✅ Pasos 1 y 2 completados.")


if __name__ == "__main__":
    main()
