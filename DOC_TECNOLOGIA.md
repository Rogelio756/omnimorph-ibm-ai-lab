# Omnimorph — Tecnología utilizada

**IBM SkillsBuild AI Experiential Learning Lab · Entregable 3**
**Fecha:** 2026-11-26 · **Repositorio:** <https://github.com/Rogelio756/omnimorph-ibm-ai-lab> (rama `feat-costa-rica`)

---

## 1. Resumen

Omnimorph es un pipeline de cinco etapas que va del video al texto: visión por computadora → motor de análisis táctico → narración con IBM Granite → voz y web. Cada etapa tiene un monitor que verifica su salida.

**IBM Bob IDE fue el socio de desarrollo central del proyecto:** construyó páginas completas de la web, ejecutó experimentos, documentó la arquitectura y evaluó el producto con una rúbrica. Toda su actividad está registrada en `bob_sessions/`.

## 2. IBM Bob IDE como componente central del desarrollo

### Qué hizo Bob

| Fecha | Tarea de Bob | Resultado | Evidencia |
|---|---|---|---|
| 2026-11-04 | Construcción de la capa visual de Omnimorph y del tablero MATEO a partir de un mockup aprobado | Base visual de las páginas Inicio y MATEO | `bob_export_2026-11-04_capa_visual_*.md` |
| 2026-11-04 | Continuación del proyecto como asistente de desarrollo | Avance del pipeline y la web | `bob_export_2026-11-04_continuacion_proyecto.md` |
| 2026-11-10 | Experimento de lectura de dorsales | Modelo con 84 % de acierto en imágenes de prueba, 0 de 20 en el video real. Resultado negativo documentado, que evitó prometer identificación automática | `bob_export_2026-11-10_dorsales.md`, `sesion_15_dorsales_bob.md` |
| 2026-11-10 | Consultoría y plano *brownfield* del estado del proyecto para el equipo | Documento de arquitectura compartido | `bob_export_2026-11-10_architect_brownfield.md`, `bob_export_2026-11-10_consultoria_sin_codigo.md` |
| 2026-11-14 | Página Partido (ficha, jugadores, comparativa, goles y eventos) | Página en producción | `bob_export_2026-11-14_pagina_partido_fer.md`, `sesion_26_pagina_partido_fer.md` |
| 2026-11-14 | Evaluación del producto con una persona simulada y una rúbrica | Lista de mejoras priorizadas | `bob_export_2026-11-14_evaluacion_rubrica.md` |
| 2026-11-22 | Página Transmisión, en 7 pasos con un commit revisado por paso | Vista tipo TV con voz, radar y alineaciones; 30 de 30 pruebas | `bob_export_transmision.md`, `sesion_36_pagina_transmision.md` |
| 2026-11-23 | Panel simulado de 100 consumidores para evaluar la propuesta y los precios | Hipótesis de precio y objeciones por segmento | `bob_export_panel_100.md` |

### Cómo trabajamos con Bob

- **Encargos escritos:** cada tarea grande empezó con un encargo en `blueprints/` que fijaba alcance, pasos y criterios de aceptación. Bob lo seguía paso a paso y mostraba cada commit antes de hacerlo.
- **Modo arquitecto:** se usaron los comandos de *The Architect* (`/architect-brownfield`) para documentar el código existente antes de cambiarlo.
- **Bitácora:** cada sesión se registró en `bob_sessions/` con un reporte en Markdown. El índice relaciona cada tarea con su exportación oficial, su captura de consumo y su reporte.
- **Consumo:** unos 196 Bobcoins en total (unos 40 de una cuenta anterior, agotada, y 156 de 180 en la cuenta activa al 2026-11-26). Las capturas están en `bob_sessions/capturas/`.

### Otros asistentes

Durante las semanas en que Bob no estuvo disponible (error 525) o sin saldo, el desarrollo continuó con Claude Code (diseño, revisión y correcciones) y Gemini (implementación). Las reglas del proyecto (`AGENTS.md`) son las mismas para los tres, y todos registran su trabajo en la misma bitácora `bob_sessions/`. Estos asistentes se usaron solo para desarrollar: **el producto usa exclusivamente modelos IBM Granite.**

## 3. IBM watsonx.ai e IBM Granite

| | |
|---|---|
| **Modelo** | `ibm/granite-4-h-small`, en watsonx.ai. Es el único modelo de lenguaje del producto; `AGENTS.md` prohíbe modelos de terceros y el monitor M3 lo verifica |
| **Biblioteca** | `ibm-watsonx-ai` 1.8.1 (`ModelInference`) |
| **Credenciales** | Solo en `.env` (`IBM_CLOUD_API_KEY`, `WATSONX_URL`, `WATSONX_SPACE_ID` o `WATSONX_PROJECT_ID`). `.env` está en `.gitignore`; no hay llaves en el código |
| **Uso 1: narrador** | `implementacion/cloud_agent/agent_narrator.py` recibe las métricas de un tramo y redacta una frase de 18 palabras o menos. Si M3 la rechaza, reintenta hasta 2 veces; si sigue fallando, usa una plantilla verificada. Cada intento queda auditado |
| **Uso 2: chat** | `implementacion/cloud_agent/chat_agent.py` responde preguntas sobre el partido. Goles, eventos, rankings y comparaciones se responden por regla, con los datos y sin LLM. Lo demás va a Granite, con verificación de cifras. Costo medido: de 0.32 a 0.37 RU por pregunta; las respuestas registradas tardaron de 0.6 a 3.9 s |

