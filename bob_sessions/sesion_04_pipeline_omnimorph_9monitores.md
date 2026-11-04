# Sesión 04 — IBM Bob IDE
## Implementación del Pipeline Omnimorph — Etapas 1 a 5 + Monitores M1 a M4
**Fecha:** 2026-11-02
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA
**Equipo:** Rogelio Leonardo Mendez Macias
**Herramientas IBM utilizadas:** IBM Bob IDE + IBM watsonx.ai (`ibm/granite-4-h-small`)

---

## Objetivo de la sesión

Construir e integrar el pipeline operativo completo de Omnimorph de principio a fin:
- ETAPA 1: Dataset + Monitor M1
- ETAPA 2: Omnimorph Engine (Fases 1-5) + Monitores M2.0 a M2.5
- ETAPA 3: Agente Narrador LLM (`ibm/granite-4-h-small`) + Monitor M3
- ETAPA 4: TTS + Dashboard Streamlit 4 paneles + Monitor M4
- ETAPA 5: Orquestador maestro `run_pipeline.py`

---

## Trabajo realizado con IBM Bob IDE

IBM Bob genero todos los modulos del pipeline desde cero, implementando los 9 monitores de verificacion y asegurando que cada etapa respete las reglas de gobernanza de `AGENTS.md`.

### Archivos creados por IBM Bob

| Archivo | Descripcion |
|---|---|
| `implementacion/dataset/dataset_manager.py` | Descarga/sincroniza parquets desde HF o local |
| `implementacion/dataset/monitor_m1.py` | Monitor M1: 750+ frames, homografia >= 95%, track y ball presentes |
| `implementacion/cloud_tool/omnimorph_engine.py` | Engine Fases 1-5 con Monitores M2.0-M2.5 |
| `implementacion/cloud_tool/adk_tool.py` | Decorador @tool ADK con fallback local |
| `implementacion/cloud_tool/openapi_tool.yaml` | Especificacion OpenAPI 3.0 para Orchestrate |
| `implementacion/cloud_agent/agent_narrator.py` | Agente narrador ibm/granite-4-h-small |
| `implementacion/cloud_agent/governance_monitor_m3.py` | Monitor M3: auditoria LLM + anti-alucinacion |
| `implementacion/dashboard/tts_service.py` | TTS local (windows_sapi) con Monitor M4 |
| `implementacion/dashboard/app.py` | Dashboard Streamlit 4 paneles sincronizados |
| `run_pipeline.py` | Orquestador maestro end-to-end |

### Dataset seleccionado

- **Fuente:** Hugging Face `QimingLi/video_human_select_Soccer`
- **Clip MVP:** `L6sbfskaTDQ-720-13.mp4` — Brasil vs. Alemania, Semifinal Mundial FIFA 2014
- **Telemetria:** 1800 frames (60 s @ 30 FPS), 26 909 objetos
- **Modelos de percepcion GPU:** YOLOv8x (cancha + jugadores), InferenceSlicer (balon), ByteTrack, SigLIP+KMeans

### Fases del Omnimorph Engine implementadas

| Fase | Descripcion | Resultado en clip_13 |
|---|---|---|
| Fase 1 | Separacion track/ball, moda de equipo | 10 818 filas track, 572 filas ball, 198 track_ids |
| Fase 2 (P1) | Homografia EMA normalizada H/H[2,2] | 1071/1800 crudas → 1800/1800 con EMA (100%) |
| Fase 3 (P3) | Track Stitching Algoritmo Hungaro | 198 IDs fragmentados → 22 dorsales cosidos |
| Fase 4 (P2) | Cinematica Savitzky-Golay v <= 9.5 m/s | 100% velocidades acotadas |
| Fase 5 | Ventanas tacticas de 4.0 s | 8 ventanas W0-W7 cubriendo 60 s |

---

## Resultados de monitores — Corrida oficial `run_pipeline.py --use-real`

| Monitor | Nombre | Metrica observada | Estado |
|---|---|---|---|
| **M1** | Observabilidad de Percepcion y Dataset | 1800 frames, 10 818 tracks, 572 balls | PASS |
| **M2.0** | Separacion track/ball y moda de equipo | 198 track_ids con equipo asignado | PASS |
| **M2.1** | Homografia EMA normalizada | 1800/1800 (100%) con continuidad H_ema | PASS |
| **M2.2** | Track Stitching (Algoritmo Hungaro) | 198 IDs → 22 dorsales cosidos (<= 25) | PASS |
| **M2.3** | Cinematica Savitzky-Golay | 100% velocidades <= 9.5 m/s | PASS |
| **M2.4** | Ventanas Tacticas | 8 ventanas (W0-W7) cubriendo 60.0 s | PASS |
| **M2.5** | Integridad del pipeline completo | 3 artefactos generados correctamente | PASS |
| **M3** | Auditoria LLM y watsonx.governance | ibm/granite-4-h-small, 8/8 PASS, 0.5287 RU | PASS |
| **M4** | Sincronizacion TTS y Dashboard | 8/8 clips WAV <= 3.90 s, desfase 8.6 ms | PASS |

**Resultado global: 9/9 PASS en 63.1 segundos**

---

## Integracion con IBM watsonx.ai

- **Modelo usado:** `ibm/granite-4-h-small` (activo en trial watsonx Orchestrate AWS)
- **API usada:** Chat API (`model.chat(messages=[...])`) — requerida para modelos Granite 4
- **Credenciales:** Exclusivamente desde `.env` (`IBM_CLOUD_API_KEY`, `WATSONX_URL`, `WATSONX_SPACE_ID`)
- **Latencia media:** 1 170 ms por ventana
- **Costo total:** 0.5287 RU (8 ventanas)
- **Narraciones:** Generadas en espanol, <= 30 palabras, sobre datos reales del partido

### Ejemplo de narracion generada (ventana W3, t=15.0-22.5 s)

> "Brasil adelanta lineas con intensidad buscando abrir espacios ante la defensa de Alemania."

---

## Reglas de gobernanza aplicadas (AGENTS.md)

- Modelo IBM Granite exclusivo (`ibm/granite-4-h-small`)
- Cero API keys en codigo — todas las credenciales desde `.env`
- No se suben archivos `.mp4`, `.parquet`, `.pt` ni `.env` a Git
- Anti-alucinacion verificada en Monitor M3 (equipo dominante coincide con datos reales)

---

## Tokens y metricas de sesion

| Metrica | Valor |
|---|---|
| Herramienta | IBM Bob IDE |
| Modelo asistente | IBM Bob |
| Modelo LLM de produccion | ibm/granite-4-h-small (IBM watsonx.ai) |
| Archivos generados | 10 modulos Python + 1 YAML + run_pipeline.py |
| Tiempo de pipeline end-to-end | 63.1 s |
| Monitores en PASS | 9/9 |
| Ventanas tacticas generadas | 8 (W0-W7) |
| Clips TTS generados | 8 (WAV, windows_sapi) |
| Costo LLM | 0.5287 RU |
