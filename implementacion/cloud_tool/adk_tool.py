"""
implementacion/cloud_tool/adk_tool.py
=======================================
Empaqueta process_parquet_files con el decorador @tool de
IBM watsonx Orchestrate ADK (ibm_watsonx_orchestrate.agent_builder.tools).

Si el paquete ADK no está disponible en el entorno, proporciona un
decorador @tool de fallback transparente para ejecución local.

Uso:
    from implementacion.cloud_tool.adk_tool import process_parquet_tool
    result = process_parquet_tool(
        frames_path="data/raw/frames.parquet",
        objects_path="data/raw/objects.parquet",
    )
"""

from __future__ import annotations

import os
import sys
import pathlib

# ---------------------------------------------------------------------------
# Importar el decorador @tool del ADK de IBM watsonx Orchestrate
# con fallback limpio para entornos locales sin el SDK
# ---------------------------------------------------------------------------

try:
    from ibm_watsonx_orchestrate.agent_builder.tools import tool as adk_tool
    _ADK_AVAILABLE = True
    print("[adk_tool] IBM watsonx Orchestrate ADK cargado correctamente.")
except ImportError:
    _ADK_AVAILABLE = False

    def adk_tool(func=None, **kwargs):
        """Fallback @tool para entornos sin el SDK de IBM watsonx Orchestrate."""
        if func is None:
            # Llamada como @tool(name=...) — retorna decorador
            def decorator(f):
                f._adk_fallback = True
                f._adk_tool_name = kwargs.get("name", f.__name__)
                f._adk_tool_description = kwargs.get("description", f.__doc__ or "")
                return f
            return decorator
        # Llamada directa como @tool
        func._adk_fallback = True
        func._adk_tool_name = func.__name__
        func._adk_tool_description = func.__doc__ or ""
        return func

    print("[adk_tool] ADK no disponible — usando fallback local (@tool sin efecto).")


# ---------------------------------------------------------------------------
# Importar el engine
# ---------------------------------------------------------------------------

# Asegurar que el módulo sea importable desde cualquier directorio de trabajo
_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.cloud_tool.omnimorph_engine import process_parquet_files


# ---------------------------------------------------------------------------
# Herramienta ADK
# ---------------------------------------------------------------------------

@adk_tool(
    name="process_omnimorph_parquets",
    description=(
        "Procesa los archivos frames.parquet y objects.parquet de un clip de fútbol "
        "mediante el pipeline Omnimorph (Fases 1–5): separación de tracks, homografía EMA, "
        "track stitching, cinemática Savitzky-Golay y ventanas tácticas de 4.0 s. "
        "Genera objects_cleaned.parquet y tactical_summaries.json en el directorio de salida. "
        "Ejecuta los Monitores M2.0–M2.5 y devuelve su estado."
    ),
)
def process_parquet_tool(
    frames_path: str = "data/raw/frames.parquet",
    objects_path: str = "data/raw/objects.parquet",
    output_dir: str = "data/clean",
) -> dict:
    """
    Herramienta ADK — Omnimorph Engine.

    Parámetros:
        frames_path  : Ruta al archivo frames.parquet de entrada.
        objects_path : Ruta al archivo objects.parquet de entrada.
        output_dir   : Directorio donde se guardarán los artefactos de salida.

    Retorna:
        dict con:
          - status           : "PASS" | "FAIL"
          - stage_monitors   : resultados de monitores M2.0–M2.5
          - output_files     : rutas de los archivos generados
          - tactical_summaries: lista de 8 ventanas tácticas
          - elapsed_s        : tiempo de ejecución en segundos
    """
    return process_parquet_files(
        frames_path=frames_path,
        objects_path=objects_path,
        output_dir=output_dir,
    )


# ---------------------------------------------------------------------------
# CLI de prueba
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys as _sys
    fp = _sys.argv[1] if len(_sys.argv) > 1 else "data/raw/frames.parquet"
    op = _sys.argv[2] if len(_sys.argv) > 2 else "data/raw/objects.parquet"

    print(f"[adk_tool] ADK disponible: {_ADK_AVAILABLE}")
    result = process_parquet_tool(frames_path=fp, objects_path=op)
    print(f"\n[adk_tool] Estado: {result['status']}")

    if result["status"] == "PASS":
        print("[adk_tool] Todos los monitores M2.x → PASS ✅")
    else:
        print("[adk_tool] Hay monitores FAIL ❌")

    raise SystemExit(0 if result["status"] == "PASS" else 1)
