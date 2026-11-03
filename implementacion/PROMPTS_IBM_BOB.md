# 🤖 Guía de Prompts para Ejecución en IBM Bob IDE (Omnimorph)

> **Presupuesto del Equipo:** 40 Bobcoins compartidos.
> **Instrucción clave:** Abre el repositorio `omnimorph-ibm-ai-lab` en **IBM Bob IDE**, pega el **Prompt Maestro Integral** (o los prompts modulares por sesión) y, al terminar, **exporta el historial `.md` y toma captura de pantalla del resumen de consumo** para subirlos a `bob_sessions/`.

---

## 🚀 PROMPT MAESTRO INTEGRAL (De Punta a Punta: Desde el Dataset hasta el Dashboard con Monitores `M1`–`M4`)

Copia y pega este bloque completo en **IBM Bob IDE** para que construya y conecte todos los módulos del proyecto siguiendo las reglas del repositorio:

```markdown
Lee primero `AGENTS.md`, `investigacion/FORMULAS_Y_FUNDAMENTOS.md`, `analisis/RESULTADOS_Y_MONITORES.md` e `implementacion/cloud_tool/omnimorph_engine.py`.

Tu tarea es construir e integrar el pipeline operativo completo de **Omnimorph** de principio a fin (empezando desde la ingesta del dataset hasta el Dashboard sincronizado), asegurándote de que cada etapa tenga activo su Monitor de Verificación (`M1`, `M2.0`–`M2.5`, `M3` y `M4`) y respetando estrictamente las reglas de IBM (`ibm/granite-3-8b-instruct`, cero API keys en código, y sin subir archivos `.mp4` a Git).

Construye los siguientes 5 módulos secuenciales y verifica que funcionen integrados:

### ETAPA 1: Dataset, Ingesta Local y MONITOR M1 (`implementacion/dataset/`)
1. Crea `implementacion/dataset/dataset_manager.py`:
   - Incluye una función para descargar bajo demanda clips de prueba desde el dataset de Hugging Face `QimingLi/video_human_select_Soccer` (carpeta `Soccer/`) o cargar archivos `.parquet` locales existentes en `data/raw/` (`frames.parquet` y `objects.parquet` del clip base `2e57b9_0.mp4`, 750 frames a 25 fps).
   - Incluye un generador de telemetría realista de respaldo (`generate_sample_parquets("data/raw")`) con el esquema exacto de 750 filas en `frames.parquet` (`frame, t, n_det, n_track, ball_found, homography_valid, homography_error, n_kp_visible, kp_x, kp_y, kp_conf, H`) y `objects.parquet` (`frame, t, source [det|track|ball], track_id, class_id, class_name, team, x1, y1, x2, y2, conf, pitch_x, pitch_y`), incluyendo el caso testigo del `track_id=19` en el frame 300 y fragmentación de tracks, para que el pipeline pueda probarse de inmediato en cualquier máquina aunque no tenga GPU ni los `.parquet` pesados aún en disco.
2. Crea `implementacion/dataset/monitor_m1.py`:
   - Implementa el **MONITOR M1 (`Observabilidad de Percepción y Dataset`)**: verifica que `frames.parquet` tenga 750 frames, `homography_valid` >= 95%, presencia de `source == 'track'` y `source == 'ball'`, y guarda el reporte en `data/clean/monitor_m1.json` con `"status": "PASS"`.

### ETAPA 2: Custom Python Tool en IBM Cloud (`watsonx Orchestrate ADK`) y MONITORES M2.0 a M2.5 (`implementacion/cloud_tool/`)
1. Revisa `implementacion/cloud_tool/omnimorph_engine.py` (que ya contiene las Fases 1 a 5: separación `track`/`ball` y moda de equipo, P1 Homografía EMA normalizada `H/H[2,2]`, P3 Track Stitching con Algoritmo Húngaro, P2 Cinemática Savitzky-Golay `v <= 9.5 m/s`, y Fase 5 Ventanas Tácticas de 4.0 s, más `stage_monitors` `M2.0` a `M2.5`).
2. Crea `implementacion/cloud_tool/adk_tool.py`:
   - Empaqueta `process_parquet_files` con el decorador `@tool` de **IBM watsonx Orchestrate ADK** (`ibm_watsonx_orchestrate.agent_builder.tools`, con fallback limpio para ejecución local si el paquete ADK no está activo en el entorno).
   - Agrega `implementacion/cloud_tool/openapi_tool.yaml` con la especificación OpenAPI de la herramienta para importación directa en `watsonx Orchestrate`.

### ETAPA 3: Agente Táctico y Narrador en `watsonx.ai` (`ibm/granite-3-8b-instruct`) + MONITOR M3 (`implementacion/cloud_agent/`)
1. Crea `implementacion/cloud_agent/governance_monitor_m3.py`:
   - Implementa el **MONITOR M3 (`Auditoría LLM y watsonx.governance`)**:
     - Verifica que `WATSONX_MODEL_ID == "ibm/granite-3-8b-instruct"` (bloquea cualquier modelo prohibido en `AGENTS.md`).
     - Valida que la salida por ventana sea un JSON con `{window_id, t0, t1, analisis_tactico, narracion_es}`.
     - Verifica que `narracion_es` tenga <= 45 palabras (para caber en una ventana de 4.0 s) y aplica un chequeo anti-alucinación verificando que el equipo dominante coincida con `tactical_summaries.json`.
     - Registra cada llamada en `data/clean/governance_audit.jsonl` (timestamp, modelo, latencia ms, tokens de entrada/salida, costo estimado RU y `"status": "PASS"`).
2. Crea `implementacion/cloud_agent/agent_narrator.py`:
   - Lee credenciales exclusivamente desde `.env` (`IBM_CLOUD_API_KEY`, `WATSONX_URL`, `WATSONX_PROJECT_ID`).
   - Consume las 8 ventanas de `data/clean/tactical_summaries.json`, invoca `ibm/granite-3-8b-instruct` (`temperature=0.3`, `max_new_tokens=220`), audita cada respuesta con el **Monitor M3** y guarda `data/clean/narrations.json`.
   - Si no hay credenciales configuradas en `.env`, ejecuta un modo determinista offline basado en los datos reales de cada ventana para no bloquear las pruebas locales.

### ETAPA 4: Síntesis de Voz TTS y Dashboard Sincronizado de 4 Paneles + MONITOR M4 (`implementacion/dashboard/`)
1. Crea `implementacion/dashboard/tts_service.py`:
   - Genera audio en español (`data/audio/<window_id>.mp3` o `.wav`) para cada ventana usando TTS Local como primario (y soporte opcional para IBM Watson Text to Speech si `USE_LOCAL_TTS=false`).
   - Mide la duración exacta `duration_s` de cada clip de voz y reporta al **Monitor M4 (`data/clean/monitor_m4.json`)** verificando que `duration_s <= 4.0` s y que el desfase de reloj sea `< 40 ms`.
2. Crea `implementacion/dashboard/app.py` (en Streamlit):
   - Muestra el logo `01_diagramas_y_assets/logos/omnimorph_logo_nombre_light.svg`.
   - Muestra en la parte superior el **Tablero de Semáforos de Observabilidad (`M1`, `M2.0`–`M2.5`, `M3`, `M4`)** en tiempo real.
   - Implementa el **Reloj Maestro Común (`frame` 0..749 / `t` 0.0..30.0 s)** que sincroniza los **4 Paneles**:
     - **Panel 1:** Video local / Visor de fotograma y bounding boxes con `track_id_stitched`.
     - **Panel 2:** Radar Cenital 2D limpio (cancha de 120×70 m dibujando `pitch_x_smooth, pitch_y_smooth` de `objects_cleaned.parquet` por equipo ARG/FRA y balón).
     - **Panel 3:** Métricas tácticas de la ventana activa de 4.0 s (`block_height_m`, `block_compactness_m`, `transition_speed_mps`, `pressure_context`).
     - **Panel 4:** Crónica táctica de `ibm/granite-3-8b-instruct` + Reproductor de Audio TTS sincronizado.

### ETAPA 5: Orquestador Maestro y Verificación End-to-End (`run_pipeline.py`)
1. Crea en la raíz `run_pipeline.py` que ejecute en orden:
   - Etapa 1 (`dataset_manager` + `MONITOR M1`)
   - Etapa 2 (`omnimorph_engine` + `MONITORES M2.0 a M2.5`)
   - Etapa 3 (`agent_narrator` + `MONITOR M3`)
   - Etapa 4 (`tts_service` + `MONITOR M4`)
   - Y al final imprima una tabla resumen con el estado (`PASS`/`WARN`/`FAIL`) de los 9 monitores (`M1`, `M2.0`, `M2.1`, `M2.2`, `M2.3`, `M2.4`, `M2.5`, `M3`, `M4`).
2. Ejecuta `python3 run_pipeline.py` para comprobar que todo el flujo corre de principio a fin sin errores y que todos los monitores están en `PASS`.
```

