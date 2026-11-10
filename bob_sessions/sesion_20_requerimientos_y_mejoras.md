# Sesión 20 — Auditoría de requerimientos y plan de mejora

**Fecha:** 2026-11-10 · **Agente:** IBM Bob (modo Plan) · **Rama:** feat-costa-rica
**Documentos del programa usados:** ninguno adjunto — requerimientos del programa tomados de la sesión 05 (`sesion_05_deploy_orchestrate_github.md`, tabla "Reglas del IBM SkillsBuild AI Experiential Learning Lab aplicadas"). Cualquier regla adicional del programa (capturas de consumo, duración del video de demo, entregables finales, fechas) se trata como **Sugerida** hasta que se adjunten las bases.

---

## 1. Resumen ejecutivo

El pipeline corre 9/9 PASS en 25,94 s con Costa Rica como partido activo. El tablero web tiene cinco páginas funcionales (Inicio, MATEO, Partido, Método, loaders) y el chatbot opera en modo solo-clip. Los datos del partido (`procedencia.validado: false`) y los 13 rastros identificados a mano siguen sin validar: es el bloqueo más importante antes de la demo. El hallazgo crítico de esta auditoría es que `SYSTEM_PROMPT` de `chat_agent.py` tiene escrito a mano "Brasil 1-7 Alemania (semifinal del Mundial 2014)" aunque el partido activo sea Costa Rica — el chatbot lleva el encabezado equivocado. La homografía de la cámara de TV no está corregida (velocidades ocultas), pero es trabajo de fondo que no debe tocarse antes de la demo.

---

## 2. Requerimientos

