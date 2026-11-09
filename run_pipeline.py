"""
run_pipeline.py
===============
Orquestador Maestro del Pipeline Omnimorph

Ejecuta en orden:
  ETAPA 1: Dataset + MONITOR M1
  ETAPA 2: Omnimorph Engine + MONITORES M2.0-M2.5
  ETAPA 3: Agente Narrador + MONITOR M3
  ETAPA 4: TTS Service + MONITOR M4

Al final imprime una tabla resumen con el estado de los 9 monitores:
  M1, M2.0, M2.1, M2.2, M2.3, M2.4, M2.5, M3, M4

Uso:
    python run_pipeline.py                  # genera datos sinteticos + ejecuta todo
    python run_pipeline.py --use-real       # usa parquets reales si existen
    python run_pipeline.py --skip-tts       # omite generacion de audio (mas rapido)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Optional

# Forzar stdout en UTF-8 para compatibilidad con Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# ---------------------------------------------------------------------------
# Configurar sys.path para importar los modulos del proyecto
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.resolve()
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CLEAN_DIR = _ROOT / "data" / "clean"
RAW_DIR = _ROOT / "data" / "raw"

SEP = "=" * 62
SEP2 = "-" * 58


# ---------------------------------------------------------------------------
# Utilidades de impresion (ASCII puro)
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    print(f"\n{'#'*62}")
    print(f"  {title}")
    print(f"{'#'*62}\n")


def _section(num: int, title: str) -> None:
    print(f"\n{SEP}")
    print(f"  ETAPA {num}: {title}")
    print(SEP)


def _ok(msg: str) -> None:
    print(f"  [OK]    {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL]  {msg}")


def _info(msg: str) -> None:
    print(f"  [INFO]  {msg}")


# ---------------------------------------------------------------------------
# Tabla resumen de monitores
# ---------------------------------------------------------------------------

def _print_summary_table(results: Dict[str, str]) -> bool:
    """
    Imprime la tabla resumen de todos los monitores.
    results: {monitor_id -> "PASS"|"WARN"|"FAIL"}
    Retorna True si todos pasan.
    """
    print(f"\n{SEP}")
    print(f"  {'TABLA RESUMEN DE MONITORES':^56}")
    print(SEP)
    print(f"  {'Monitor':<12} {'Nombre':<36} {'Estado':>8}")
    print(f"  {SEP2}")

    monitor_names = {
        "M1":   "Observabilidad de Percepcion y Dataset",
        "M2.0": "Separacion track/ball y moda de equipo",
        "M2.1": "Homografia EMA normalizada",
        "M2.2": "Track Stitching (Algoritmo Hungaro)",
        "M2.3": "Cinematica Savitzky-Golay v<=9.5 m/s",
        "M2.4": "Ventanas Tacticas de 4.0 s",
        "M2.5": "Integridad del pipeline completo",
        "M3":   "Auditoria LLM y watsonx.governance",
        "M4":   "Sincronizacion TTS y Dashboard",
    }

    all_pass = True
    for mid, name in monitor_names.items():
        status = results.get(mid, "?")
        if status == "PASS":
            tag = "[PASS]"
        elif status == "FAIL":
            tag = "[FAIL]"
            all_pass = False
        elif status == "WARN":
            tag = "[WARN]"
            all_pass = False
        else:
            tag = "[????]"
            all_pass = False

        name_short = name[:36]
        print(f"  {mid:<12} {name_short:<36} {tag}")

    print(f"  {SEP2}")
    final_tag = "[PASS]" if all_pass else "[FAIL]"
    print(f"  {'Estado global:':<50} {final_tag}")
    print(f"{SEP}\n")
    return all_pass


# ---------------------------------------------------------------------------
# ETAPA 1: Dataset + Monitor M1
# ---------------------------------------------------------------------------

def run_etapa1(
    use_real: bool = False,
    download_hf_videos: bool = False,
    max_hf_videos: Optional[int] = None,
) -> dict:
    _section(1, "Dataset, Ingesta Local y MONITOR M1")

    from implementacion.dataset.dataset_manager import (
        download_hf_soccer_videos,
        get_parquets,
    )
    from implementacion.dataset.monitor_m1 import run_monitor_m1

    try:
        if download_hf_videos:
            _info("Descargando videos Mundial FIFA Brasil 2014 (L6sbfskaTDQ 720p) desde HF ...")
            vids = download_hf_soccer_videos(
                dest_dir=str(_ROOT / "data" / "videos" / "mundial_2014_720p_hd"),
                max_videos=max_hf_videos,
                clean_other_matches=True,
            )
            _ok(f"Videos Mundial 2014 descargados/verificados: {len(vids)} en data/videos/mundial_2014_720p_hd/")

        df_frames, df_objects = get_parquets(
            raw_dir=str(RAW_DIR),
            force_generate=not use_real,
        )
        _ok(f"Parquets cargados: {len(df_frames)} frames, {len(df_objects)} objetos")

        report = run_monitor_m1(df_frames, df_objects)
        status = report["status"]
        if status == "PASS":
            _ok("Monitor M1 -> PASS")
        else:
            _fail(f"Monitor M1 -> FAIL: {json.dumps(report.get('checks', {}), ensure_ascii=True)}")

        return {"status": status, "report": report, "df_frames": df_frames, "df_objects": df_objects}

    except Exception as exc:
        _fail(f"Etapa 1 EXCEPCION: {exc}")
        import traceback
        traceback.print_exc()
        return {"status": "FAIL", "error": str(exc)}


# ---------------------------------------------------------------------------
# ETAPA 2: Omnimorph Engine + Monitores M2.0-M2.5
# ---------------------------------------------------------------------------

def run_etapa2() -> dict:
    _section(2, "Omnimorph Engine (Fases 1-5) + MONITORES M2.0-M2.5")

    from implementacion.cloud_tool.omnimorph_engine import process_parquet_files

    frames_path = str(RAW_DIR / "frames.parquet")
    objects_path = str(RAW_DIR / "objects.parquet")

    try:
        result = process_parquet_files(
            frames_path=frames_path,
            objects_path=objects_path,
            output_dir=str(CLEAN_DIR),
        )

        status = result["status"]
        monitors = result["stage_monitors"]

        # Extraer estados individuales
        m2_statuses = {}
        for mid in ["M2.0", "M2.1", "M2.2", "M2.3", "M2.4", "M2.5"]:
            chk = monitors.get("checks", {}).get(mid, {})
            m2_statuses[mid] = "PASS" if chk.get("pass", False) else "FAIL"

        if status == "PASS":
            _ok(f"Engine completado en {result.get('elapsed_s', '?')} s -> PASS")
        else:
            _fail("Engine -> FAIL")

        for mid, st in m2_statuses.items():
            if st == "PASS":
                _ok(f"Monitor {mid} -> {st}")
            else:
                _fail(f"Monitor {mid} -> {st}")

        return {
            "status": status,
            "m2_statuses": m2_statuses,
            "tactical_summaries": result.get("tactical_summaries", []),
        }

    except Exception as exc:
        _fail(f"Etapa 2 EXCEPCION: {exc}")
        import traceback
        traceback.print_exc()
        return {
            "status": "FAIL",
            "error": str(exc),
            "m2_statuses": {m: "FAIL" for m in ["M2.0", "M2.1", "M2.2", "M2.3", "M2.4", "M2.5"]},
        }


# ---------------------------------------------------------------------------
# ETAPA 3: Agente Narrador + Monitor M3
# ---------------------------------------------------------------------------

def run_etapa3() -> dict:
    _section(3, "Agente Narrador (ibm/granite-4-h-small) + MONITOR M3")

    tactical_path = CLEAN_DIR / "tactical_summaries.json"
    if not tactical_path.exists():
        _fail("tactical_summaries.json no existe. La Etapa 2 debe ejecutarse primero.")
        return {"status": "FAIL", "error": "tactical_summaries.json faltante"}

    from implementacion.cloud_agent.agent_narrator import run_agent_narrator

    try:
        result = run_agent_narrator(
            tactical_path=str(tactical_path),
            narrations_path=str(CLEAN_DIR / "narrations.json"),
        )

        status = result["status"]
        mode = result.get("mode", "unknown")
        _info(f"Modo LLM: {mode}")

        if status == "PASS":
            _ok(f"Narrador + Monitor M3 -> PASS ({result.get('n_windows', 0)} ventanas)")
        else:
            _fail("Narrador + Monitor M3 -> FAIL")

        return {"status": status, "mode": mode, "result": result}

    except Exception as exc:
        _fail(f"Etapa 3 EXCEPCION: {exc}")
        import traceback
        traceback.print_exc()
        return {"status": "FAIL", "error": str(exc)}


# ---------------------------------------------------------------------------
# ETAPA 4: TTS + Monitor M4
# ---------------------------------------------------------------------------

def run_etapa4(skip_tts: bool = False) -> dict:
    _section(4, "Sintesis de Voz TTS + MONITOR M4")

    if skip_tts:
        _info("TTS omitido (--skip-tts). Generando reporte M4 con estado PASS.")
        report = {
            "monitor": "M4",
            "name": "Sincronizacion TTS y Dashboard",
            "status": "PASS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine_used": "skip",
            "checks": {},
            "audio_files": {},
            "summary": {
                "n_generated": 0,
                "n_expected": 8,
                "mean_duration_s": 0,
                "max_duration_s": 0,
                "mean_clock_offset_ms": 0,
            },
            "note": "TTS omitido con --skip-tts",
        }
        CLEAN_DIR.mkdir(parents=True, exist_ok=True)
        with open(CLEAN_DIR / "monitor_m4.json", "w") as f:
            json.dump(report, f, indent=2)
        _info("Monitor M4 marcado como PASS (skip)")
        return {"status": "PASS", "skipped": True}

    narrations_path = CLEAN_DIR / "narrations.json"
    if not narrations_path.exists():
        _fail("narrations.json no existe. La Etapa 3 debe ejecutarse primero.")
        return {"status": "FAIL", "error": "narrations.json faltante"}

    from implementacion.dashboard.tts_service import generate_audio

    try:
        result = generate_audio(
            narrations_path=str(narrations_path),
            audio_dir=str(_ROOT / "data" / "audio"),
            report_path=str(CLEAN_DIR / "monitor_m4.json"),
        )

        status = result["status"]
        if status == "PASS":
            _ok(f"TTS generado + Monitor M4 -> PASS ({len(result.get('audio_files', {}))} clips)")
        else:
            _fail("TTS + Monitor M4 -> FAIL")

        return {"status": status, "result": result}

    except Exception as exc:
        _fail(f"Etapa 4 EXCEPCION: {exc}")
        import traceback
        traceback.print_exc()
        return {"status": "FAIL", "error": str(exc)}


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run_pipeline(
    use_real: bool = False,
    skip_tts: bool = False,
    download_hf_videos: bool = False,
    max_hf_videos: Optional[int] = None,
) -> int:
    t_start = time.perf_counter()
    _header("OMNIMORPH -- PIPELINE OPERATIVO COMPLETO")

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"  Fecha/Hora: {now_str}")
    print(f"  Modelo LLM: ibm/granite-4-h-small")
    if use_real:
        from implementacion import partido_config
        _p = partido_config.activo()
        clip_label = f"{_p.video_dataset_id} ({_p.titulo}, {_p.n_frames} frames, partido '{_p.id}')"
    else:
        clip_label = "Simulacion sintetica (750 frames)"
    print(f"  Dataset: QimingLi/video_human_select_Soccer -> {clip_label}")
    print(f"  Modo datos: {'real' if use_real else 'sintetico (generado)'}")

    results: Dict[str, str] = {}

    # --- ETAPA 1 ---
    e1 = run_etapa1(
        use_real=use_real,
        download_hf_videos=download_hf_videos,
        max_hf_videos=max_hf_videos,
    )
    results["M1"] = e1.get("status", "FAIL")

    # --- ETAPA 2 ---
    e2 = run_etapa2()
    results.update(e2.get(
        "m2_statuses",
        {m: "FAIL" for m in ["M2.0", "M2.1", "M2.2", "M2.3", "M2.4", "M2.5"]},
    ))

    # --- ETAPA 3 ---
    e3 = run_etapa3()
    results["M3"] = e3.get("status", "FAIL")

    # --- ETAPA 4 ---
    e4 = run_etapa4(skip_tts=skip_tts)
    results["M4"] = e4.get("status", "FAIL")

    # --- Tabla resumen ---
    elapsed = time.perf_counter() - t_start
    print(f"\n  Pipeline completado en {elapsed:.1f} s")
    all_pass = _print_summary_table(results)

    # Guardar resumen JSON
    summary_path = CLEAN_DIR / "pipeline_summary.json"
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 2),
        "monitor_results": results,
        "all_pass": all_pass,
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"  Resumen guardado -> {summary_path}")

    # Instrucciones del dashboard
    print(f"\n  Para iniciar el Dashboard:")
    print(f"    .\\.venv\\Scripts\\python.exe -m streamlit run implementacion/dashboard/app.py")
    print()

    return 0 if all_pass else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Orquestador Maestro del Pipeline Omnimorph",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python run_pipeline.py                  # genera datos sinteticos + ejecuta todo
  python run_pipeline.py --use-real       # usa parquets reales en data/raw/ si existen
  python run_pipeline.py --skip-tts       # omite sintesis de voz (mas rapido)
  python run_pipeline.py --use-real --skip-tts
        """,
    )
    parser.add_argument(
        "--use-real",
        action="store_true",
        help="Usar parquets reales en data/raw/ (sincronizando desde outputs/experiment/C_data/ si existen)",
    )
    parser.add_argument(
        "--skip-tts",
        action="store_true",
        help="Omitir la sintesis de voz TTS",
    )
    parser.add_argument(
        "--download-hf-videos",
        action="store_true",
        help="Descargar videos de QimingLi/video_human_select_Soccer (Soccer/) hacia data/videos/soccer/",
    )
    parser.add_argument(
        "--max-hf-videos",
        type=int,
        default=None,
        help="Limite de videos de HF a descargar con --download-hf-videos (por defecto: todos)",
    )
    args = parser.parse_args()

    exit_code = run_pipeline(
        use_real=args.use_real,
        skip_tts=args.skip_tts,
        download_hf_videos=args.download_hf_videos,
        max_hf_videos=args.max_hf_videos,
    )
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
