# 🤖 Guía de Prompts para Ejecución en IBM Bob IDE (Omnimorph)

> **Presupuesto del Equipo:** 40 Bobcoins compartidos.
> **Instrucción clave:** Abre el repositorio en **IBM Bob IDE**, ejecuta únicamente el prompt de la sesión asignada a tu rol y, al terminar, **exporta el historial `.md` y toma captura de pantalla del resumen de consumo** para subirlos a `bob_sessions/`.

---

## Sesión Bob 1 · Empaquetado ADK y Validación Matemática (`M2.0` a `M2.5`)

**Responsable sugerido:** Equipo de Matemáticas / Backend
**Archivos objetivo:** `implementacion/cloud_tool/omnimorph_engine.py`, `implementacion/cloud_tool/adk_tool.py`, `tests/test_monitors.py`

### 📋 Copia y pega este Prompt en IBM Bob IDE:
```markdown
Lee `AGENTS.md` y `implementacion/cloud_tool/omnimorph_engine.py`.
Necesito completar dos archivos sin modificar la lógica matemática existente en `run_omnimorph_engine`:

1. Crea `implementacion/cloud_tool/adk_tool.py`:
   - Envuelve `process_parquet_files` como una herramienta compatible con IBM watsonx Orchestrate ADK (`@tool` de `ibm_watsonx_orchestrate.agent_builder.tools`, con fallback limpio si el paquete ADK no está instalado localmente).
   - Incluye docstring claro con tipos de entrada y salida JSON para que el agente en Orchestrate sepa cuándo invocarla.

2. Crea `tests/test_monitors.py`:
   - Genera un dataset sintético de prueba (o carga `frames.parquet` y `objects.parquet` si existen en `data/raw/`) con 100 frames a 25 fps, incluyendo un pico artificial de ruido en H y dos fragmentos de track del mismo equipo.
   - Ejecuta `run_omnimorph_engine` y verifica con `assert` que todos los monitores (`M2.0_input_schema`, `M2.1_sources_and_teams`, `M2.2_homography_p1`, `M2.3_track_stitching_p3`, `M2.4_kinematics_p2`, `M2.5_tactical_windows`) devuelvan `"status": "PASS"` y que `max_player_speed_mps <= 9.5`.
   - Corre el test y muéstrame la salida de los 6 monitores.
```

---

## Sesión Bob 2 · Agente en `watsonx.ai` (`ibm/granite-3-8b-instruct`) + Monitor `M3`

**Responsable sugerido:** Integración IA Cloud y Gobernanza
**Archivos objetivo:** `implementacion/cloud_agent/agent_narrator.py`, `implementacion/cloud_agent/governance_logger.py`

### 📋 Copia y pega este Prompt en IBM Bob IDE:
```markdown
Lee `AGENTS.md` y `.env.example`.
Crea el módulo de inferencia y gobernanza en `implementacion/cloud_agent/`:

1. `implementacion/cloud_agent/governance_logger.py`:
   - Implementa el **Monitor M3 (`MONITOR M3 · Auditoría LLM y Gobernanza`)**.
   - Valida que el modelo configurado sea estrictamente `ibm/granite-3-8b-instruct` (bloqueando los modelos prohibidos en `AGENTS.md`).
   - Implementa una función `verify_and_log_response(window_summary: dict, llm_output: dict, latency_ms: float, prompt_tokens: int, completion_tokens: int)` que:
     a) Verifique que `llm_output` tenga las llaves `{window_id, t0, t1, analisis_tactico, narracion_es}`.
     b) Verifique que `narracion_es` tenga <= 45 palabras (para caber en una ventana de 4.0 segundos de voz).
     c) Escriba una línea JSON en `data/clean/governance_audit.jsonl` con timestamp ISO, `model_id`, `latency_ms`, `tokens`, costo estimado en RU y `"m3_status": "PASS"`.

2. `implementacion/cloud_agent/agent_narrator.py`:
   - Lee credenciales desde variables de entorno (`IBM_CLOUD_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID`) usando `python-dotenv` sin imprimir jamás las llaves.
   - Conecta con `ibm/granite-3-8b-instruct` en `watsonx.ai` (`temperature=0.3`, `max_new_tokens=220`).
   - Recibe la lista de ventanas `tactical_summaries.json` generada por `omnimorph_engine.py` y devuelve para cada ventana el JSON `{window_id, t0, t1, analisis_tactico, narracion_es}` validado por `governance_logger.py`.
   - Incluye modo simulación (`--dry-run`) para probar el Monitor M3 sin gastar tokens cuando no hay `.env`.
```

---

## Sesión Bob 3 · Dashboard Sincronizado de 4 Paneles + Voz TTS + Monitor `M4`

**Responsable sugerido:** Frontend / UX / Visualización
**Archivos objetivo:** `implementacion/dashboard/tts_service.py`, `implementacion/dashboard/app.py`

### 📋 Copia y pega este Prompt en IBM Bob IDE:
```markdown
Lee `AGENTS.md` y `implementacion/cloud_tool/omnimorph_engine.py`.
Construye el Dashboard Local de Omnimorph en `implementacion/dashboard/`:

1. `implementacion/dashboard/tts_service.py`:
   - Sintetiza en español el campo `narracion_es` de cada ventana de 4.0 s guardando el audio en `data/audio/<window_id>.mp3`.
   - Soporta TTS Local como primario (usando `edge-tts` o `pyttsx3`) y conector opcional a IBM Watson Text to Speech si `USE_LOCAL_TTS=false`.
   - Calcula la duración exacta del audio (`duration_s`) y reporta al **Monitor M4** si `duration_s <= 4.0`.

2. `implementacion/dashboard/app.py` (en Streamlit):
   - Muestra el encabezado con el logo `01_diagramas_y_assets/logos/omnimorph_logo_nombre_light.svg`.
   - Implementa una barra superior de **Semáforos de Monitores en Vivo (`M1`, `M2.0`–`M2.5`, `M3`, `M4`)** leyendo `stage_monitors.json` y `governance_audit.jsonl`.
   - Muestra los **4 Paneles Sincronizados** por el selector/reloj común `frame (0..749) / t (0.0..30.0 s)`:
     - Panel 1: Video local + overlays.
     - Panel 2: Radar cenital 2D limpio dibujando la cancha (120×70 m) y los puntos `(pitch_x_smooth, pitch_y_smooth)` de `objects_cleaned.parquet` coloreados por `team_clean` (ARG vs FRA) y balón.
     - Panel 3: Métricas tácticas de la ventana activa de 4 s (altura de bloque, compactación, transición y presión).
     - Panel 4: Crónica táctica + reproductor de audio TTS sincronizado + estado del Monitor M4.
```