| ID | Requerimiento | Fuente | Tipo |
|---|---|---|---|
| R01 | IBM Bob IDE es el entorno de desarrollo obligatorio y los reportes se exportan a `bob_sessions/` | `sesion_05`, tabla reglas; `bob_sessions/README.md` intro | Obligatorio del programa |
| R02 | Usar IBM watsonx.ai con modelos IBM Granite (`ibm/granite-4-h-small` o `ibm/granite-3-8b-instruct`) | `AGENTS.md §1`; `sesion_05`, tabla reglas | Obligatorio del programa + Regla del proyecto |
| R03 | Prohibido usar modelos de terceros (gpt-\*, claude-\*, llama-\*, mistral-\*) | `AGENTS.md §1` | Regla del proyecto (más estricta que el programa) |
| R04 | Despliegue 100 % local — la llamada a watsonx.ai es un servicio IBM exigido, no un incumplimiento | `sesion_05`, tabla reglas | Obligatorio del programa |
| R05 | Sin datos confidenciales ni PII en el repositorio | `sesion_05`, tabla reglas; `AGENTS.md §2 y §3` | Obligatorio del programa |
| R06 | Cero API keys en código fuente — solo en `.env` | `AGENTS.md §2` | Regla del proyecto |
| R07 | Archivos prohibidos en Git: `.env`, `.mp4`, `.pt`/`.pth`, parquets en `data/raw/`, `.venv/`, `.hf_cache/` | `AGENTS.md §3` | Regla del proyecto |
| R08 | Bitácora de sesiones: cada agente registra su sesión en `bob_sessions/` y actualiza `README.md` | `AGENTS.md §8 B` | Regla del proyecto |
| R09 | Monitores M1, M2.0–M2.5, M3 y M4 deben ejecutarse y reportar su estado | `AGENTS.md §5` | Regla del proyecto |
| R10 | IBM watsonx Orchestrate — herramienta táctica publicada como endpoint OpenAPI | `sesion_05`, tabla reglas ("opcional") | Obligatorio del programa (opcional) |
| R11 | Pipeline funcional de extremo a extremo: dataset → percepción → motor → narrador → TTS → tablero | `AGENTS.md §4`; `sesion_04`, objetivo | Funcional |
| R12 | Partido activo configurable sin cambiar código — `partido_activo.json` o variable `OMNIMORPH_PARTIDO` | `sesion_10`, sesion_12 | Funcional |
| R13 | Tablero web: página Inicio con hero, tiles y franja IBM | `sesion_dashboard` (sesion_06) | Funcional |
| R14 | Tablero web: página MATEO con video, radar, crónica, transcripción y chatbot | `sesion_06`; `sesion_13` | Funcional |
| R15 | Tablero web: página Partido con ficha, fichero, comparativa, goles y aviso "por validar" | `sesion_08`; `sesion_17` | Funcional |
| R16 | Tablero web: página Método con flujo, monitores, niveles de confianza, límites y gobernanza | `sesion_18`; `sesion_19` | Funcional |
| R17 | Chatbot habla del partido activo, no de un partido hardcodeado | `sesion_10`, §chatbot | Funcional |
| R18 | `metodo.json` se actualiza automáticamente desde los monitores de la última corrida | `sesion_19`, §export_metodo | Funcional |
| R19 | Videos, radar y audio duran el mismo tiempo (sincronización) | `sesion_13`, §bug fps; Monitor M4 | No funcional |
| R20 | Página responsive: sin scroll horizontal en 375 px | `sesion_09`; `sesion_17`; `sesion_19` | No funcional |
| R21 | Sin API keys ni credenciales en los archivos exportados a `bob_sessions/` | `AGENTS.md §2`; `bob_sessions/README.md` seguridad | No funcional |
| R22 | Trazabilidad: registro de cada llamada LLM en `governance_audit.jsonl` y `chat_audit.jsonl` | `sesion_04`; `AGENTS.md §5 M3` | No funcional |
| R23 | Plan B para la demo si falla la red o watsonx | Implícito en R04 (local) | No funcional |
| R24 | Brasil-Alemania se conserva como referencia y partido de regresión; no se borra | Instrucción del usuario en esta sesión | Funcional |
| R25 | Datos del partido (marcador, alineaciones, goles) validados por una persona del equipo | `sesion_17`, campo `validado`; `sesion_14` | Expectativa del usuario final |
| R26 | Dorsales de jugadores en el tablero MATEO validados por una persona del equipo | `sesion_16`, §pendiente; `sesion_19`, §pendiente | Expectativa del usuario final |
| R27 | Velocidades por jugador creíbles en el video y en MATEO | `sesion_13`, §6 riesgo; `sesion_12`, §velocidades | Expectativa del usuario final |
| R28 | El chatbot responde con los datos del partido activo, no de otro partido | `sesion_13`, §chatbot modo solo-clip | Expectativa del usuario final |

### Sugeridos (sin fuente verificada)

| ID | Sugerencia | Por qué |
|---|---|---|
| S01 | Capturas de pantalla de consumo de RU en watsonx adjuntas al repositorio final | Podría ser requerimiento del programa; no aparece en la sesión 05 |
| S02 | Video de demo de duración acotada (p. ej. ≤ 3 min) | Podría ser requerimiento del programa; no aparece en la sesión 05 |
| S03 | `.bobignore` configurado | Mencionado en docs de IBM Bob; no citado en fuentes del repo |
| S04 | Entregables finales en rama `main` (no en `feat-*`) | Buena práctica; no hay regla explícita en las fuentes revisadas |
| S05 | Identificación automática de dorsales con modelo propio o Granite Vision | `sesion_15`; no hay requerimiento explícito, es mejora de fondo |
| S06 | Chatbot con datos completos del partido (activar `chat_datos_completos: true`) | Depende de R25; no hay plazo en ninguna fuente |

---

## 3. Cumplimiento

