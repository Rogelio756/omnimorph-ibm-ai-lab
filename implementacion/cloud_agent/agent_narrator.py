"""
implementacion/cloud_agent/agent_narrator.py
=============================================
Agente Táctico y Narrador — ibm/granite-4-h-small

Lee las 8 ventanas de data/clean/tactical_summaries.json,
invoca ibm/granite-4-h-small (temperature=0.3, max_tokens=220),
audita cada respuesta con el Monitor M3 y guarda data/clean/narrations.json.

Credenciales exclusivamente desde .env:
  IBM_CLOUD_API_KEY, WATSONX_URL, WATSONX_PROJECT_ID

Si no hay credenciales (.env no configurado), ejecuta modo OFFLINE determinista
basado en los datos reales de cada ventana.

Regla IBM: NUNCA escribir API keys en el código fuente.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Cargar variables de entorno desde .env (si existe)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv no instalado — se usan variables de entorno del sistema

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
REQUIRED_MODEL = "ibm/granite-4-h-small"
WATSONX_TEMPERATURE = 0.3
WATSONX_MAX_TOKENS = 220
CLEAN_DIR = pathlib.Path("data/clean")
TACTICAL_PATH = CLEAN_DIR / "tactical_summaries.json"
NARRATIONS_PATH = CLEAN_DIR / "narrations.json"

# Rutas para importar módulos del proyecto
_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.cloud_agent.governance_monitor_m3 import GovernanceMonitorM3
from implementacion import partido_config
from implementacion.cloud_agent.red_ipv4 import preferir_ipv4_en_ibm

preferir_ipv4_en_ibm()


# ---------------------------------------------------------------------------
# Configuración watsonx.ai
# ---------------------------------------------------------------------------

def _get_watsonx_credentials() -> Optional[dict]:
    """
    Lee credenciales exclusivamente desde el entorno.
    Usa WATSONX_SPACE_ID si está disponible (trial Orchestrate/AWS),
    si no usa WATSONX_PROJECT_ID (watsonx.ai Studio clásico).
    Devuelve None si no hay credenciales configuradas.
    """
    api_key  = os.environ.get("IBM_CLOUD_API_KEY", "").strip()
    url      = os.environ.get("WATSONX_URL", "").strip()
    space_id = os.environ.get("WATSONX_SPACE_ID", "").strip()
    proj_id  = os.environ.get("WATSONX_PROJECT_ID", "").strip()

    if not api_key or not url:
        return None
    if not space_id and not proj_id:
        return None

    return {
        "api_key":    api_key,
        "url":        url,
        "space_id":   space_id if space_id else None,
        "project_id": proj_id  if proj_id  else None,
    }


# ---------------------------------------------------------------------------
# Cliente watsonx.ai (IBM watsonx-ai SDK)
# ---------------------------------------------------------------------------

def _init_watsonx_model(creds: dict):
    """
    Inicializa ibm/granite-4-h-small con el SDK ibm-watsonx-ai.
    Usa space_id si está disponible (trial Orchestrate/AWS), si no project_id.
    Retorna el objeto model o None si el SDK no está disponible.
    """
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            url=creds["url"],
            api_key=creds["api_key"],
        )

        # Preferir space_id (trial Orchestrate) sobre project_id
        init_kwargs = dict(
            model_id=REQUIRED_MODEL,
            credentials=credentials,
            params={
                "temperature": WATSONX_TEMPERATURE,
                "max_new_tokens": WATSONX_MAX_TOKENS,  # granite-3-8b-instruct
                "max_tokens": WATSONX_MAX_TOKENS,       # granite-4-h-small (chat API)
            },
        )
        if creds.get("space_id"):
            init_kwargs["space_id"] = creds["space_id"]
            print(f"[agent_narrator] Usando space_id={creds['space_id'][:8]}...")
        else:
            init_kwargs["project_id"] = creds["project_id"]
            print(f"[agent_narrator] Usando project_id={creds['project_id'][:8]}...")

        model = ModelInference(**init_kwargs)
        return model
    except ImportError:
        print("[agent_narrator] ibm-watsonx-ai SDK no disponible — modo OFFLINE.")
        return None
    except Exception as exc:
        print(f"[agent_narrator] Error inicializando watsonx.ai: {exc} — modo OFFLINE.")
        return None


# ---------------------------------------------------------------------------
# Generador de prompts
# ---------------------------------------------------------------------------

def _build_prompt(window: dict) -> str:
    """
    Construye el prompt para ibm/granite-4-h-small dada una ventana táctica.
    El prompt pide un JSON con {window_id, t0, t1, analisis_tactico, narracion_es}.
    """
    dominant = window["dominant_team"]
    pressure = window["pressure_context"]
    block_h = window["block_height_m"]
    block_c = window["block_compactness_m"]
    t0 = window["t0"]
    t1 = window["t1"]
    wid = window["window_id"]

    # Descripción de dominio según el partido activo (data/partidos/<id>/partido.config.json)
    partido = partido_config.activo()
    eq0, eq1 = partido.equipos
    equipo_dom = partido.equipo_por_codigo(dominant)
    if equipo_dom is not None:
        rival = eq1 if equipo_dom.team_id == 0 else eq0
        team_label = f"{equipo_dom.nombre} ({equipo_dom.codigo})"
        dominio_texto = f"{equipo_dom.nombre} tiene su bloque en campo de {rival.nombre}."
    else:
        team_label = "Neutro (Disputa en mediocampo)"
        dominio_texto = "El juego está equilibrado en el mediocampo, sin dominio claro."

    prompt = f"""Eres un analista táctico de fútbol especializado en el partido {partido.titulo} ({partido.competicion}).

