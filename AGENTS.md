# AGENTS.md — Reglas del proyecto Omnimorph

## 1. Modelo LLM obligatorio

**Todo agente táctico o narrador DEBE usar exclusivamente un modelo IBM Granite:**

```
ibm/granite-4-h-small          ← modelo activo (trial watsonx Orchestrate AWS)
ibm/granite-3-8b-instruct      ← alternativa si el entorno lo soporta
```

El modelo activo depende del entorno de despliegue:
- **Trial watsonx Orchestrate (AWS):** `ibm/granite-4-h-small`
- **watsonx.ai Studio con WML completo:** `ibm/granite-3-8b-instruct`

Está **PROHIBIDO** usar modelos de terceros, incluyendo:
- `gpt-*` (OpenAI)
- `claude-*` (Anthropic)
- `llama-*` (Meta)
- `mistral-*` (Mistral AI)

El Monitor M3 verifica que el modelo usado sea un IBM Granite autorizado.

---

## 2. Gestión de credenciales — Cero API keys en código

**Nunca escribir API keys, tokens o secretos directamente en el código fuente.**

- Todas las credenciales se leen exclusivamente desde `.env` (con `python-dotenv`).
- El archivo `.env` está en `.gitignore` y NUNCA se sube al repositorio.
- Variables requeridas:
  ```
  IBM_CLOUD_API_KEY=<tu-api-key>
  WATSONX_URL=https://us-south.ml.cloud.ibm.com
  WATSONX_PROJECT_ID=<tu-project-id>
  ```

---

## 3. Git — Restricciones de archivos

**Está PROHIBIDO subir a Git:**
- Archivos `.mp4` (videos) — usar `.gitignore`
- Archivos `.pt` o `.pth` (pesos de modelos)
- Archivos `.parquet` pesados en `data/raw/`
- El directorio `.venv/`
- El directorio `.hf_cache/`
- Archivos `.env`

El pipeline puede generarse localmente con los generadores de telemetría sintética.

---

## 4. Arquitectura del pipeline (resumen)

```
ETAPA 1: Dataset + MONITOR M1
  └─ dataset_manager.py → data/raw/{frames,objects}.parquet

ETAPA 2: Omnimorph Engine + MONITORES M2.0–M2.5
  └─ omnimorph_engine.py → data/clean/{objects_cleaned,tactical_summaries}.parquet/json

ETAPA 3: Agente Narrador + MONITOR M3
  └─ agent_narrator.py → data/clean/narrations.json
  └─ governance_monitor_m3.py → data/clean/governance_audit.jsonl

ETAPA 4: TTS + Dashboard + MONITOR M4
  └─ tts_service.py → data/audio/<window_id>.{mp3,wav}
  └─ app.py (Streamlit, 4 paneles sincronizados)

ETAPA 5: Orquestador maestro
  └─ run_pipeline.py → tabla resumen M1, M2.0–M2.5, M3, M4
```

---

## 5. Monitores de verificación

| Monitor | Responsabilidad |
|---------|----------------|
| **M1** | Observabilidad de Percepción y Dataset |
| **M2.0** | Separación track/ball y moda de equipo |
| **M2.1** | Homografía EMA normalizada |
| **M2.2** | Track Stitching (Algoritmo Húngaro) |
| **M2.3** | Cinemática Savitzky-Golay (v ≤ 9.5 m/s) |
| **M2.4** | Ventanas Tácticas (4.0 s) |
| **M2.5** | Integridad del pipeline completo |
| **M3** | Auditoría LLM y watsonx.governance |
| **M4** | Sincronización TTS y Dashboard |

---

## 6. Dataset de referencia

- **Fuente:** Hugging Face `QimingLi/video_human_select_Soccer` (carpeta `Soccer/`)
- **Clip base:** `2e57b9_0.mp4` — 1920×1080, 25 fps, 750 frames = 30 s
- **Parquet de referencia:** `data/raw/frames.parquet` (750 filas) y `data/raw/objects.parquet`
- **Cancha:** 120 × 70 m (12 000 × 7 000 cm); X: 0 = portería ARG → 12 000 = portería FRA
- **Equipos:** `team_id=0` → ARG (blanco/celeste), `team_id=1` → FRA (azul marino)
- **Caso testigo:** `track_id=19` en el frame 300 (jugador FRA, pitch_x≈7877 cm, pitch_y≈6541 cm)

---

## 7. Convenciones de código

- Python 3.10+
- Dependencias: `pandas`, `numpy`, `scipy`, `pyarrow`, `scikit-learn`, `python-dotenv`
- TTS local: `pyttsx3` (primario) o `gTTS` (fallback)
- Dashboard: `streamlit`
- Sin imports de `openai`, `anthropic` u otras APIs de terceros en código de producción

---

## 8. Continuidad entre Agentes (IBM Bob, Claude Code, Gemini Antigravity)

Para garantizar que el desarrollo continúe sin fricción independientemente del entorno o agente que use el desarrollador (IBM Bob IDE, Claude Code o Gemini en Antigravity):

### A. Meta-agente de Arquitectura: The Architect
- Ubicación central: `tools/the-architect/`
- Enlaces de skills: `.agents/skills/the-architect/` y `.claude/skills/the-architect/`
- Comandos Claude: `.claude/commands/` (`/architect`, `/architect-brownfield`, `/architect-quick`)
- **Modo Brownfield:** Al planear nuevas capacidades sobre el código existente, consultar `tools/the-architect/commands/architect-brownfield.md`.
- **Blueprints:** Los planos técnicos aprobados se guardan en `./blueprints/`.

### B. Bitácora Oficial Unificada: `bob_sessions/`
- Todo agente (Bob, Claude o Gemini) **DEBE registrar al finalizar su trabajo** un reporte detallado en `bob_sessions/` siguiendo la numeración secuencial (`sesion_01`, `sesion_02`, ..., `sesion_07_...`).
- Actualizar siempre la tabla índice de `bob_sessions/README.md`.
- Cualquier agente nuevo que inicie sesión debe leer la última entrada en `bob_sessions/` para retomar el hilo exacto de trabajo.