| ID | Requerimiento | Estado | Evidencia | Qué falta |
|---|---|---|---|---|
| R01 | IBM Bob IDE obligatorio + `bob_sessions/` | **Cumple** | 20 sesiones en `bob_sessions/`; `README.md` actualizado hasta sesión 19 | Agregar fila 20 (esta sesión) |
| R02 | IBM watsonx.ai + modelos Granite | **Cumple** | `monitor_m3.json`: `"model_used": "ibm/granite-4-h-small"`, 8/8 PASS | — |
| R03 | Sin modelos de terceros | **Cumple** | Grep en `implementacion/`: ninguna importación de `openai`, `anthropic`, `llama` ni `mistral` | — |
| R04 | Despliegue 100 % local | **Cumple** | Pipeline y tablero corren en `localhost:8600`; única red externa: watsonx.ai (IBM) | — |
| R05 | Sin PII ni datos confidenciales | **Cumple** | Dataset público HF; alineaciones y nombres de futbolistas son públicos; `.env` en `.gitignore` | — |
| R06 | Cero API keys en código | **Cumple** | Grep en `implementacion/*.py`: no hay literales de clave; todas las credenciales vienen de `os.environ` o `.env` | — |
| R07 | Archivos prohibidos en `.gitignore` | **Cumple** | `.gitignore` cubre: `.env`, `*.mp4`, `*.pt`, `*.pth`, `data/raw/*.parquet`, `.venv/`, `.hf_cache/` | `data/clean/*.parquet` no está en `.gitignore` — los parquets de `clean` sí se versionan; no viola la regla (que solo prohíbe los de `data/raw/`) |
| R08 | Bitácora de sesiones | **Cumple parcialmente** | 19 sesiones documentadas; fila 20 pendiente de esta auditoría | Agregar fila 20 |
| R09 | Monitores M1–M4 | **Cumple** | `pipeline_summary.json`: `"all_pass": true`, 9/9; `monitor_m1–m4.json` presentes y fechados 2026-11-09 | — |
| R10 | watsonx Orchestrate (opcional) | **Cumple parcialmente** | `openapi_tool.yaml` y `api_server.py` listos (`sesion_05`); pendiente importar en Orchestrate | Importar el YAML en el panel de Orchestrate antes de la demo (si se quiere demostrar en vivo) |
| R11 | Pipeline extremo a extremo | **Cumple** | `pipeline_summary.json`: 9/9 PASS en 25,94 s; `data/clean/` con todos los artefactos | — |
| R12 | Partido activo configurable | **Cumple** | `partido_activo.json` → `costa_rica_skn_eliminatorias_2026`; `partido_config.py` usa env-var con prioridad | — |
| R13 | Página Inicio | **Cumple** | `index.html` verificado; nav incluye "Método" (cambio externo confirmado) | — |
| R14 | Página MATEO | **Cumple** | `mateo.html` verificado en `sesion_13` a 36,04 s | — |
| R15 | Página Partido | **Cumple** | `partido.html` + `partido.js` genéricos; aviso "por validar" activo (`validado: false`) | — |
| R16 | Página Método | **Cumple** | `metodo.html` + `metodo.js` + `metodo.json` presentes; cifras reales (1 080 cuadros, 1 588 ms, 0,60 RU) | — |
| R17 | Chatbot habla del partido activo | **No cumple** | `chat_agent.py` línea 58: `SYSTEM_PROMPT` tiene escrito a mano `"Brasil 1-7 Alemania (semifinal del Mundial 2014)"`. El chatbot ya inyecta los datos de Costa Rica en `{contexto}`, pero el **encabezado del sistema** sigue nombrando Brasil — confundirá a quien lo lea en la demo | Reemplazar la frase fija por el título dinámico del partido activo usando `partido_config.activo().titulo` |
| R18 | `metodo.json` actualizado automáticamente | **Cumple** | `export_metodo()` en `export_dashboard_data.py`; campo `coincide_partido: true` en `metodo.json` | — |
| R19 | Sincronización de videos y audio | **Cumple** | M4: desfase máximo 19,02 ms (límite 40 ms); bug de fps corregido en `sesion_13` | — |
| R20 | Responsivo 375 px | **Cumple** | Verificado en `sesion_17` y `sesion_19` (0 scroll horizontal) | — |
| R21 | Sin credenciales en `bob_sessions/` | **Cumple** | `README.md` seguridad lo confirma; ninguna sesión contiene literales de clave | — |
| R22 | Trazabilidad LLM | **Cumple** | `governance_audit.jsonl` y `chat_audit.jsonl` presentes en `data/clean/` | `chat_audit.jsonl` está en `.gitignore` (`data/clean/chat_audit.jsonl`); el log no se versiona. No viola ninguna regla: es un archivo de auditoría local | — |
| R23 | Plan B para la demo | **No verificable** | No hay script ni documento de contingencia offline | Ver plan de mejora M-B01 |
| R24 | Brasil conservado como referencia | **Cumple** | `data/partidos/brasil_alemania_2014/` presente; `partido_activo.json` apunta a Costa Rica; `sesion_13 §6.3` documenta el hallazgo de inversión de equipos pendiente de verificar | Verificar si los equipos de Brasil están invertidos antes de usarlo como demo de regresión |
| R25 | Datos del partido validados | **No cumple** | `metodo.json`: `"datos_validados": false`; `partido.json`: `"validado": false`; aviso "por validar" activo en el tablero | Una persona del equipo debe revisar `PLANTILLA_datos_partido.xlsx` y crear `contexto_partido.json` validado |
| R26 | Dorsales validados | **No cumple** | `metodo.json`: `"dorsales.validado": false`; 10 jugadores en 13 rastros como borrador | Fer debe revisar `rastros_dorsales_borrador.json` y crear `rastros_dorsales.json` |
| R27 | Velocidades creíbles | **Parcial** | Velocidades ocultas en el tablero y en los videos (decisión de `sesion_13 §6.2`); `data/clean/monitor_m2.json` M2.3: `v_max_clipped_mps: 9.5`, mediana real ~10 m/s | Corrección de la homografía: trabajo de fondo, no para antes de la demo |
| R28 | Chatbot con datos de Costa Rica | **Parcial** | El contexto `{contexto}` sí incluye datos de Costa Rica; pero `SYSTEM_PROMPT` nombra Brasil (R17). El chatbot opera en modo solo-clip porque `chat_datos_completos: false` en la config | Corregir R17; R25 y R26 desbloquean `chat_datos_completos: true` |

