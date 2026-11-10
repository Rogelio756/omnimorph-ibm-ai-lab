# Estado actual de Omnimorph — 10 de noviembre de 2026

**Rama activa:** `feat-costa-rica`  
**Generado por:** IBM Bob (modo Plan) · Sesión 23  
**Propósito:** Documento de situación para compartir con el equipo. No propone cambios; solo describe lo que existe hoy.  
**Audience:** Personas del equipo que no son desarrolladores.

---

## 1. ¿Qué es Omnimorph?

Omnimorph es un sistema que toma un video de fútbol, detecta a los jugadores y al balón cuadro a cuadro, calcula métricas tácticas y genera —con inteligencia artificial de IBM— una crónica narrada en español que se sincroniza con el video en un tablero web.

El sistema se construyó como proyecto de un laboratorio de IBM (IBM SkillsBuild AI Experiential Learning Lab). Toda la computación corre en la computadora del equipo; la única conexión a internet que se necesita es para que IBM Granite genere el texto de la narración.

---

## 2. Partido activo

| Campo | Valor |
|---|---|
| **Partido** | Costa Rica vs. San Cristóbal y Nieves |
| **Competición** | Eliminatorias Concacaf — Segunda ronda, Grupo B, Jornada 1 |
| **Fecha del partido** | 6 de junio de 2024 |
| **Estadio** | Estadio Nacional de Costa Rica, San José |
| **Resultado** | Costa Rica 4 – 0 San Cristóbal y Nieves |
| **Clip analizado** | 36 segundos (1 080 cuadros a 29,97 fps) de un plano táctico continuo |
| **Datos validados** | ❌ Pendiente de revisión por una persona del equipo (Fer) |

El sistema también conserva el partido Brasil vs. Alemania 2014 como referencia histórica. Se puede alternar entre los dos partidos con un solo archivo de configuración.

---

## 3. Arquitectura: cómo fluye la información

```
┌─────────────────────────────────────────────────────────────────────┐
│  VIDEO DE ENTRADA                                                   │
│  HP3zxNuoWXE-720-15.mp4  (36 s · 1 080 cuadros · 720 p)           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 1 — PERCEPCIÓN  (Monitor M1)                                 │
│  dataset_manager.py                                                  │
│  • Detecta jugadores (112 rastros) y balón (860 detecciones)        │
│  • Calcula la transformación de pantalla a cancha real (homografía) │
│  • Guarda: data/raw/frames.parquet, data/raw/objects.parquet        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 2 — MOTOR OMNIMORPH  (Monitores M2.0 – M2.5)                │
│  omnimorph_engine.py                                                 │
│  • Separa jugadores de balón y asigna equipo a cada uno             │
│  • Suaviza los movimientos (elimina saltos bruscos)                 │
│  • Une rastros partidos con el algoritmo húngaro (112 → 93 rastros) │
│  • Limita la velocidad máxima a 9,5 m/s (tope físico)              │
│  • Divide el partido en 8 ventanas tácticas de ~4,5 s cada una     │
│  • Guarda: data/clean/objects_cleaned.parquet,                      │
│            data/clean/tactical_summaries.json                        │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 3 — NARRADOR GRANITE  (Monitor M3)                           │
│  agent_narrator.py + governance_monitor_m3.py                       │
│  • Envía cada ventana táctica a IBM Granite (ibm/granite-4-h-small) │
│  • Obtiene una narración en español de hasta 45 palabras            │
│  • Verifica que el modelo sea IBM Granite (nunca otro)              │
│  • Registra cada llamada en governance_audit.jsonl                  │
│  • Guarda: data/clean/narrations.json, data/clean/narrations_es.vtt │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 4 — VOZ Y TABLERO  (Monitor M4)                              │
│  tts_service.py + dashboard/serve.py                                │
│  • Convierte el texto a audio con la voz del sistema (Windows SAPI) │
│  • Genera 8 clips de audio (W0.wav … W7.wav, máx. 3,9 s cada uno)  │
│  • Verifica que el audio y el video estén sincronizados (< 40 ms)  │
│  • Sirve el tablero web en http://localhost:8600                    │
└─────────────────────────────────────────────────────────────────────┘
```

El orquestador `run_pipeline.py` ejecuta las cinco etapas de punta a punta y muestra un resumen de los 9 monitores al final.

---

## 4. Stack y dependencias

El proyecto corre en **Python 3.10 o superior** en Windows.