### Gobernanza de la narración (monitor M3)

`implementacion/cloud_agent/governance_monitor_m3.py` audita cada llamada a Granite y la registra en `data/clean/governance_audit.jsonl`:

- Rechaza palabras que el sistema no mide: posesión, presión, dominio, velocidad, ataque, entre otras.
- Comprueba que cada número de la frase exista en los datos de ese tramo y pertenezca al equipo nombrado.
- Comprueba que el equipo al que la frase da más territorio coincida con los datos.
- Registra si se usó Granite o la plantilla, y avisa cuando una corrida con credenciales tuvo que usar plantillas.

En la última corrida, 2 de 8 frases son de Granite y 6 de la plantilla. Cuatro frases de Granite pasaban el monitor pero contradecían el video; se detectaron en la revisión humana y se reemplazaron, con el cambio anotado en la auditoría. Las reglas de M3 se están endureciendo para detectar esos casos de forma automática.

**Nota:** M3 es una auditoría propia, pensada para conectarse a watsonx.governance. Hoy no usa ese servicio.

## 4. Arquitectura del pipeline

```
ETAPA 1  Video → percepción
         roboflow/sports · YOLOv8 · ByteTrack · equipos por SigLIP + UMAP + KMeans
         Calibración por líneas de la cancha (homografía con RANSAC)
         → data/raw/{frames,objects}.parquet                       [Monitor M1]

ETAPA 2  Motor táctico (implementacion/cloud_tool/omnimorph_engine.py)
         Unión de rastros (algoritmo húngaro) · trayectorias Savitzky-Golay
         Tramos de 4.5 s · métricas por equipo · error del radar
         → data/clean/tactical_summaries.json                      [Monitores M2.0–M2.5]

ETAPA 3  Narración con IBM Granite (watsonx.ai) + auditoría
         → data/clean/narrations.json, governance_audit.jsonl      [Monitor M3]

ETAPA 4  Voz local (pyttsx3) + subtítulos + exportación a la web
         → data/audio/*.wav, dashboard/data/*.json                 [Monitor M4]

ETAPA 5  Orquestador (run_pipeline.py): corre todo y resume los 9 monitores
```

| Componente | Tecnología |
|---|---|
| Percepción | Python, `roboflow/sports`, YOLOv8 (Ultralytics), ByteTrack (`supervision`), SigLIP, UMAP, KMeans, OpenCV |
| Motor | `pandas`, `numpy`, `scipy` (algoritmo húngaro y Savitzky-Golay), `scikit-learn`, `pyarrow` |
| Lenguaje | IBM Granite `ibm/granite-4-h-small` en watsonx.ai (`ibm-watsonx-ai`) |
| Voz | Síntesis local con `pyttsx3`, sin enviar datos fuera de la computadora |
| Web | HTML, CSS y JavaScript sin framework; servidor en Python (`dashboard/serve.py`) con el chat |
| Credenciales | `python-dotenv` y `.env` |
| Pruebas | `scripts/probar_*.py`: chat (62 casos), métricas, crónica, radar y Transmisión |

**No se usan** LangChain, CrewAI ni otros frameworks de agentes: el narrador y el chat llaman a watsonx.ai directamente, y las reglas y verificaciones están en Python.

### Ejecución

Hoy todo corre en local: el pipeline en la computadora del equipo y la web en `http://localhost:8600`. El despliegue en IBM Cloud (Code Engine para el servidor y Cloud Object Storage para los videos) está planeado; el repositorio ya incluye `requirements-api.txt` para el contenedor. La herramienta táctica quedó preparada como herramienta OpenAPI para watsonx Orchestrate (`implementacion/cloud_tool/openapi_tool.yaml`), pero hoy no forma parte del flujo.

## 5. Calidad y verificación

| Monitor | Qué verifica | Última corrida |
|---|---|---|
| M1 | Dataset y percepción: cuadros, objetos y calibración por cuadro | PASS |
| M2.0 | Separación de rastros de jugadores y balón; equipo por moda | PASS |
| M2.1 | Calibración y error del radar (falla si la mediana supera 3 m; hoy 2.4 m) | PASS |
| M2.2 | Unión de rastros con el algoritmo húngaro | PASS |
| M2.3 | Cinemática Savitzky-Golay | PASS |
| M2.4 | Tramos tácticos de 4.5 s | PASS |
| M2.5 | Integridad del pipeline completo | PASS |
| M3 | Narración de Granite contra los datos | PASS, con aviso de plantillas |
| M4 | Sincronía de la voz y los datos de la web | PASS |

## 6. Seguridad y reglas del repositorio

- Ninguna llave, token ni contraseña en el código ni en `bob_sessions/`. Las exportaciones de Bob se revisaron antes de subirlas.
- `.env`, videos (`.mp4`), pesos de modelos (`.pt`, `.pth`), datos crudos pesados, `.venv/` y `.hf_cache/` están fuera de Git (`.gitignore`, `AGENTS.md` §3).
- Las reglas del proyecto para cualquier agente están en `AGENTS.md`.