---

## 4. Plan de mejora priorizado

### Antes de la demo

#### M-A01 · Corregir el encabezado del chatbot (R17, R28)
- **Qué es:** `SYSTEM_PROMPT` en `implementacion/cloud_agent/chat_agent.py` tiene el texto `"Brasil 1-7 Alemania (semifinal del Mundial 2014)"` escrito a mano. El cuerpo técnico que abre el chat en la demo lo verá de inmediato.
- **Archivos:** `implementacion/cloud_agent/chat_agent.py` línea 58.
- **Cambio mínimo:** sustituir la frase fija de Brasil por `{partido_titulo}` y formatearlo al inicio con `partido_config.activo().titulo`. El resto del prompt no cambia.
- **Esfuerzo:** 1 h · **Riesgo:** Mínimo (cambio de texto; el contexto `{contexto}` ya funciona con Costa Rica).
- **Verificación:** iniciar el chatbot con Costa Rica activo y comprobar que el mensaje del sistema no contiene "Brasil".
- **Asignado a:** Claude Code.

#### M-A02 · Validar los datos del partido (R25, R28)
- **Qué es:** `procedencia.validado` es `false`. El tablero muestra el aviso amarillo y la página Método dice "Todavía nada" en la fila "Verificado". Para la demo con un club profesional, al menos el marcador, los goles y los árbitros deben estar confirmados.
- **Archivos:** `data/partidos/costa_rica_skn_eliminatorias_2026/partido/contexto_partido.json` → cambiar `procedencia.validado: true` después de revisar contra fuentes citadas; volver a exportar con `scripts/export_dashboard_data.py --solo-partido`.
- **Esfuerzo:** 1–2 h de revisión humana · **Riesgo:** Ninguno para el pipeline.
- **Verificación:** aviso amarillo desaparece del tablero; página Método muestra "Verificado: Ficha, alineaciones, estadísticas y goles del partido."
- **Asignado a:** Persona del equipo (Fer).

