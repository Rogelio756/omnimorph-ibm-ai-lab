# Sesión 05 — IBM Bob IDE
## Despliegue FastAPI + IBM watsonx Orchestrate + GitHub
**Fecha:** 2026-11-04
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA
**Equipo:** Rogelio Leonardo Mendez Macias
**Herramientas IBM utilizadas:** IBM Bob IDE + IBM watsonx Orchestrate (trial 30 dias)

---

## Objetivo de la sesión

1. Crear el servidor FastAPI para exponer el Omnimorph Engine como herramienta HTTP.
2. Preparar el despliegue en IBM watsonx Orchestrate via OpenAPI.
3. Inicializar el repositorio Git y subir el codigo a GitHub.
4. Crear la carpeta `bob_sessions/` con los reportes de sesiones.

---

## Trabajo realizado con IBM Bob IDE

### Archivos creados

| Archivo | Descripcion |
|---|---|
| `implementacion/cloud_tool/api_server.py` | Servidor FastAPI con endpoints GET /, GET /health, POST /process |
| `implementacion/cloud_tool/launch_ngrok.py` | Lanza uvicorn + tunel ngrok publico para Orchestrate |
| `deploy_code_engine.py` | Deploy en IBM Cloud Code Engine via REST API (sin CLI) |
| `Dockerfile` | Imagen Docker para Code Engine (Python 3.12 slim) |
| `requirements-api.txt` | Dependencias minimas para el servidor API |
| `bob_sessions/*.md` | Reportes de las 5 sesiones de IBM Bob IDE |

### Validacion del servidor FastAPI

```
GET  /         → 200 {"status": "ok", "service": "Omnimorph Engine Tool", "version": "1.0.0"}
GET  /health   → 200 {"status": "ok", "data_ready": true, "frames_parquet": true, "objects_parquet": true}
POST /process  → 200 {"status": "PASS", "elapsed_s": 1.625, "tactical_summaries": [8 ventanas]}
               → M2.0 PASS, M2.1 PASS, M2.2 PASS, M2.3 PASS, M2.4 PASS, M2.5 PASS
```

### Repositorio GitHub

- **URL:** https://github.com/Rogelio756/omnimorph-ibm-ai-lab
- **Rama:** master
- **Commit inicial:** `f9d07c2` — 29 archivos, 6502 inserciones
- **Archivos excluidos de Git (AGENTS.md §3):** `.env`, `.mp4`, `.parquet`, `.pt`, `.venv/`

### Activacion de IBM watsonx Orchestrate

- **Trial activado:** 30 dias (IBM SaaS, AWS, Londres eu-west-2)
- **URL:** https://dl.watson-orchestrate.ibm.com
- **Estado:** 2 agentes live existentes + nueva instancia `watsonx-orchestrate-qe` creada
- **Paso pendiente:** Importar `openapi_tool.yaml` via Skills & Tools → Add tool → Import from OpenAPI

---

## Estado final del pipeline — Corrida de verificacion

```
run_pipeline.py --use-real  →  9/9 PASS en 63.1 s
```

| Monitor | Estado |
|---|---|
| M1 — Observabilidad de Percepcion | PASS |
| M2.0 — Separacion track/ball | PASS |
| M2.1 — Homografia EMA normalizada | PASS |
| M2.2 — Track Stitching | PASS |
| M2.3 — Cinematica Savitzky-Golay | PASS |
| M2.4 — Ventanas Tacticas | PASS |
| M2.5 — Integridad del pipeline | PASS |
| M3 — Auditoria LLM (ibm/granite-4-h-small) | PASS |
| M4 — Sincronizacion TTS y Dashboard | PASS |

---

## Reglas del IBM SkillsBuild AI Experiential Learning Lab aplicadas

| Regla | Cumplimiento |
|---|---|
| IBM Bob IDE obligatorio | Todas las sesiones desarrolladas en IBM Bob |
| IBM watsonx.ai con modelos Granite | ibm/granite-4-h-small activo y auditado en M3 |
| IBM watsonx Orchestrate (opcional) | Trial activado, OpenAPI spec lista para importar |
| Despliegue 100% local | Pipeline corre localmente; servidor FastAPI en localhost:8000 |
| Sin datos confidenciales ni PII | Dataset publico de Hugging Face (videos de partidos de futbol) |
| Sin modelos prohibidos | Solo ibm/granite-4-h-small (familia Granite autorizada) |
| bob_sessions exportadas | 5 sesiones documentadas en `bob_sessions/*.md` |

---

## Tokens y metricas de sesion

| Metrica | Valor |
|---|---|
| Herramienta | IBM Bob IDE |
| Modelo asistente | IBM Bob |
| Archivos generados | api_server.py, launch_ngrok.py, Dockerfile, requirements-api.txt, deploy_code_engine.py, 5 sesiones bob_sessions |
| Repositorio GitHub | https://github.com/Rogelio756/omnimorph-ibm-ai-lab |
| Corridas de pipeline | 2 (verificacion pre y post FastAPI) |
| Estado final | 9/9 monitores PASS |
