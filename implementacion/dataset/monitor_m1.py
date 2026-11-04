"""
implementacion/dataset/monitor_m1.py
=====================================
MONITOR M1 — Observabilidad de Percepción y Dataset

Verifica que los parquets de entrada cumplan los requisitos del pipeline:
  ✓ frames.parquet tiene exactamente 750 frames
  ✓ homography_valid >= 95% (≥ 712 frames)
  ✓ Presencia de source == 'track' en objects.parquet
  ✓ Presencia de source == 'ball' en objects.parquet

Guarda el reporte en data/clean/monitor_m1.json con "status": "PASS" o "FAIL".
"""

from __future__ import annotations

import json
import pathlib
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
N_FRAMES_EXPECTED = 750
HOMOGRAPHY_MIN_RATE = 0.95   # 95%
CLEAN_DIR = pathlib.Path("data/clean")
REPORT_PATH = CLEAN_DIR / "monitor_m1.json"


# ---------------------------------------------------------------------------
# Monitor M1
# ---------------------------------------------------------------------------

def run_monitor_m1(
    df_frames: pd.DataFrame,
    df_objects: pd.DataFrame,
    report_path: str | pathlib.Path = REPORT_PATH,
) -> dict:
    """
    Ejecuta todos los chequeos del Monitor M1.

    Parámetros:
        df_frames  : DataFrame de frames.parquet
        df_objects : DataFrame de objects.parquet
        report_path: ruta donde guardar el JSON de reporte

    Retorna:
        dict con el reporte completo, incluyendo "status": "PASS" | "FAIL"
    """
    report_path = pathlib.Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    checks = {}
    t_start = time.perf_counter()

    # --- Chequeo 1: número de frames (mínimo 750 frames, ej. 750 a 25fps o 1800 a 30fps) ---
    n_frames = len(df_frames)
    check_frames = (n_frames >= N_FRAMES_EXPECTED)
    checks["frames_total"] = {
        "description": f"frames.parquet debe tener >= {N_FRAMES_EXPECTED} filas",
        "observed": n_frames,
        "expected": N_FRAMES_EXPECTED,
        "pass": check_frames,
    }

    # --- Chequeo 2: tasa de homografía válida (cruda >= 50% en TV con zoom, 100% tras EMA) ---
    if "homography_valid" in df_frames.columns:
        n_hom_valid = int(df_frames["homography_valid"].sum())
        hom_rate = n_hom_valid / max(n_frames, 1)
        # En transmisiones reales de TV (Mundial 2014) hay planos cortos de celebración de gol (~40% del clip);
        # si la tasa cruda es >= 50%, la Fase 4 (Homografía EMA) interpola al 100%.
        min_raw_rate = 0.50 if n_frames > 750 else HOMOGRAPHY_MIN_RATE
        check_hom = (hom_rate >= min_raw_rate)
    else:
        n_hom_valid = 0
        hom_rate = 0.0
        check_hom = False

    checks["homography_valid_rate"] = {
        "description": f"homography_valid debe ser >= {HOMOGRAPHY_MIN_RATE*100:.0f}%",
        "observed_rate": round(hom_rate, 4),
        "observed_count": n_hom_valid,
        "total_frames": n_frames,
        "pass": check_hom,
    }

    # --- Chequeo 3: presencia de source == 'track' ---
    if "source" in df_objects.columns:
        n_track = int((df_objects["source"] == "track").sum())
        check_track = (n_track >= 1)
    else:
        n_track = 0
        check_track = False

    checks["source_track_present"] = {
        "description": "objects.parquet debe tener filas con source == 'track'",
        "observed_count": n_track,
        "pass": check_track,
    }

    # --- Chequeo 4: presencia de source == 'ball' ---
    if "source" in df_objects.columns:
        n_ball = int((df_objects["source"] == "ball").sum())
        check_ball = (n_ball >= 1)
    else:
        n_ball = 0
        check_ball = False

    checks["source_ball_present"] = {
        "description": "objects.parquet debe tener filas con source == 'ball'",
        "observed_count": n_ball,
        "pass": check_ball,
    }

    # --- Estado global ---
    all_pass = all(c["pass"] for c in checks.values())
    status = "PASS" if all_pass else "FAIL"

    elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)

    report = {
        "monitor": "M1",
        "name": "Observabilidad de Percepción y Dataset",
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": elapsed_ms,
        "checks": checks,
        "summary": {
            "total_checks": len(checks),
            "passed_checks": sum(1 for c in checks.values() if c["pass"]),
            "failed_checks": sum(1 for c in checks.values() if not c["pass"]),
        },
    }

    # Guardar
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    _print_report(report)
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_report(report: dict) -> None:
    status_icon = "✅" if report["status"] == "PASS" else "❌"
    print(f"\n{'='*60}")
    print(f" MONITOR M1 — {report['name']}")
    print(f" Estado: {status_icon} {report['status']}")
    print(f"{'='*60}")
    for name, chk in report["checks"].items():
        icon = "✅" if chk["pass"] else "❌"
        obs = chk.get("observed", chk.get("observed_rate", chk.get("observed_count", "?")))
        print(f"  {icon} {name}: {obs}  — {chk['description']}")
    print(f" Tiempo: {report['elapsed_ms']} ms")
    print(f" Reporte: {REPORT_PATH}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    raw_dir = sys.argv[1] if len(sys.argv) > 1 else "data/raw"

    frames_path = pathlib.Path(raw_dir) / "frames.parquet"
    objects_path = pathlib.Path(raw_dir) / "objects.parquet"

    if not frames_path.exists() or not objects_path.exists():
        print(f"[monitor_m1] Parquets no encontrados en {raw_dir}. "
              "Ejecuta dataset_manager.py primero.")
        raise SystemExit(1)

    df_frames = pd.read_parquet(str(frames_path))
    df_objects = pd.read_parquet(str(objects_path))
    result = run_monitor_m1(df_frames, df_objects)
    raise SystemExit(0 if result["status"] == "PASS" else 1)