#### M-A03 · Validar los dorsales (R26)
- **Qué es:** `rastros_dorsales_borrador.json` tiene 10 jugadores en 13 rastros, marcados `"validado": false`. En el tablero MATEO aparece la etiqueta naranja "POR VALIDAR" junto a cada nombre.
- **Archivos:** revisar `outputs/experimentos/dorsales/revision_manual/rastros_1.jpg` a `rastros_4.jpg` (fuera de Git); si son correctos, crear `data/partidos/costa_rica_skn_eliminatorias_2026/rastros_dorsales.json` (sin la clave `validado: false`); volver a exportar con `scripts/export_dashboard_data.py`.
- **Esfuerzo:** 30 min de revisión visual · **Riesgo:** Ninguno para el pipeline.
- **Verificación:** etiqueta "POR VALIDAR" desaparece de los nombres confirmados en MATEO.
- **Asignado a:** Persona del equipo (Fer) + Claude Code para el script de exportación.

#### M-A04 · Plan B offline para la demo (R23)
- **Qué es:** si falla la red o watsonx durante la demo, el chatbot no responde y las narraciones no se generan. El pipeline ya guarda `narrations.json` y los 8 WAV: la demo puede continuar sin conexión si el tablero está pre-exportado.
- **Archivos:** no requiere cambios de código. Solo preparar:
  1. Verificar que `dashboard/data/` esté exportado antes de la demo (`export_dashboard_data.py`).
  2. Tener `data/audio/W0–W7.wav` generados.
  3. Saber cómo responder si el chat falla ("el chatbot usa IA en la nube; si no hay red, las respuestas están en la página Partido").
- **Esfuerzo:** 30 min · **Riesgo:** Sin riesgo (solo preparación).
- **Verificación:** el tablero funciona completo (video, radar, narración, partido) sin conexión a internet, excepto el chat en vivo.
- **Asignado a:** Persona del equipo.

#### M-A05 · Verificar la inversión de equipos en Brasil (R24)
- **Qué es:** `sesion_13 §6.3` documenta que al renderizar Brasil, los jugadores de amarillo salen con `team_id 1` y los de blanco con `team_id 0`, al revés de la configuración. No afecta a la demo de Costa Rica, pero si se quiere demostrar Brasil como referencia habrá confusión.
- **Archivos:** `data/partidos/brasil_alemania_2014/partido.config.json` — verificar visualmente el video renderizado y, si se confirma, intercambiar los `team_id`.
- **Esfuerzo:** 30 min · **Riesgo:** Bajo (solo afecta al partido de referencia).
- **Verificación:** el color naranja/amarillo coincide con Brasil en el video de marcas.
- **Asignado a:** Claude Code (verificación visual) + Persona del equipo (confirmación).

#### M-A06 · Unir los rastros partidos identificados (R26, R27 — mejora de presentación)
- **Qué es:** T12→T59, T2→T74 y T18→T70 son el mismo jugador en dos tramos. En MATEO aparecen dos veces. No rompe el pipeline, pero ante un director deportivo parece un error.
- **Archivos:** `data/partidos/costa_rica_skn_eliminatorias_2026/rastros_dorsales_borrador.json` — agregar el campo `fusionar_con` o similar; adaptar `export_dashboard_data.py` para que los trate como un solo rastro en `mateo_data.json`.
- **Esfuerzo:** 2–3 h · **Riesgo:** Bajo, solo afecta a la presentación en MATEO, no al pipeline.
- **Verificación:** Madrigal aparece una sola vez, Ugalde una sola vez, Lassiter una sola vez en la lista de MATEO.
- **Asignado a:** Claude Code.

