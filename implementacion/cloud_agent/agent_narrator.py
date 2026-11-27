"""
implementacion/cloud_agent/agent_narrator.py
=============================================
Agente Táctico y Narrador — ibm/granite-4-h-small

Lee las 8 ventanas de data/clean/tactical_summaries.json,
invoca ibm/granite-4-h-small (temperature=0.3, max_tokens=220),
audita cada respuesta con el Monitor M3 (con hasta 2 reintentos si falla)
y guarda data/clean/narrations.json.

Credenciales exclusivamente desde .env:
  IBM_CLOUD_API_KEY, WATSONX_URL, WATSONX_PROJECT_ID (o WATSONX_SPACE_ID)

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
from typing import Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
REQUIRED_MODEL = "ibm/granite-4-h-small"
WATSONX_TEMPERATURE = 0.3
WATSONX_MAX_TOKENS = 220
MAX_RETRIES = 2
CLEAN_DIR = pathlib.Path("data/clean")
TACTICAL_PATH = CLEAN_DIR / "tactical_summaries.json"
NARRATIONS_PATH = CLEAN_DIR / "narrations.json"
AUDIT_LOG_PATH = CLEAN_DIR / "governance_audit.jsonl"
REPORT_M3_PATH = CLEAN_DIR / "monitor_m3.json"

_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.cloud_agent.governance_monitor_m3 import (
    GovernanceMonitorM3,
    MAX_NARRATION_WORDS,
)
from implementacion import partido_config
from implementacion.cloud_agent.red_ipv4 import preferir_ipv4_en_ibm

preferir_ipv4_en_ibm()


# ---------------------------------------------------------------------------
# Configuración watsonx.ai
# ---------------------------------------------------------------------------

def _get_watsonx_credentials() -> Optional[dict]:
    """
    Lee credenciales exclusivamente desde el entorno.
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


def _init_watsonx_model(creds: dict):
    """
    Inicializa ibm/granite-4-h-small con el SDK ibm-watsonx-ai.
    No imprime space_id ni project_id.
    """
    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference

        credentials = Credentials(
            url=creds["url"],
            api_key=creds["api_key"],
        )

        init_kwargs = dict(
            model_id=REQUIRED_MODEL,
            credentials=credentials,
            params={
                "temperature": WATSONX_TEMPERATURE,
                "max_new_tokens": WATSONX_MAX_TOKENS,
                "max_tokens": WATSONX_MAX_TOKENS,
            },
        )
        if creds.get("space_id"):
            init_kwargs["space_id"] = creds["space_id"]
        else:
            init_kwargs["project_id"] = creds["project_id"]

        return ModelInference(**init_kwargs)
    except ImportError:
        print("[agent_narrator] ibm-watsonx-ai SDK no disponible — modo OFFLINE.")
        return None
    except Exception as exc:
        print(f"[agent_narrator] Error inicializando watsonx.ai: {exc} — modo OFFLINE.")
        return None


# ---------------------------------------------------------------------------
# Helpers de formato de métricas
# ---------------------------------------------------------------------------

def _redondear_entero(val: Any) -> Optional[int]:
    if val is None or (isinstance(val, float) and val != val):
        return None
    return int(round(float(val)))


def _lineas_equipo_prompt(nombre: str, codigo: str, datos_eq: dict) -> str:
    """
    Formatea las 4 medidas de un equipo redondeadas a enteros, con nombre.
    Omite los valores None.
    """
    partes = []
    pos = _redondear_entero(datos_eq.get("posicion_m"))
    pct = _redondear_entero(datos_eq.get("pct_campo_rival"))
    largo = _redondear_entero(datos_eq.get("largo_m"))
    ancho = _redondear_entero(datos_eq.get("ancho_m"))

    if pos is not None:
        partes.append(f"posición media a {pos} m de su portería")
    if pct is not None:
        partes.append(f"{pct}% en campo rival")
    if largo is not None:
        partes.append(f"largo de {largo} m")
    if ancho is not None:
        partes.append(f"ancho de {ancho} m")

    if not partes:
        return f"- {nombre} ({codigo}): sin observaciones en este tramo"
    return f"- {nombre} ({codigo}): " + ", ".join(partes)


# ---------------------------------------------------------------------------
# Generador de prompts
# ---------------------------------------------------------------------------