| Paquete | Para qué se usa |
|---|---|
| `pandas` / `pyarrow` | Tablas de datos (frames, objetos, métricas) |
| `numpy` / `scipy` | Cálculos de velocidad y suavizado de movimientos |
| `scikit-learn` | Agrupación de jugadores por equipo |
| `ibm-watsonx-ai 1.8.1` | Conexión con IBM Granite para las narraciones |
| `python-dotenv` | Lee las credenciales desde el archivo `.env` sin escribirlas en el código |
| `pyttsx3` | Motor de texto a voz local (Windows SAPI) |
| `fastapi` / `uvicorn` | Servidor de la herramienta táctica (OpenAPI para Orchestrate) |
| `streamlit` | Prototipo de tablero alternativo (no es el tablero principal) |

El tablero web principal (`dashboard/serve.py`) usa solo la biblioteca estándar de Python y no necesita nada instalado aparte de `ibm-watsonx-ai`, `python-dotenv` y `pandas` para funcionar.

---

## 5. Mapa de carpetas y archivos clave

```
omnimorph-pruebas/
│
├── run_pipeline.py             ← Orquestador: ejecuta las 5 etapas y los 9 monitores
├── AGENTS.md                   ← Reglas del proyecto para todos los agentes
├── data/
│   ├── partidos/
│   │   ├── partido_activo.json         ← Dice qué partido está activo (Costa Rica)
│   │   ├── costa_rica_skn_eliminatorias_2026/
│   │   │   ├── partido.config.json     ← Config del partido: equipos, video, modelo
│   │   │   ├── partido/                ← Datos del partido (ficha, goles, alineaciones)
│   │   │   └── rastros_dorsales_borrador.json  ← Dorsales a mano, pendiente validar
│   │   └── brasil_alemania_2014/       ← Partido de referencia histórica
│   ├── raw/                    ← Parquets de la percepción (no están en Git)
│   ├── clean/                  ← Resultados del motor + narraciones + auditorías
│   │   ├── pipeline_summary.json       ← Resultado de la última corrida (9/9 PASS)
│   │   ├── monitor_m1.json             ← Resultado del Monitor M1
│   │   ├── monitor_m2.json             ← Resultado de los Monitores M2.0–M2.5
│   │   ├── monitor_m3.json             ← Resultado del Monitor M3 (Granite)
│   │   ├── monitor_m4.json             ← Resultado del Monitor M4 (TTS y sincronía)
│   │   ├── narrations.json             ← 8 narraciones generadas por Granite
│   │   └── governance_audit.jsonl      ← Log de cada llamada a Granite
│   └── audio/                  ← 8 clips WAV de narración (W0.wav … W7.wav)
│
├── implementacion/
│   ├── partido_config.py               ← Lee partido_activo.json o la variable de entorno
│   ├── dataset/
│   │   ├── dataset_manager.py          ← Etapa 1: percepción
│   │   └── monitor_m1.py               ← Verifica el dataset
│   ├── cloud_tool/
│   │   ├── omnimorph_engine.py         ← Etapa 2: motor táctico
│   │   ├── api_server.py               ← FastAPI: endpoint para Orchestrate
│   │   └── openapi_tool.yaml           ← Especificación OpenAPI de la herramienta
│   ├── dashboard/
│   │   └── tts_service.py              ← Etapa 4: convierte las narraciones en audio
│   └── cloud_agent/
│       ├── agent_narrator.py           ← Etapa 3: narrador con Granite
│       ├── governance_monitor_m3.py    ← Monitor M3: auditoría de Granite
│       ├── chat_agent.py               ← Chatbot del tablero (responde preguntas)
│       └── chat_verificador.py         ← Revisa que el chat cite fuentes reales
│
├── dashboard/                  ← Tablero web (Puerto 8600)
│   ├── serve.py                        ← Servidor HTTP del tablero
│   ├── pages/                          ← 6 páginas HTML
│   ├── components/                     ← JavaScript por página
│   ├── data/                           ← JSON listos para el navegador
│   │   ├── metodo.json                 ← Cifras de los monitores para la página Método
│   │   ├── mateo_data.json             ← Datos de jugadores, radar y narraciones
│   │   └── partido/partido.json        ← Ficha del partido para la página Partido
│   └── styles/                         ← CSS del sistema de diseño
│
├── scripts/
│   └── export_dashboard_data.py        ← Exporta data/clean/ → dashboard/data/
│
├── bob_sessions/               ← Bitácora de 22 sesiones de desarrollo
└── blueprints/                 ← Documentos de arquitectura y planos aprobados
```

