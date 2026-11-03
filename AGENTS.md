# AGENTS.md — Reglas de Contexto y Arquitectura para IBM Bob IDE

## 1. Propósito del Proyecto (Omnimorph)
Omnimorph es un sistema híbrido de análisis táctico y narración deportiva con IA para fútbol broadcast (1080p, 25 fps, 30 s), desarrollado para el **IBM SkillsBuild AI Experiential Learning Lab | México 2026**.

## 2. Reglas Estrictas de Cumplimiento IBM (Obligatorias)
1. **Seguridad de Credenciales:** JAMÁS escribas API Keys de IBM Cloud ni secretos en archivos de código, logs o Markdown. Lee siempre desde variables de entorno (`os.getenv("IBM_CLOUD_API_KEY")`, `os.getenv("WATSONX_PROJECT_ID")`).
2. **Modelo LLM Permitido en `watsonx.ai`:** Usa exclusivamente **`ibm/granite-3-8b-instruct`** (con `temperature=0.3`, `max_new_tokens=220`).
   - **PROHIBIDO usar:** `llama-3-405b-instruct`, `mistral-large`, `mistral-medium-2502`, `mixtral-8x7b-instruct-v01`, `mistral-small-3-1-24b-instruct-2503`, `pixtral-12b`.
3. **Eficiencia de Bobcoins:** Mantén las respuestas y generación de código directas, modulares y sin dependencias innecesarias.

## 3. Arquitectura de 3 Bloques y Monitores (`M1` a `M4`)
- **Bloque 1 (Local GPU - Congelado):** Produce `frames.parquet` (750 filas) y `objects.parquet` (35,870 filas). Validado por **`MONITOR M1`**.
- **Bloque 2 (Nube - IBM Cloud):**
  - **Custom Python Tool (`watsonx Orchestrate ADK`):** Ejecuta `omnimorph_engine.py` con sus 5 fases secuenciales:
    - Fase 1: Separación `track` vs `ball` y moda de `team_clean` (`MONITOR M2.1`).
    - Fase 2 (`P1`): Normalización `H / H[2,2]` + EMA adaptativo + proyección directa `H_smooth @ p_img` (`MONITOR M2.2`).
    - Fase 3 (`P3`): Re-ID / Track Stitching con Algoritmo Húngaro (`linear_sum_assignment`) y cadenas transitivas (`MONITOR M2.3`).
    - Fase 4 (`P2`): Despiking mediano + derivada analítica Savitzky-Golay (`delta=0.04s`) con cota física `v <= 9.5 m/s` (`MONITOR M2.4`).
    - Fase 5: Resumen táctico en 8 ventanas de 4.0 s (`< 500 B` por ventana) (`MONITOR M2.5`).
  - **Agente LLM (`watsonx Orchestrate` + `watsonx.ai`) y Gobernanza:** Genera crónica táctica y narración en español con `ibm/granite-3-8b-instruct`, auditado por **`MONITOR M3`** (`governance_audit.jsonl`).
- **Bloque 3 (Local - Dashboard Sincronizado):**
  - 4 paneles sincronizados por el reloj común `(frame, t)` + Voz TTS (Local primario o IBM Watson TTS opcional), supervisado por **`MONITOR M4`**.