def _build_prompt(window: dict, errores_previos: Optional[List[str]] = None) -> str:
    """
    Construye el prompt para ibm/granite-4-h-small dada una ventana táctica.
    Recibe territorio y las 4 medidas de los DOS equipos, redondeadas a enteros, con nombre.
    """
    wid = window["window_id"]
    t0 = window["t0"]
    t1 = window["t1"]
    territorio = window.get("territorio") or window.get("dominant_team") or "repartido"
    if territorio == "neutro":
        territorio = "repartido"

    partido = partido_config.activo()
    eq0, eq1 = partido.equipos
    equipos_w = window.get("equipos") or {}
    datos0 = equipos_w.get(eq0.codigo) or {}
    datos1 = equipos_w.get(eq1.codigo) or {}

    eq_dom = partido.equipo_por_codigo(territorio)
    if eq_dom is not None:
        rival = eq1 if eq_dom.team_id == 0 else eq0
        datos_dom = datos0 if eq_dom.team_id == 0 else datos1
        pos_ej = _redondear_entero(datos_dom.get("posicion_m")) or 65
        territorio_linea = f"{eq_dom.nombre} ({eq_dom.codigo})"
        regla_territorio = (
            f"El territorio corresponde a {eq_dom.nombre}: la narración DEBE nombrar a {eq_dom.nombre} "
            f"y NO puede decir que el territorio está repartido o parejo. "
            f"No afirmes que el otro equipo está más adelantado ni en campo rival."
        )
    else:
        rival = eq1
        pos_ej = _redondear_entero(datos1.get("posicion_m")) or 65
        territorio_linea = "repartido"
        regla_territorio = (
            "El territorio está repartido: NO digas que alguno de los dos equipos está más adelantado."
        )

    ej_dom = eq_dom if eq_dom is not None else eq1
    ej_riv = rival if eq_dom is not None else eq0
    ejemplo_territorio = (
        f"{ej_dom.nombre} juega adelantado, a {pos_ej} metros de su portería; {ej_riv.nombre} queda en su mitad."
    )
    ejemplo_repartido = (
        "Territorio repartido: ninguno de los dos equipos ocupa claramente más campo rival."
    )

    linea_eq0 = _lineas_equipo_prompt(eq0.nombre, eq0.codigo, datos0)
    linea_eq1 = _lineas_equipo_prompt(eq1.nombre, eq1.codigo, datos1)

    bloque_errores = ""
    if errores_previos:
        lista_err = "\n".join(f"  * {e}" for e in errores_previos)
        bloque_errores = (
            f"\nATENCIÓN — Tu intento anterior fue rechazado por el monitor M3 por estos motivos:\n"
            f"{lista_err}\n"
            f"Corrige esos errores estrictamente en esta respuesta.\n"
        )

    prompt = f"""Eres un analista táctico de fútbol del partido {partido.titulo} ({partido.competicion}).

Datos medidos en el tramo {wid}:
- Territorio: {territorio_linea}
{linea_eq0}
{linea_eq1}

Describe únicamente dónde está cada equipo en la cancha y qué espacio ocupa (largo y ancho visibles):
1. "analisis_tactico": exactamente 2 oraciones en español (una para {eq0.nombre} y otra para {eq1.nombre}). Escribe los números en cifras (dígitos, nunca en letras) y usa SOLO los números dados arriba para cada equipo. No escribas los segundos del tramo.
2. "narracion_es": frase para voz de MÁXIMO {MAX_NARRATION_WORDS} PALABRAS (para durar menos de 3.9 s), sin cifras o con una sola cifra de las dadas arriba (en dígitos).
   - Ejemplo válido para este tramo: "{ejemplo_territorio if eq_dom is not None else ejemplo_repartido}"
3. {regla_territorio}
   Solo di que un equipo está «en la mitad rival» o «en campo rival» si tiene 50 % o más en campo rival; si tiene menos de 50 %, está «en su mitad».
4. PROHIBIDO usar cualquiera de estas palabras o sus derivados (por raíz): posesión, presiona, presión, domina, dominio, controla, control, lucha, disputa, busca, intenta, quiere, pretende, ataca, ataque, gol, marcador, velocidad, repliega, repliegue, retrocede, empuja, arrincona, acorrala, encierra, encerrado, avanza. Prohibido mencionar intenciones de los jugadores, nombres de jugadores, goles, marcador o velocidades, y prohibido escribir números con letras.{bloque_errores}

Responde EXCLUSIVAMENTE con un objeto JSON válido (sin texto antes ni después):
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
    Devuelve (parsed_json, latency_ms, tokens_in, tokens_out).
    """
    import re
    t0 = time.perf_counter()
    try:
        messages = [
            {"role": "system", "content": (
                "Eres un analista tactico de futbol. "
                "Responde SOLO con un JSON valido, sin texto adicional, sin markdown, sin explicaciones."
            )},
            {"role": "user", "content": prompt},
        ]
        response = model.chat(messages=messages)
        latency_ms = (time.perf_counter() - t0) * 1000

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

        json_match = re.search(r"\{.*\}", generated_text, re.DOTALL)
        parsed = json.loads(json_match.group()) if json_match else None

        return parsed, latency_ms, int(tokens_in), int(tokens_out)

    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000
        print(f"  [agent_narrator] Error llamando watsonx (chat): {exc}")
        try:
            t1 = time.perf_counter()
            generated_text = model.generate_text(prompt=prompt) or ""
            latency_ms = (time.perf_counter() - t1) * 1000
            json_match = re.search(r"\{.*\}", generated_text, re.DOTALL)
            parsed = json.loads(json_match.group()) if json_match else None
            return parsed, latency_ms, len(prompt) // 4, len(generated_text) // 4
        except Exception as exc2:
            latency_ms2 = (time.perf_counter() - t0) * 1000
            print(f"  [agent_narrator] Fallback generate_text tambien fallo: {exc2}")
            return None, latency_ms2, 0, 0


