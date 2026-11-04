"""
implementacion/cloud_tool/api_server.py
========================================
FastAPI wrapper del Omnimorph Engine para importacion en IBM watsonx Orchestrate.

Expone el endpoint POST /process que recibe rutas a los parquet y devuelve
el resultado completo del pipeline (ventanas tácticas + monitores M2.0–M2.5).

Inicio rápido (local):
    .\.venv\Scripts\python.exe -m uvicorn implementacion.cloud_tool.api_server:app --reload --port 8000

Con ngrok (tunnel público para Orchestrate):
    .\.venv\Scripts\python.exe implementacion/cloud_tool/launch_ngrok.py

Reglas IBM:
  - Cero API keys en código — usa .env para cualquier credencial.
  - Sin .mp4 en Git.
"""

from __future__ import annotations

import io
import os
import pathlib
import sys
import time
from typing import Optional

# Forzar UTF-8 en stdout/stderr para evitar errores de codificacion en Windows
# cuando el engine imprime caracteres Unicode (flechas, emojis, etc.)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Asegurar que el raíz del proyecto esté en sys.path
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.cloud_tool.omnimorph_engine import process_parquet_files

# ---------------------------------------------------------------------------
# App FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Omnimorph Engine Tool",
    description=(
        "Herramienta de procesamiento de telemetría de fútbol para importación "
        "en IBM watsonx Orchestrate. Ejecuta el pipeline Omnimorph (Fases 1–5) "
        "sobre archivos parquet y devuelve ventanas tácticas + estado de monitores."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS — permite que Orchestrate (dominio externo) llame al servidor
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------

class ProcessRequest(BaseModel):
    frames_path: str = Field(
        default="data/raw/frames.parquet",
        description="Ruta al archivo frames.parquet (relativa a la raíz del proyecto)",
        example="data/raw/frames.parquet",
    )
    objects_path: str = Field(
        default="data/raw/objects.parquet",
        description="Ruta al archivo objects.parquet",
        example="data/raw/objects.parquet",
    )
    output_dir: str = Field(
        default="data/clean",
        description="Directorio de salida para artefactos limpios",
        example="data/clean",
    )


class ProcessResponse(BaseModel):
    status: str
    elapsed_s: float
    output_files: dict
    stage_monitors: dict
    tactical_summaries: list


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", summary="Health check")
def root():
    """Verificación de disponibilidad del servidor."""
    return {"status": "ok", "service": "Omnimorph Engine Tool", "version": "1.0.0"}


@app.get("/health", summary="Health check detallado")
def health():
    """Estado detallado del servidor."""
    frames_exists = pathlib.Path("data/raw/frames.parquet").exists()
    objects_exists = pathlib.Path("data/raw/objects.parquet").exists()
    return {
        "status": "ok",
        "data_ready": frames_exists and objects_exists,
        "frames_parquet": frames_exists,
        "objects_parquet": objects_exists,
    }


@app.post(
    "/process",
    response_model=ProcessResponse,
    summary="Procesar archivos parquet con el pipeline Omnimorph",
    operation_id="process_parquet_tool",
    tags=["Omnimorph Engine"],
)
def process(request: ProcessRequest):
    """
    Recibe las rutas a frames.parquet y objects.parquet, ejecuta las 5 fases
    del Omnimorph Engine y devuelve ventanas tácticas + estado de monitores M2.0–M2.5.

    Si los archivos no existen, genera telemetría sintética de respaldo automáticamente.
    """
    t_start = time.perf_counter()

    # Resolver rutas relativas a la raíz del proyecto
    frames_path = str(_ROOT / request.frames_path) if not pathlib.Path(request.frames_path).is_absolute() else request.frames_path
    objects_path = str(_ROOT / request.objects_path) if not pathlib.Path(request.objects_path).is_absolute() else request.objects_path
    output_dir = str(_ROOT / request.output_dir) if not pathlib.Path(request.output_dir).is_absolute() else request.output_dir

    try:
        # Capturar stdout del engine en un buffer UTF-8 para evitar
        # errores de codificacion en consolas Windows cp1252
        import io as _io
        old_stdout = sys.stdout
        sys.stdout = _io.TextIOWrapper(
            _io.BytesIO(), encoding="utf-8", errors="replace"
        )
        try:
            result = process_parquet_files(
                frames_path=frames_path,
                objects_path=objects_path,
                output_dir=output_dir,
            )
        finally:
            sys.stdout = old_stdout
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error en el pipeline: {exc}") from exc

    if result.get("status") == "FAIL":
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline FAIL",
                "stage_monitors": result.get("stage_monitors", {}),
            },
        )

    return ProcessResponse(
        status=result["status"],
        elapsed_s=round(time.perf_counter() - t_start, 3),
        output_files=result.get("output_files", {}),
        stage_monitors=result.get("stage_monitors", {}),
        tactical_summaries=result.get("tactical_summaries", []),
    )


# ---------------------------------------------------------------------------
# Punto de entrada directo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "implementacion.cloud_tool.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        app_dir=str(_ROOT),
    )