---

## 6. Páginas del tablero web

El tablero corre en **http://localhost:8600** y tiene seis páginas:

### Inicio (`index.html`)
Portada pública del proyecto. Muestra:
- Video de fondo con el análisis del partido (demo_omni.mp4).
- Tres bloques que explican cómo funciona el sistema: Visión, Métricas y Narrador.
- Video comercial de 21 segundos que muestra el sistema en tres partidos distintos.
- Franja con los logos de IBM, IBM Granite, IBM watsonx Orchestrate e IBM Bob.

El texto es estático. Solo lee `assets/logos/logos.manifest.json` para armar la franja de logos de IBM.

---

### MATEO (`mateo.html`)
Es el tablero de análisis táctico. Muestra:
- **Video del partido** con los rastros de jugadores dibujados encima.
- **Radar 2D** de la cancha con la posición de todos los jugadores.
- **Crónica táctica** generada por Granite, ventana a ventana.
- **Transcripción** de las narraciones con marcas de tiempo.
- **Chatbot flotante** para hacer preguntas sobre el partido (responde en vivo con Granite).
- **Lista de jugadores** con sus datos (nombre, número de dorsal, equipo, tiempo visible).

Lee desde: `dashboard/data/mateo_data.json`

---

### Partido (`partido.html`)
Ficha completa del partido analizado. Muestra:
- Resultado, fecha, estadio, árbitros y condiciones climáticas.
- Alineaciones de los dos equipos con sus esquemas tácticos.
- Estadísticas del partido (posesión, tiros, faltas, tarjetas).
- Cronología de los goles.
- Fichero de jugadores con foto, dorsal, posición y minutos jugados.
- **Aviso amarillo** "POR VALIDAR" porque los datos aún no los ha revisado una persona del equipo.

Lee desde: `dashboard/data/partido/partido.json`

---

### Método (`metodo.html`)
Explica cómo funciona Omnimorph para un público profesional (directores deportivos, clubes). Muestra:
- **Diagrama de flujo** del sistema: Video → Percepción → Motor → Narrador Granite → Voz → Tablero.
- **Ficha técnica** del MVP con todas las cifras reales de la última corrida.
- **Tabla de los 9 monitores** con los valores observados frente a los límites.
- **Niveles de confianza** y límites del sistema (qué puede hacer y qué no).
- **Gobernanza**: cómo se registra y audita cada llamada a Granite.
- **Logos IBM** al pie: IBM, IBM Granite, IBM watsonx Orchestrate, IBM Bob.

Lee desde: `dashboard/data/metodo.json`

---

### Operaciones (`operaciones.html`)
Panel técnico para mostrar el sistema en funcionamiento durante la demo. Muestra:
- **Estado de los servicios**: servidor local, IBM Cloud IAM, watsonx.ai (confirmando que Granite está disponible en us-south), chatbot y Orchestrate. Botón "Comprobar ahora".
- **Las 9 tarjetas de monitores** con el valor observado frente al límite de cada comprobación.
- **Terminal en vivo** que se actualiza cada 5 segundos: muestra cada llamada al chatbot con sus tokens, RU consumidas y latencia. Las respuestas por regla se marcan con "0 RU · sin llamada al modelo".
- **Totales del día**: preguntas, tokens, RU y latencia promedio.
- **Resumen del narrador**: cifras de la última corrida de Granite (tomadas de `metodo.json`).

Lee desde: `dashboard/data/metodo.json` + rutas del servidor (`/api/operaciones/chat` y `/api/operaciones/ibm`).

---

### Equipo (`#`)
Enlace que aparece en el menú pero **aún no tiene página**. Está en el plan de trabajo.

---

## 7. Monitores M1 – M4

Cada vez que se ejecuta el pipeline, los 9 monitores escriben su resultado en `data/clean/`. La última corrida fue el **9 de noviembre de 2026 a las 23:06 UTC** y duró **25,94 segundos**.

### Resultado de la última corrida: 9 / 9 PASS ✅

