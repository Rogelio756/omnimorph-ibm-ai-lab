# bob_sessions — Reportes de Sesiones IBM Bob IDE

Esta carpeta contiene los reportes Markdown de cada sesion de desarrollo
realizada con **IBM Bob IDE** para el proyecto **Omnimorph**.

Requerimiento del IBM SkillsBuild AI Experiential Learning Lab:
> "Es obligatorio exportar e incluir la carpeta `bob_sessions` con los
> reportes Markdown de las sesiones de tareas y capturas de pantalla
> en el repositorio final."

---

## Sesiones documentadas

| Archivo | Fecha | Descripcion |
|---|---|---|
| `sesion_01_evaluacion_inicial.md` | 2026-10-08 | Evaluacion del repositorio `roboflow/sports` — 6 modos de percepcion, diagnóstico de compatibilidad |
| `sesion_02_pipeline_unificado.md` | 2026-10-13 | Experimento A/B/C/C2 — pipeline unificado `-43%` mas rapido, generacion de parquets |
| `sesion_03_arquitectura_accesibilidad.md` | 2026-10-15 | Arquitectura formal + analisis `worldcupvoice` + prompt accesibilidad visual (frame 300) |
| `sesion_04_pipeline_omnimorph_9monitores.md` | 2026-11-02 | Implementacion completa Etapas 1-5 + 9 monitores PASS + `ibm/granite-4-h-small` online |
| `sesion_05_deploy_orchestrate_github.md` | 2026-11-04 | FastAPI + IBM watsonx Orchestrate + GitHub + bob_sessions |
| `sesion_06_mateo_dashboard.md` | 2026-11-04 | Dashboard MATEO en paralelo H.264, radar 2D independiente y audio TTS 60s |
| `sesion_dashboard_omnimorph_2026-11-04.md` | 2026-11-04 | Construcción de la capa visual en `dashboard/`: sistema de diseño, páginas HTML y componentes CSS |
| `sesion_07_arquitectura_hibrida_y_the_architect.md` | 2026-11-04 | Análisis híbrido (Fernando Maciel), repo Brasil-Alemania, The Architect y ramas Git |
| `sesion_08_auditoria_y_migracion_brasil_alemania.md` | 2026-11-04 | Auditoría del repo, migración corregida de datos, página de análisis y chatbot con Granite |
| `sesion_09_visual_chat_flotante_y_fichero.md` | 2026-11-04 | Mejora visual, transiciones, audio de MATEO, chat flotante, fichero de jugadores y hallazgo de identificadores repetidos |
| `sesion_10_cambio_a_costa_rica_y_partido_configurable.md` | 2026-11-09 | Elección del clip de Costa Rica vs. San Cristóbal y Nieves por cortes de cámara, reparto entre agentes y partido configurable en engine, narrador, M3 y chatbot |
| `sesion_11_percepcion_costa_rica_gemini.md` | 2026-11-09 | Ejecución de los 6 modelos de percepción sobre Costa Rica vs. San Cristóbal y Nieves (clip 15, 1080 frames), parametrización de etiquetas en scripts y verificación cuantitativa (Gemini) |
| `sesion_12_costa_rica_activo_pipeline.md` | 2026-11-09 | Revisión de la percepción de Gemini, Costa Rica como partido activo y pipeline 9/9 con Granite real |
| `sesion_13_dashboard_web_costa_rica.md` | 2026-11-09 | Dashboard web con Costa Rica, corrección de fps en videos, página Partido en preparación, chatbot en modo solo clip, sección del comercial junto a los logos de IBM y diagnóstico del ruido de velocidad |
| `sesion_14_datos_partido_gemini.md` | 2026-11-09 | Investigación y llenado completo de `PLANTILLA_datos_partido.xlsx` (Ficha, Alineaciones, Estadísticas, Eventos y 15 Fuentes públicas) para Costa Rica vs. San Cristóbal y Nieves (Gemini) |
| `sesion_15_dorsales_bob.md` | 2026-11-10 | Experimento de reconocimiento de dorsales con dataset de Roboflow (4,114 imgs, CC BY 4.0). YOLOv8n-cls: 84.3 % original / 69.2 % degradado. Cobertura en clip TV 720p: 0/20 rastros. Conclusión: no sirve en transmisión TV; propuesta IBM Granite Vision (IBM Bob) |

---

## Tecnologias IBM utilizadas

| Tecnologia | Uso |
|---|---|
| **IBM Bob IDE** | Entorno central de desarrollo — todas las sesiones |
| **IBM watsonx.ai** | Narracion tactica con `ibm/granite-4-h-small` (Monitor M3) |
| **IBM watsonx Orchestrate** | Orquestacion de herramientas via OpenAPI (trial activo) |
| **IBM Granite** | Modelo `ibm/granite-4-h-small` — generacion de narraciones en espanol |

---

## Resultado final del pipeline

```
run_pipeline.py --use-real  →  9/9 monitores PASS en 63.1 s
Dataset: Brasil vs. Alemania, Semifinal Mundial FIFA 2014 (1800 frames, 60 s)
Modelo LLM: ibm/granite-4-h-small (0.5287 RU, latencia media 1170 ms)
```

---

## Seguridad

Estos reportes NO contienen credenciales, API keys, tokens ni informacion sensible.
El archivo `.env` con las credenciales reales esta en `.gitignore` y nunca se sube al repositorio.