---

## 🧩 Prompts Modulares por Sesión (Si dividen el trabajo entre 3 integrantes)

### Sesión Bob 1 · Empaquetado ADK y Validación Matemática (`M2.0` a `M2.5`)
```markdown
Lee `AGENTS.md` e `implementacion/cloud_tool/omnimorph_engine.py`.
1. Crea `implementacion/cloud_tool/adk_tool.py` envolviendo `process_parquet_files` con `@tool` de IBM watsonx Orchestrate ADK.
2. Crea `tests/test_monitors.py` que pruebe `run_omnimorph_engine` con datos de prueba (o desde `data/raw/`), verifique que los monitores `M2.0` a `M2.5` estén en `"PASS"` y que `max_player_speed_mps <= 9.5`. Corre el test.
```

### Sesión Bob 2 · Agente en `watsonx.ai` (`ibm/granite-3-8b-instruct`) + Monitor `M3`
```markdown
Lee `AGENTS.md` y `.env.example`.
Crea `implementacion/cloud_agent/governance_monitor_m3.py` e `implementacion/cloud_agent/agent_narrator.py` para conectar las 8 ventanas tácticas con `ibm/granite-3-8b-instruct` (`temperature=0.3`, `max_new_tokens=220`), validar el JSON de salida, auditar con el Monitor M3 en `data/clean/governance_audit.jsonl` y guardar `data/clean/narrations.json`.
```

### Sesión Bob 3 · Dashboard Sincronizado de 4 Paneles + Voz TTS + Monitor `M4`
```markdown
Lee `AGENTS.md` e `implementacion/cloud_tool/omnimorph_engine.py`.
Crea `implementacion/dashboard/tts_service.py` e `implementacion/dashboard/app.py` (en Streamlit) con la barra de semáforos de los Monitores `M1` a `M4` y los 4 paneles sincronizados por `(frame, t)`: (1) Video + marcas, (2) Radar 2D limpio desde `objects_cleaned.parquet`, (3) Métricas de ventana de 4s y (4) Narración de Granite 3 8B + Audio TTS sincronizado.
```