| Monitor | Nombre | Qué verifica | Último resultado |
|---|---|---|---|
| **M1** | Percepción y dataset | Que el video tenga al menos 750 cuadros; que la transformación de cancha esté calculada para todos los cuadros (≥ 95 %); que existan filas de jugadores y de balón. | ✅ 1 080 cuadros · 100 % homografía · 17 620 filas jugadores · 860 filas balón |
| **M2.0** | Separación jugadores / balón | Que los jugadores y el balón estén en filas separadas y que todos los rastros tengan equipo asignado. | ✅ 112 rastros con equipo |
| **M2.1** | Homografía EMA | Que la transformación de pantalla a cancha esté suavizada y normalizada en todos los cuadros. | ✅ 100 % de cuadros |
| **M2.2** | Unión de rastros | Que el algoritmo húngaro haya unido rastros partidos sin crear identificadores repetidos en el mismo cuadro. | ✅ 112 → 93 rastros (19 uniones · 0 repetidos) |
| **M2.3** | Cinemática Savitzky-Golay | Que ninguna velocidad supere el límite físico de 9,5 m/s. | ✅ 100 % dentro del límite · 17 612 muestras |
| **M2.4** | Ventanas tácticas | Que se hayan generado exactamente 8 ventanas tácticas. | ✅ 8 / 8 ventanas |
| **M2.5** | Integridad del pipeline | Que los datos limpios, las coordenadas suavizadas, la velocidad y las ventanas estén todos presentes. | ✅ Todo presente |
| **M3** | Auditoría de IBM Granite | Que las 8 narraciones las haya generado exclusivamente `ibm/granite-4-h-small`; que el JSON de cada respuesta sea válido; que el texto no supere 45 palabras; que el equipo dominante coincida con los datos. | ✅ 8 / 8 llamadas con Granite · latencia media 1 588 ms · costo 0,60 RU |
| **M4** | Sincronización de voz y tablero | Que se hayan generado los 8 audios; que ninguno dure más de 4 s; que el desfase entre el audio y el video sea menor a 40 ms. | ✅ Desfase máximo 19,02 ms · audio más largo 3,9 s |

---

## 8. Uso de IBM

| Tecnología IBM | Cómo se usa en Omnimorph |
|---|---|
| **IBM Bob IDE** | Entorno de desarrollo principal. Todas las sesiones se planificaron o programaron aquí. La bitácora de 22 sesiones está en `bob_sessions/`. |
| **IBM watsonx.ai** | Servicio en la nube que aloja el modelo Granite. El narrador le envía la descripción táctica de cada ventana y recibe el texto de la narración. La URL es `https://us-south.ml.cloud.ibm.com`. |
| **IBM Granite (`ibm/granite-4-h-small`)** | Modelo de lenguaje de IBM. Genera las narraciones tácticas en español (hasta 45 palabras por ventana). Es el único modelo autorizado; el Monitor M3 rechaza cualquier otro. |
| **IBM watsonx Orchestrate** | Plataforma de orquestación de agentes. La herramienta táctica de Omnimorph está publicada como endpoint OpenAPI (`openapi_tool.yaml`) y lista para importarse en Orchestrate. La integración se probó durante el desarrollo (sesión 5); la importación en el panel está pendiente. |

Las credenciales (clave de API, URL y proyecto de watsonx) están guardadas solo en el archivo `.env`, que no se sube a Git.

---

## 9. Estado: qué funciona, qué espera validación y qué queda pendiente

### ✅ Funciona hoy

| Qué | Evidencia |
|---|---|
| Pipeline completo de punta a punta (5 etapas + 9 monitores) | `pipeline_summary.json`: `all_pass: true` en 25,94 s |
| Narraciones con IBM Granite (`ibm/granite-4-h-small`) | `monitor_m3.json`: 8/8 PASS · 0,60 RU · latencia media 1 588 ms |
| Tablero web con 5 páginas (Inicio, MATEO, Partido, Método, Operaciones) | Verificado en navegador hasta la sesión 22 |
| Chatbot del tablero habla del partido activo (Costa Rica) | Corregido en el commit `9cd476f` (sesión 20) |
| Fusión de rastros partidos en MATEO (Madrigal, Ugalde, Lassiter aparecen una sola vez) | Sesión 21: 49 → 46 jugadores |
| Sincronización de audio y video (desfase < 40 ms) | M4: 19,02 ms máximo |
| Partido activo configurable sin tocar código | `partido_activo.json` apunta a Costa Rica |
| Brasil-Alemania 2014 conservado como referencia | `data/partidos/brasil_alemania_2014/` presente |
| Cero credenciales en el código fuente | Grep verificado: solo `os.environ` y `.env` |
| Conexión con IBM Cloud IAM y watsonx.ai confirmada sin gastar RU | Ruta `/api/operaciones/ibm`: IAM < 663 ms · watsonx < 372 ms |

---

### 🔶 Espera revisión de Fer

Estos puntos están técnicamente listos pero necesitan que una persona del equipo los confirme antes de la demo:

| Qué espera | Dónde revisar | Impacto si no se hace |
|---|---|---|
| **Datos del partido** (marcador, árbitros, alineaciones, goles) | `data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx` → cambiar `procedencia.validado: true` en `contexto_partido.json` → volver a exportar | El tablero Partido sigue mostrando el aviso amarillo "POR VALIDAR" |
| **Dorsales de jugadores** (10 jugadores en 13 rastros identificados a mano) | `data/partidos/costa_rica_skn_eliminatorias_2026/rastros_dorsales_borrador.json` → confirmar o corregir → crear `rastros_dorsales.json` → volver a exportar | En MATEO aparece la etiqueta naranja "POR VALIDAR" junto a cada nombre |
| **Mapeo de equipos** (cuál equipo ataca hacia qué lado en el video) | Revisar la pestaña `Clip_15` del análisis. Gemini y Claude lo confirmaron en las sesiones 11 y 12, pero el equipo de análisis no lo ha verificado en persona | Solo afecta a si el análisis táctico tiene el sentido de ataque correcto |

Después de que Fer revise los datos y los dorsales, se puede activar el chatbot con la ficha completa del partido (`chat_datos_completos: true` en `partido.config.json`).

---

### 🔲 Pendiente antes de la demo

| Tarea | Quién | Dificultad |
|---|---|---|
| Preparar el plan B offline: pre-exportar `dashboard/data/`, tener los 8 WAV listos, saber qué decir si falla el chat, y ensayarlo con el Wi-Fi apagado | Persona del equipo | 30 minutos de preparación |
| Probar la caída de red en Operaciones: que el estado de IBM y el chat muestren un aviso claro en vez de quedarse esperando | Claude Code | 30 minutos |
| Corregir el nombre del M2.4: el motor dice "Ventanas Tácticas de 4.0 s", pero las ventanas reales duran 4,5 s (`omnimorph_engine.py`, líneas 10, 53 y 330) | Claude Code | 15 minutos |
| Página **Equipo** (enlace en el menú sin página destino) | Por definir | Contenido pendiente de decidir |
| Verificar si los equipos de Brasil-Alemania están invertidos en el video (sesión 13, §6.3) | Claude Code + persona del equipo | 30 minutos |

---

### 🔲 Pendiente después de la demo

| Tarea | Por qué espera | Dificultad |
|---|---|---|
| **Corrección de velocidades** (homografía de cámara TV) | La corrección toca el motor completo y es riesgosa antes de la demo. Las velocidades se ocultan en el tablero como medida temporal. | 4–8 horas de experimentación |
| **Identificación automática de dorsales** (YOLOv8 no sirve en transmisión TV) | Requiere investigación nueva: Granite Vision, OCR o reentrenamiento | 8–16 horas; resultado incierto |
| **Entregables finales del programa** (fusionar a `main`, limpiar ramas, capturas de consumo de RU, video de demo) | Después de la demo | 2–3 horas |
| **Importar la herramienta en watsonx Orchestrate** (`openapi_tool.yaml`) | No hace falta para la demo; la auditoría de la sesión 20 lo dejó para después (M-D05). Requiere acceso al panel y red. | 1–2 horas |
| **Texto del docstring de Brasil** en `chat_agent.py` | Cosmético; no afecta al funcionamiento | 5 minutos |

---

## 10. Datos importantes para la demo

- **Cómo arrancar el día de la demo:** solo `python dashboard/serve.py` y abrir http://localhost:8600. Los datos ya están exportados; no hace falta volver a correr el pipeline.
- **Si se quiere regenerar todo:** `python run_pipeline.py --use-real` y después `python scripts/export_dashboard_data.py`. Ojo: esto vuelve a llamar a Granite, gasta RU y reescribe las narraciones. No hacerlo justo antes de la demo.
- **Tiempo de corrida:** ~26 segundos para las 5 etapas con los 9 monitores.
- **Costo de la última corrida:** 0,60 RU de IBM watsonx.ai (ocho llamadas a Granite).
- **Sin conexión:** el tablero completo (video, radar, narración, ficha del partido) funciona sin internet. Solo el chat en vivo necesita red.
- **Sesiones de trabajo:** 22 sesiones documentadas en `bob_sessions/`. La sesión 22 es la más reciente.

---

*Documento generado por IBM Bob (modo Plan) · 10 de noviembre de 2026 · Rama `feat-costa-rica` · No contiene credenciales, API keys ni tokens.*