# ---------------------------------------------------------------------------
# Modo OFFLINE determinista
# ---------------------------------------------------------------------------

def _oracion_equipo_offline(nombre: str, datos_eq: dict) -> str:
    pos = _redondear_entero(datos_eq.get("posicion_m"))
    pct = _redondear_entero(datos_eq.get("pct_campo_rival"))
    largo = _redondear_entero(datos_eq.get("largo_m"))
    ancho = _redondear_entero(datos_eq.get("ancho_m"))

    fragmentos = []
    if pos is not None:
        fragmentos.append(f"se ubica a {pos} m de su portería")
    if pct is not None:
        fragmentos.append(f"con {pct}% en campo rival")
    if largo is not None and ancho is not None:
        fragmentos.append(f"ocupando {largo} m de largo por {ancho} m de ancho")
    elif largo is not None:
        fragmentos.append(f"con {largo} m de largo")
    elif ancho is not None:
        fragmentos.append(f"con {ancho} m de ancho")

    if not fragmentos:
        return f"{nombre} no registra observaciones visibles en este tramo."
    return f"{nombre} " + ", ".join(fragmentos) + "."


def _generate_offline_narration(window: dict) -> tuple[dict, float, int, int]:
    """
    Genera narración determinista offline basada en los datos reales de la ventana.
    Cumple todas las reglas de M3:
      - <= 18 palabras en narracion_es (sin cifras o con una sola).
      - 2 oraciones en analisis_tactico con cifras exactas de cada equipo.
      - Cero palabras prohibidas y coherencia total con territorio.
    """
    wid = window["window_id"]
    t0 = window["t0"]
    t1 = window["t1"]
    territorio = window.get("territorio") or window.get("dominant_team") or "repartido"
    if territorio == "neutro":
        territorio = "repartido"

    partido = partido_config.activo()
    eq0, eq1 = partido.equipos
    equipos_w = window.get("equipos") or {}
    datos0 = equipos_w.get(eq0.codigo) or {}
    datos1 = equipos_w.get(eq1.codigo) or {}

    oracion0 = _oracion_equipo_offline(eq0.nombre, datos0)
    oracion1 = _oracion_equipo_offline(eq1.nombre, datos1)
    analisis = f"{oracion0} {oracion1}"

    eq_dom = partido.equipo_por_codigo(territorio)
    if eq_dom is not None:
        rival = eq1 if eq_dom.team_id == 0 else eq0
        datos_dom = datos0 if eq_dom.team_id == 0 else datos1
        pos_dom = _redondear_entero(datos_dom.get("posicion_m"))
        if pos_dom is not None:
            narracion = f"{eq_dom.nombre} juega adelantado, a {pos_dom} metros de su portería; {rival.nombre} queda en su mitad."
        else:
            narracion = f"{eq_dom.nombre} juega adelantado en campo rival; {rival.nombre} queda en su mitad."
    else:
        narracion = "Territorio repartido: ninguno de los dos equipos ocupa claramente más campo rival."

    words = narracion.split()
    if len(words) > MAX_NARRATION_WORDS:
        narracion = " ".join(words[:MAX_NARRATION_WORDS])

    result = {
        "window_id": wid,
        "t0": t0,
        "t1": t1,
        "analisis_tactico": analisis,
        "narracion_es": narracion,
    }

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
    audit_log: str | pathlib.Path = AUDIT_LOG_PATH,
    report_path: str | pathlib.Path = REPORT_M3_PATH,
    model_override: Any = None,
    model_id_override: Optional[str] = None,
) -> dict:
    """
    Procesa las 8 ventanas tácticas con ibm/granite-4-h-small.
    Si M3 da FAIL, reintenta con Granite hasta 2 veces enviando los errores.
    Si sigue en FAIL, usa la plantilla offline con mode="offline".
    Registra todos los intentos en audit_log y guarda el reporte final en report_path.
    """
    tactical_path = pathlib.Path(tactical_path)
    narrations_path = pathlib.Path(narrations_path)
    audit_log = pathlib.Path(audit_log)
    report_path = pathlib.Path(report_path)

    narrations_path.parent.mkdir(parents=True, exist_ok=True)
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if audit_log.exists():
        audit_log.unlink()

    if not tactical_path.exists():
        raise FileNotFoundError(f"No se encontró {tactical_path}. Ejecuta el engine primero.")

    with open(tactical_path, encoding="utf-8") as f:
        tactical_summaries = json.load(f)

    print(f"\n[agent_narrator] Procesando {len(tactical_summaries)} ventanas tácticas …")

    effective_model_id = model_id_override or REQUIRED_MODEL

    if model_override is not None:
        mode = "online"
        model = model_override
        print(f"[agent_narrator] Modelo (override): {effective_model_id} (online)")
    else:
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
                print(f"[agent_narrator] Modelo: {effective_model_id} (online)")

    monitor = GovernanceMonitorM3(tactical_summaries, audit_log=audit_log)

    narrations = []
    for window in tactical_summaries:
        wid = window["window_id"]
        print(f"  [{wid}] Generando narración …", end=" ")

        if mode == "online" and model is not None:
            errores_previos: Optional[List[str]] = None
            exito_online = False
            result = None
            latency_ms = 0.0
            tokens_in = 0
            tokens_out = 0

            for intento in range(1, MAX_RETRIES + 2):  # hasta 3 intentos (1 inicial + 2 reintentos)
                prompt = _build_prompt(window, errores_previos=errores_previos)
                cand, lat, tin, tout = _call_watsonx(model, prompt)
                llm_resp = (
                    {k: cand[k] for k in ("window_id", "t0", "t1", "analisis_tactico", "narracion_es") if k in cand}
                    if isinstance(cand, dict) else None
                )
                audit = monitor.audit_call(
                    model_id=effective_model_id,
                    window_id=wid,
                    llm_response=llm_resp,
                    latency_ms=lat,
                    tokens_in=tin,
                    tokens_out=tout,
                    mode="online",
                    attempt=intento,
                )
                if audit["status"] == "PASS" and cand is not None:
                    result = cand
                    latency_ms, tokens_in, tokens_out = lat, tin, tout
                    exito_online = True
                    print(f"✓ online intento {intento} ({latency_ms:.0f} ms)")
                    break
                errores_previos = audit.get("errors", ["Respuesta inválida"])

            if exito_online and result is not None:
                window_mode = "online"
            else:
                print("(fallback offline tras agotar reintentos)")
                result, latency_ms, tokens_in, tokens_out = _generate_offline_narration(window)
                window_mode = "offline"
                monitor.audit_call(
                    model_id=effective_model_id,
                    window_id=wid,
                    llm_response={k: result[k] for k in ("window_id", "t0", "t1", "analisis_tactico", "narracion_es") if k in result},
                    latency_ms=latency_ms,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    mode="offline",
                    attempt=MAX_RETRIES + 2,
                )
        else:
            result, latency_ms, tokens_in, tokens_out = _generate_offline_narration(window)
            window_mode = "offline"
            print(f"✓ offline ({latency_ms:.0f} ms)")
            monitor.audit_call(
                model_id=effective_model_id,
                window_id=wid,
                llm_response={k: result[k] for k in ("window_id", "t0", "t1", "analisis_tactico", "narracion_es") if k in result},
                latency_ms=latency_ms,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                mode="offline",
                attempt=1,
            )

        result["latency_ms"] = round(latency_ms, 2)
        result["tokens_in"] = tokens_in
        result["tokens_out"] = tokens_out
        result["mode"] = window_mode

        narrations.append(result)

    window_modes = {n["mode"] for n in narrations}
    if len(window_modes) > 1:
        mode = "mixto"
    elif window_modes:
        mode = window_modes.pop()

    with open(narrations_path, "w", encoding="utf-8") as f:
        json.dump(narrations, f, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"\n[agent_narrator] Narrations guardadas → {narrations_path}")

    m3_report = monitor.finalize_report(report_path=report_path)

    return {
        "status": m3_report["status"],
        "narrations": narrations,
        "mode": mode,
        "m3_report": m3_report,
        "n_windows": len(narrations),
    }


if __name__ == "__main__":
    result = run_agent_narrator()
    print(f"\n[agent_narrator] Estado: {result['status']}")
    print(f"[agent_narrator] Modo: {result['mode']}")
    print(f"[agent_narrator] Ventanas procesadas: {result['n_windows']}")
    raise SystemExit(0 if result["status"] == "PASS" else 1)