Se te proporcionan las métricas tácticas de la ventana {wid} (t={t0:.1f}s – {t1:.1f}s):
- Contexto de presión: {pressure}
- Equipo dominante: {team_label}
- {dominio_texto}
- Altura del bloque defensivo: {block_h:.2f} m
- Compacidad del bloque: {block_c:.2f} m

Genera un análisis táctico breve en español (2-3 oraciones técnicas mencionando a {eq0.nombre} o {eq1.nombre} según corresponda; usa solo las métricas dadas, sin inventar jugadores, goles, marcador ni velocidades) y una narración deportiva en español de MÁXIMO 30 PALABRAS pensada para comentario de audio en vivo de 4 segundos.

Responde EXCLUSIVAMENTE con un objeto JSON válido (sin texto antes ni después) con el siguiente esquema:
{{
  "window_id": "{wid}",
  "t0": {t0},
  "t1": {t1},
  "analisis_tactico": "...",
  "narracion_es": "..."
}}"""
    return prompt


# ---------------------------------------------------------------------------
# Invocación LLM (online)
# ---------------------------------------------------------------------------

def _call_watsonx(model, prompt: str) -> tuple[Optional[dict], float, int, int]:
    """
    Llama al modelo watsonx.ai via API de chat (messages).
    Compatible con ibm/granite-4-h-small y granite-3-8b-instruct.
    Devuelve (parsed_json, latency_ms, tokens_in, tokens_out).
    """
    import re
    t0 = time.perf_counter()
    try:
        # Usar chat API (messages) — funciona con modelos base e instruct
        messages = [
            {"role": "system", "content": (
                "Eres un analista tactico de futbol. "
                "Responde SOLO con un JSON valido, sin texto adicional, sin markdown, sin explicaciones."
            )},
            {"role": "user", "content": prompt},
        ]
        response = model.chat(messages=messages)
        latency_ms = (time.perf_counter() - t0) * 1000

        # Shape chat response: {"choices": [{"message": {"content": "..."}}], "usage": {...}}
        generated_text = ""
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                generated_text = choices[0].get("message", {}).get("content", "") or ""
            usage = response.get("usage", {})
            tokens_in  = usage.get("prompt_tokens",     len(prompt) // 4)
            tokens_out = usage.get("completion_tokens", len(generated_text) // 4)
        else:
            generated_text = str(response)
            tokens_in  = len(prompt) // 4
            tokens_out = len(generated_text) // 4

        # Parsear JSON de la respuesta
        json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
        parsed = json.loads(json_match.group()) if json_match else None

        return parsed, latency_ms, int(tokens_in), int(tokens_out)

    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"  [agent_narrator] Error llamando watsonx (chat): {exc}")
        # Fallback a generate_text si chat no esta soportado
        try:
            t1 = time.perf_counter()
            generated_text = model.generate_text(prompt=prompt) or ""
            latency_ms = (time.perf_counter() - t1) * 1000
            json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
            parsed = json.loads(json_match.group()) if json_match else None
            return parsed, latency_ms, len(prompt)//4, len(generated_text)//4
        except Exception as exc2:
            latency_ms2 = (time.perf_counter() - t0) * 1000
            print(f"  [agent_narrator] Fallback generate_text tambien fallo: {exc2}")
            return None, latency_ms2, 0, 0


# ---------------------------------------------------------------------------
# Modo OFFLINE determinista
# ---------------------------------------------------------------------------

def _generate_offline_narration(window: dict) -> tuple[dict, float, int, int]:
    """
    Genera narración determinista offline basada en los datos reales de la ventana.
    No usa LLM — para pruebas locales sin credenciales.
    """
    dominant = window["dominant_team"]
    pressure = window["pressure_context"]
    wid = window["window_id"]
    t0 = window["t0"]
    t1 = window["t1"]
    block_h = window["block_height_m"]

    # Análisis táctico basado en las métricas de la ventana y el partido activo
    partido = partido_config.activo()
    eq0, eq1 = partido.equipos
    equipo_dom = partido.equipo_por_codigo(dominant)
    if equipo_dom is not None:
        rival = eq1 if equipo_dom.team_id == 0 else eq0
        analisis = (
            f"{equipo_dom.nombre} adelanta sus líneas en campo de {rival.nombre} con un bloque de {block_h:.1f} m de amplitud. "
            f"Fase de {pressure} con el bloque en campo rival. "
            f"{rival.nombre} se repliega para cerrar los espacios por dentro."
        )
        narracion = (
            f"{equipo_dom.nombre} adelanta líneas buscando abrir espacios ante la defensa de {rival.nombre}."
        )
    else:
        analisis = (
            f"Disputa táctica equilibrada en el mediocampo ({block_h:.1f} m de dispersión vertical). "
            f"{eq0.nombre} y {eq1.nombre} se reparten el mediocampo sin un dominador claro. "
            f"Fase de transición neutral con presión recíproca."
        )
        narracion = (
            f"{eq0.nombre} y {eq1.nombre} disputan con intensidad el control del mediocampo."
        )

    # Asegurar límite de 45 palabras
    words = narracion.split()
    if len(words) > 45:
        narracion = " ".join(words[:45])

    result = {
        "window_id": wid,
        "t0": t0,
        "t1": t1,
        "analisis_tactico": analisis,
        "narracion_es": narracion,
    }

    # Simular latencia y tokens
    latency_ms = 5.0
    tokens_in = len(_build_prompt(window)) // 4
    tokens_out = len(analisis + narracion) // 4

    return result, latency_ms, tokens_in, tokens_out


# ---------------------------------------------------------------------------
# Agente principal
# ---------------------------------------------------------------------------

def run_agent_narrator(
    tactical_path: str | pathlib.Path = TACTICAL_PATH,
    narrations_path: str | pathlib.Path = NARRATIONS_PATH,
) -> dict:
    """
    Procesa las 8 ventanas tácticas con ibm/granite-4-h-small.
    Si las credenciales no están configuradas, ejecuta modo OFFLINE.

    Retorna dict con:
        status      : "PASS" | "FAIL"
        narrations  : lista de narraciones generadas
        mode        : "online" | "offline" | "mixto" (hubo ventanas sin LLM)
        m3_report   : reporte del Monitor M3
    """
    tactical_path = pathlib.Path(tactical_path)
    narrations_path = pathlib.Path(narrations_path)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    # Limpiar audit log anterior
    audit_log = CLEAN_DIR / "governance_audit.jsonl"
    if audit_log.exists():
        audit_log.unlink()

    # Cargar ventanas tácticas
    if not tactical_path.exists():
        raise FileNotFoundError(f"No se encontró {tactical_path}. Ejecuta el engine primero.")

    with open(tactical_path, encoding="utf-8") as f:
        tactical_summaries = json.load(f)

    print(f"\n[agent_narrator] Procesando {len(tactical_summaries)} ventanas tácticas …")

    # Verificar credenciales
    creds = _get_watsonx_credentials()
    if creds is None:
        mode = "offline"
        model = None
        print("[agent_narrator] Credenciales no configuradas en .env → modo OFFLINE determinista")
    else:
        mode = "online"
        model = _init_watsonx_model(creds)
        if model is None:
            mode = "offline"
            print("[agent_narrator] SDK watsonx no disponible → modo OFFLINE determinista")
        else:
            print(f"[agent_narrator] Modelo: {REQUIRED_MODEL} (online)")

    # Inicializar Monitor M3
    monitor = GovernanceMonitorM3(tactical_summaries)

    narrations = []
    for window in tactical_summaries:
        wid = window["window_id"]
        print(f"  [{wid}] Generando narración …", end=" ")
        window_mode = "offline"

        if mode == "online" and model is not None:
            prompt = _build_prompt(window)
            result, latency_ms, tokens_in, tokens_out = _call_watsonx(model, prompt)
            if result is None:
                # Fallback offline si la llamada falló
                print("(fallback offline)")
                result, latency_ms, tokens_in, tokens_out = _generate_offline_narration(window)
            else:
                window_mode = "online"
                print(f"✓ ({latency_ms:.0f} ms)")
        else:
            result, latency_ms, tokens_in, tokens_out = _generate_offline_narration(window)
            print(f"✓ offline ({latency_ms:.0f} ms)")

        # Agregar metadatos de auditoría
        result["latency_ms"] = round(latency_ms, 2)
        result["tokens_in"] = tokens_in
        result["tokens_out"] = tokens_out
        result["mode"] = window_mode

        # Auditar con Monitor M3
        audit = monitor.audit_call(
            model_id=REQUIRED_MODEL,
            window_id=wid,
            llm_response={k: result[k] for k in ("window_id", "t0", "t1", "analisis_tactico", "narracion_es") if k in result},
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            mode=window_mode,
        )

        narrations.append(result)

    # El modo global refleja lo que ocurrió, no lo que se intentó
    window_modes = {n["mode"] for n in narrations}
    if len(window_modes) > 1:
        mode = "mixto"
    elif window_modes:
        mode = window_modes.pop()

    # Guardar narrations.json
    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, indent=2, ensure_ascii=False)
    print(f"\n[agent_narrator] Narrations guardadas → {narrations_path}")

    # Reporte final M3
    m3_report = monitor.finalize_report()

    return {
        "status": m3_report["status"],
        "narrations": narrations,
        "mode": mode,
        "m3_report": m3_report,
        "n_windows": len(narrations),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    result = run_agent_narrator()
    print(f"\n[agent_narrator] Estado: {result['status']}")
    print(f"[agent_narrator] Modo: {result['mode']}")
    print(f"[agent_narrator] Ventanas procesadas: {result['n_windows']}")
    raise SystemExit(0 if result["status"] == "PASS" else 1)