---

### Después de la demo

#### M-D01 · Corrección de la homografía (R27)
- **Qué es:** la causa del ruido de velocidades. La cámara de TV produce saltos en la homografía que hacen parecer que los jugadores se mueven a 10 m/s sin moverse. El diagnóstico está en `sesion_13 §6.1`: la variante "conf ≥ 0.5 + H suavizada 15 cuadros + SG 31" baja la mediana a 5,3 m/s; ninguna variante llega a una mediana creíble de 1,5–3 m/s.
- **Archivos:** `implementacion/cloud_tool/omnimorph_engine.py` (fases 2 y 4).
- **Esfuerzo:** 4–8 h de experimentación · **Riesgo:** Alto (toca el motor completo; requiere corrida del pipeline para verificar).
- **Verificación:** mediana de `v_mps` ≤ 4 m/s en `objects_cleaned.parquet`; M2.3 sigue en PASS; no aparecen "9,5 m/s" en el tablero.
- **Asignado a:** Claude Code (prototipo en rama aislada) + Bob (análisis de variantes).

#### M-D02 · Activar chatbot con datos completos (R28, S06)
- **Qué es:** cuando R25 y R26 estén completos, cambiar `chat_datos_completos: true` en `partido.config.json` de Costa Rica. Esto habilita el verificador de atribución, las reglas de datos y el contexto completo del partido en el chatbot.
- **Archivos:** `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json`; `implementacion/cloud_agent/chat_agent.py` (selección de prompt).
- **Esfuerzo:** 1–2 h · **Riesgo:** Bajo (el mecanismo ya existe para Brasil).
- **Verificación:** el chatbot responde a "¿cómo quedó el marcador?" con "4-0" sin el aviso de que no tiene ese dato.
- **Asignado a:** Claude Code (después de R25 y R26).

#### M-D03 · Identificación automática de dorsales (S05)
- **Qué es:** el modelo YOLOv8n-cls tiene 0 % de cobertura en transmisión de TV (sesión 15). Opciones: Granite Vision local (Apache 2.0, Hugging Face), reentrenar con recortes propios etiquetados por Fer, o un pipeline de recorte + OCR clásico.
- **Archivos:** nueva carpeta `implementacion/dorsales/` (no existe).
- **Esfuerzo:** 8–16 h de experimentación · **Riesgo:** Investigación abierta; resultado incierto.
- **Verificación:** cobertura ≥ 50 % en los 20 rastros principales del clip de Costa Rica.
- **Asignado a:** Bob (experimento) + Persona del equipo (validación del ground truth).

#### M-D04 · Entregables finales del programa (S04)
- **Qué es:** fusionar `feat-costa-rica` + `feat-dashboard-mejoras` a `main`, limpiar ramas antiguas, añadir capturas de consumo de RU, preparar el video de demo y revisar `.bobignore`.
- **Archivos:** ramas Git, `bob_sessions/`, capturas de pantalla.
- **Esfuerzo:** 2–3 h · **Riesgo:** Ninguno si se hace en rama aislada primero.
- **Verificación:** `main` corre el pipeline 9/9 PASS; el README final está actualizado.
- **Asignado a:** Persona del equipo + Claude Code.

#### M-D05 · Importar la herramienta en watsonx Orchestrate (R10)
- **Qué es:** `openapi_tool.yaml` está lista desde la sesión 05, pero no se completó la importación en el panel de Orchestrate.
- **Archivos:** `implementacion/cloud_tool/openapi_tool.yaml`; `implementacion/cloud_tool/launch_ngrok.py`.
- **Esfuerzo:** 1–2 h · **Riesgo:** Requiere red y acceso al panel de Orchestrate.
- **Verificación:** el endpoint `/process` aparece como herramienta disponible en el agente de Orchestrate.
- **Asignado a:** Persona del equipo.

---

## 5. Riesgos para la demo

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| El chatbot muestra "Brasil 1-7 Alemania" en el encabezado del sistema (R17) | Alta — ya confirmado | Alto — quita credibilidad ante el club | M-A01 (corrección de 1 h) |
| Los datos del partido siguen marcados "por validar" en el tablero | Alta — `validado: false` confirmado | Medio — el club verá el aviso amarillo | M-A02 (revisión humana de 1–2 h) |
| La red falla durante la demo o watsonx tiene latencia alta | Media | Alto si no hay plan B | M-A04 (pre-exportar todo el tablero) |
| Los dorsales "POR VALIDAR" en MATEO generan dudas sobre la calidad del sistema | Alta — confirmado | Medio | M-A03 (30 min de revisión) |
| Un mismo jugador aparece con dos IDs en MATEO (rastros partidos) | Alta — T12/T59, T2/T74, T18/T70 confirmados | Medio — parece un error ante el director deportivo | M-A06 (2–3 h de desarrollo) |
| Brasil aparece en el comercial con equipos invertidos | Baja — solo si se usa Brasil en la demo | Bajo — solo afecta al clip de referencia del comercial | M-A05 (verificar en 30 min) |
| La página Método cita "Orchestrate activo" y Orchestrate no está importado | Baja — el texto actual dice "se integró y probó durante el desarrollo" | Bajo | El texto actual es correcto; no exagera |
| El audio TTS suena robótico o con artefactos en el sistema de la sala | Media | Medio | Probar `pyttsx3` en el sistema de la sala antes de la presentación |

---

## 6. Revisión de Claude Code (2026-11-09)

Se contrastaron los hallazgos con el código. La estructura y el plan sirven. Hay que corregir lo siguiente:

| Bob dijo | Comprobación |
|---|---|
| **R17 "No cumple" / riesgo alto: el chatbot muestra "Brasil 1-7 Alemania"** | **Ya corregido en la copia de trabajo, pero sin commit cuando Bob auditó.** El riesgo era real en el commit anterior: como Gemini creó `contexto_partido.json` para Costa Rica, el chat habría pasado al modo completo con el `SYSTEM_PROMPT` de Brasil. La protección `chat_datos_completos` (commit `9cd476f`) lo evita. Con Costa Rica, `cargar_datos()` devuelve `solo_clip`, y `construir_mensajes()` usa `SYSTEM_PROMPT_CLIP` con el título del partido activo. El prompt se arma en el servidor y no se ve en DevTools. Queda Brasil solo en el docstring de la línea 4. R17 → **Cumple** desde `9cd476f`. R28 → **Parcial**, solo por R25. |
| Rama `feat-dashboard-mejoras` | La rama es `feat-costa-rica` (corregido en el encabezado). |
| R07: "los parquets de `data/clean` se versionan" | `data/clean/` no está en Git (`git ls-files data/clean` está vacío). |
| M-A02: "crear `contexto_partido.json` validado" | El archivo ya existe (sesión 17). Después de que Fer lo revise, basta con cambiar `procedencia.validado` a `true` y volver a exportar. |
| M-A06: agregar `fusionar_con` al borrador | No hace falta: el borrador ya agrupa los tramos (`[12, 59]`, `[2, 74]`, `[18, 70]`). Falta que `export_dashboard_data.py` fusione en un solo jugador los rastros asignados a la misma persona. Se estima en 1–2 h. |

**Plan antes de la demo, ajustado:**
- M-A01 queda resuelta por `9cd476f`. Solo falta cambiar el docstring, que es cosmético.
- Quedan como prioridades M-A02 y M-A03 (Fer), M-A04 (plan B) y M-A06 (fusión de rastros en el exportador).
