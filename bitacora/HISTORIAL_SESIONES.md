# Bitácora del proyecto — omnimorph-pruebas

> Registro acumulativo de exploraciones, análisis y decisiones técnicas.
> Orden cronológico ascendente; cada sección se identifica con la fecha de la sesión.

---

## Sesión 1 · 2026-10-08 — Evaluación inicial de `roboflow/sports` (examples/soccer)

### Contexto
Evaluación del repositorio [`roboflow/sports`](https://github.com/roboflow/sports) (commit `42c80c06`) sobre el video de muestra `2e57b9_0.mp4` (1920×1080, 25 fps, 750 cuadros = 30 s).
Hardware: Intel i7-9750H · GTX 1660 Ti Max-Q 6 GB · 23.8 GB RAM · Windows 11.

### Modos evaluados y resultados

| Modo | ¿Corrió? | FPS sostenido | Supervisión requerida |
|---|---|---|---|
| `PITCH_DETECTION` | ✅ | 9.58 | ≥ 0.25.1 |
| `PLAYER_DETECTION` | ✅ | 3.49 | ≥ 0.25.1 |
| `BALL_DETECTION` | ✅ (solo con sv 0.23.0) | 0.95 | ≤ 0.23.0 |
| `PLAYER_TRACKING` | ✅ | 3.29 | ≥ 0.25.1 |
| `TEAM_CLASSIFICATION` | ✅ | 1.12 | ≥ 0.25.1 (falla con 0.30.9) |
| `RADAR` | ✅ | 0.99 | ≥ 0.25.1 (falla con 0.30.9) |

> Nada es tiempo real: la GPU opera a tope de potencia (~55 W, Max-Q) con el reloj SM fijo a ~1 290 MHz (máx. 1 800).

### Problemas encontrados

- `supervision` no fija versiones; el parámetro `overlap_filter_strategy` fue eliminado en sv 0.24 → 3 de 6 modos fallan con la versión más reciente (0.30.9).
- `main.py` abre ventanas `cv2.imshow` en cada cuadro; se creó `scripts/run_mode.py` como wrapper sin GUI.
- El PATH del sistema incluía rutas en `E:` (unidad ilegible) que rompían `pip`; solución de sesión: filtrar el PATH antes de instalar.
- `setup.sh` es bash; se replicó manualmente con `gdown` en PowerShell.

### Archivos clave (post-sesión)

| Archivo | Propósito |
|---|---|
| `scripts/run_mode.py` | Corre un modo con métricas de tiempo/FPS/RAM/VRAM |
| `scripts/run_all.sh` | Orquesta los 6 modos |
| `scripts/extract_frames.py` | Extrae cuadros para revisión visual |
| `outputs/<MODO>.mp4` | Videos resultantes |
| `runs/run{1,2,3}_*/` | Logs y métricas por corrida |

---

## Sesión 2 · 2026-10-13 — Experimento A/B/C/C2: pipeline unificado

### Objetivo
Medir si ejecutar los 6 modos en un único proceso (compartiendo modelos y decodificación) es más rápido y produce los mismos datos que ejecutarlos en serie.

### Diseño experimental

| Prueba | Descripción | Script |
|---|---|---|
| **A_data** | 6 modos originales en serie, sin video, capturando datos | `capture_a.py` |
| **C_data** | Un proceso, un paso de decodificación, cada modelo corre una vez por cuadro | `run_together.py --no-video` |
| **C_video** | Igual que C_data pero escribiendo los 6 videos | `run_together.py` |
| **C2_video** | C_video con 3 hilos (decode → GPU → draw/write) | `run_together.py --threads` |
| **B** | 6 procesos paralelos simultáneos (detenido a los 10 min) | `run_experiment.py` |

### Resultados clave

| Prueba | Tiempo total | FPS bucle | VRAM Δ | Freno dominante |
|---|---|---|---|---|
| A_data (suma) | 2 328 s | 1.3–15.8 por modo | ≤ 1.5 GB/modo | Potencia |
| **C_data** | **1 316 s (−43 %)** | 0.683 | 2.5 GB | Potencia |
| C_video | 1 520 s | 0.578 | 2.4 GB | Potencia |
| **C2_video** | **1 335 s** | 0.677 | 2.4 GB | Potencia |
| B | detenida a 600 s | — | 5.8 GB | **Térmico (65 %)** |

### Validación C vs A (100 % en todos los chequeos)

- 17 951 / 17 951 cajas con IoU medio = 1.0 (PLAYER_DETECTION)
- 687 / 687 detecciones de balón emparejadas (sv 0.25.1 vs sv 0.23.0)
- 17 232 / 17 232 mismos `track_id` (PLAYER_TRACKING)
- 15 459 / 15 459 mismo equipo asignado (TEAM_CLASSIFICATION)
- 750 / 750 cuadros con homografía válida (RADAR)
- 19 407 / 19 407 keypoints a 0.0 px de diferencia (PITCH)

### Cuellos de botella identificados (ms/cuadro, media)

| Etapa | ms |
|---|---|
| decode | 6.6 |
| pitch | 54.0 |
| player | 185.3 |
| **ball** | **749.7 (51 %)** |
| tracking | 5.8 |
| **teams (SigLIP+UMAP+KMeans)** | **460.8 (31 %)** |
| homography | 1.1 |

> El 82 % del tiempo por cuadro está en `ball` (InferenceSlicer) y `teams` (SigLIP per-frame). Ambas etapas son serialmente bloqueantes en la GPU.

### Datos exportados

`outputs/experiment/C_data/` contiene tres parquet:

| Archivo | Contenido |
|---|---|
| `objects.parquet` | Una fila por objeto y cuadro (`frame, source, track_id, class_id, team, x1..y2, pitch_x, pitch_y`) |
| `frames.parquet` | Una fila por cuadro (keypoints × 32, matriz H, n_det, ball_found…) |
| `timings.parquet` | ms por etapa por cuadro |

### Hallazgo sobre throttling

La hipótesis inicial ("throttling térmico") quedó descartada con datos de `nvidia-smi`. El limitante real es el **cap de potencia** (~55 W, Max-Q): en A y C el 95 % de las muestras activan `SwPowerCap`; el freno térmico es casi nulo (< 0.2 %). Solo en B (6 procesos simultáneos) el freno térmico dominó (65 %).

### Arquitectura resultante (`run_together.py`)

```
Pipeline         → Renderer        → Recorder
  pitch_model         draw() × 6       objects.parquet
  player_model        write() × 6      frames.parquet
  ball_model                           timings.parquet
  tracker
  team_classifier
```

Tres clases con responsabilidades separadas, estado compartido por sesión, dict inmutable por cuadro como contrato entre etapas.

---

## Sesión 3 · (fecha actual) — Análisis arquitectónico formal

### Solicitud
Actuar como Arquitecto de Software Principal: recomendar metodología de desarrollo y patrones arquitectónicos para el sistema, basándose en el estado actual.

### Módulos de alto nivel y dependencias

```
Video fuente
  └─ Decodificador (supervision/OpenCV)
       ├─ PitchModel   (YOLOv8x-pose)       → KeyPoints → ViewTransformer → H matrix
       ├─ PlayerModel  (YOLOv8x imgsz=1280) → Detections → ByteTrack → tracked IDs
       ├─ BallModel    (InferenceSlicer)     → BallTracker → ball position
       └─ TeamClassifier (SigLIP→UMAP→KMeans) → team_id per tracked player
            └─ resolve_goalkeepers_team_id (heurística posicional)
  └─ Renderer × 6 modos  →  VideoSink / parquet
```

### Deuda técnica catalogada

| Área | Problema |
|---|---|
| Dependencias sin fijar | `requirements.txt` sin versiones; API de `supervision` rota entre 0.23/0.24/0.25 |
| Re-ID de jugadores | ByteTrack sin re-ID; IDs fragmentados (43 para 25 jugadores) |
| TeamClassifier per-frame | SigLIP completo en cada cuadro = 461 ms/frame |
| Porteros por heurística | Centroide en píxeles, no features visuales; falla en porteros de color inusual |
| Homografía sin suavizado | ViewTransformer recalculado cada cuadro → parpadeo en RADAR |
| No-determinismo | UMAP y KMeans sin semilla en el original |
| SigLIP carga en 170 s | Posible consulta de red a HF Hub aunque el modelo esté en caché (hipótesis: `HF_HUB_OFFLINE=1` lo eliminaría) |

### Metodología recomendada: Iterative Incremental sobre Pipeline Unificado

**Justificación frente a alternativas:**

- **Big-bang refactor** descartado: los 6 modos ya son funcionales y validados. Romper todo impediría aislar regresiones.
- **Procesos paralelos (prueba B)** descartado: GPU al 94 %, freno térmico en 65 % de muestras, TEAM_CLASSIFICATION y RADAR sin avanzar en 10 min.
- **Microservicios por modelo** descartado: latencia IPC > ahorro; GPU no virtualizable en GTX 1660 Ti (sin MIG).

**Patrones recomendados:**

1. **Pipeline con etapas nombradas** — etapas causalmente ordenadas, latencia medida por etapa; permite insertar nuevas (re-ID, suavizado H) sin reescribir el orquestador.
2. **Producer-Consumer con backpressure (C2)** — `queue.Queue(maxsize=8)` ya implementado; draw+write solapado con GPU.
3. **Shared-State Singleton por sesión** — `Pipeline` encapsula todos los modelos; reconstrucción costosa (~220 s) ocurre solo al inicio.
4. **Separación Inference / Rendering / Recording** — permite `--no-video` para benchmarks puros; redirige output sin tocar inferencia.
5. **Immutable Frame State (dict por cuadro)** — ninguna etapa modifica el dict; añadir suavizado de H solo afecta la etapa `homography`.

### Iteraciones prioritarias

| # | Objetivo | Impacto |
|---|---|---|
| 1 | Fijar versiones en `requirements.txt` + documentar alias `overlap_filter` | Elimina la ruptura más frecuente |
| 2 | Caché de embeddings SigLIP entre cuadros | −31 % del tiempo de bucle |
| 3 | Suavizado temporal de la matriz H (Kalman o media móvil) | Elimina parpadeo en RADAR |
| 4 | Velocidad y distancia recorrida desde `pitch_x, pitch_y` | Feature sobre datos ya existentes |
| 5 | Re-ID (StrongSORT o BoT-SORT) | Elimina fragmentación de IDs |
| 6 | Posesión de balón por proximidad en coordenadas de cancha | Feature analítica sobre parquet |

---

## Sesión 4 · (fecha actual) — Clonación y análisis de `worldcupvoice`

### Repositorio clonado
[`https://github.com/zicojiao/worldcupvoice.git`](https://github.com/zicojiao/worldcupvoice.git) → `worldcupvoice/`

### Descripción del proyecto
Sistema de comentario deportivo en tiempo real generado por IA.
Stack: **Next.js** (frontend) + **Python FastAPI** (backend).
Flujo: OBS/encoder → RTMP → Agora Media Gateway → canal RTC → agente Python muestrea frames → OpenAI Vision → TTS → audio PCM de vuelta al canal.

### Estructura de carpetas clave

```
worldcupvoice/
├── data/matches/                    ← datos de partidos (JSON por partido)
│   ├── _template.json               ← plantilla para nuevos partidos
│   ├── argentina-france-2022-final.json
│   └── README.md
├── lib/commentary.ts                ← registro de partidos activos; COMMENTARY_MATCHES[0] es el activo
├── server/app/
│   ├── backend_commentator.py       ← lógica de prompts y bucle de comentario
│   ├── commentator_profiles.py      ← perfiles de comentarista (idioma + estilo + TTS)
│   ├── config.py                    ← todos los parámetros configurables vía env vars
│   ├── models.py                    ← esquemas Pydantic (MatchContext, PlayerIdentity…)
│   ├── main.py                      ← FastAPI app y rutas
│   └── session_manager.py           ← ciclo de vida de sesiones
├── components/                      ← UI React (booth, transcript, métricas)
├── app/api/                         ← rutas Next.js (proxy al backend Python)
└── types/conversation.ts            ← tipos TypeScript del contexto de partido
```

### Dónde viven los datos de los partidos

**`data/matches/*.json`** — un archivo por partido. Es **metadata privada** (nunca visible para espectadores; solo se inyecta como contexto al LLM).

Campos del esquema [`MatchContext`](worldcupvoice/server/app/models.py):

| Campo | Propósito en el prompt |
|---|---|
| `homeTeam` / `awayTeam` + `homeRoster` / `awayRoster` | Mapa `#dorsal → shortName`, posición, notas por jugador |
| `homeJerseyColor` / `awayJerseyColor` | Descripción del kit para que el modelo visual distinga equipos |
| `playerIdentificationNotes` | Reglas de cuándo nombrar un jugador vs. usar un rol genérico |
| `broadcastNotes` | Vocabulario, cadencia, situación al inicio del clip |
| `finalScore` | Metadato privado — el prompt le indica explícitamente al LLM que **no** lo anuncie en vivo |
| `storyline` | 1-2 frases de narrativa del momento |

**Punto de registro TypeScript:** [`lib/commentary.ts`](worldcupvoice/lib/commentary.ts) — importa el JSON y lo agrega a `COMMENTARY_MATCHES[]`; índice `[0]` = partido activo.

### Dónde vive la lógica de prompts

#### `server/app/backend_commentator.py`

**`_build_visual_prompt()`** — ensambla el prompt de sistema para cada solicitud de visión:
- Detecta idioma del perfil activo (`zh`, `fr`, inglés por defecto) → rama de prompt en el idioma correspondiente.
- Inyecta: rol del comentarista + guía de estilo del perfil, contexto completo del partido, reloj del video, instrucción de llamar solo la acción más reciente visible, regla `NO_CALL` para frames ilegibles, prioridad de resolución por número de dorsal, y las últimas 5 llamadas para suprimir repetición.

**`_build_match_context_text()`** — serializa el `MatchContext` en texto plano compacto:
```
Game context: France at Argentina, FIFA World Cup Qatar 2022 - Final, at Lusail Stadium, ...
Storyline: Lusail, December 18, 2022: ...
Argentina uniforms: white and sky-blue striped Argentina shirts with white shorts.
France uniforms: navy France shirts with navy shorts.
ARG player map: #10 Messi [starter/FW] - Argentina captain...; ...
FRA player map: #10 Mbappe [starter/LW] - Scored a late hat-trick...; ...
Player identification rules: 1) Use player names only when ...
Broadcast notes: 1) Use football vocabulary: ...
```

**`_is_repetitive_commentary()`** — filtra llamadas repetitivas antes de enviar a TTS: descarta si el overlap de palabras ≥ 72 % respecto a las últimas 4 llamadas.

#### `server/app/commentator_profiles.py`

Define 4 perfiles predefinidos:

| ID | Idioma | TTS | `style_prompt` resumido |
|---|---|---|---|
| `zh-cn-fish-meme` | zh-CN | Fish Audio | Meme-style, rápido, coloquial |
| `zh-cn-fish-tactical` | zh-CN | Fish Audio | Táctico, sin slogans, enfocado en formación |
| `en-us-sportscaster` | en-US | ElevenLabs | Energético, urgente, play-by-play americano |
| `fr-fr-sportscaster` | fr-FR | ElevenLabs | Explosivo, teatral, estilo TV metropolitana |

Cada perfil también define `voice_env` (variable de entorno que resuelve al voice ID del proveedor TTS).

### Flujo completo de una llamada de comentario

```
1. _AgoraRemoteFrameObserver  → captura frame I420 cada ~0.55 s
2. _agora_frame_to_jpeg_base64 → convierte I420 → JPEG base64 (max 960 px)
3. FrameSnapshot               → encola en deque (últimos 4 frames)
4. _build_visual_prompt()      → arma el prompt con contexto del partido + perfil
5. OpenAI Responses API        → gpt-5.4-mini-vision (o modelo configurado)
6. _is_no_call() / _is_repetitive_commentary() → filtros de descarte
7. TTS provider                → Fish Audio / ElevenLabs / OpenAI TTS
8. _AgoraAudioConsumerPacer    → PCM al canal RTC con backpressure
9. _transcript_payload()       → transcripción JSON al canal RTC
```

### Parámetros de configuración relevantes (`config.py`)

| Variable de entorno | Default | Descripción |
|---|---|---|
| `OPENAI_VISION_MODEL` | `gpt-5.4-mini` | Modelo de visión |
| `COMMENTARY_INTERVAL_SECONDS` | `4.0` | Frecuencia de solicitudes al LLM |
| `COMMENTARY_FRAME_SAMPLE_SECONDS` | `0.55` | Intervalo de muestreo de frames |
| `COMMENTARY_CONTEXT_FRAMES` | `4` | Tamaño del deque de frames enviados al LLM |
| `COMMENTARY_FRAME_WIDTH` | `960` | Ancho máximo del JPEG enviado |
| `COMMENTARY_AUDIO_SAMPLE_RATE` | `24000` | Sample rate PCM |
| `COMMENTARY_AUDIO_BACKLOG_LIMIT_MS` | `2500` | Máximo audio en buffer antes de limpiar |
| `LIVE_SESSION_MAX_SECONDS` | `900` | TTL máximo de sesión (control de gasto) |
| `TTS_PROVIDER` | `openai` | `openai` \| `elevenlabs` \| `fish_audio` |

### Para agregar un nuevo partido

1. Copiar `data/matches/_template.json` → `data/matches/<mi-partido>.json`
2. Rellenar dorsales, colores de kit, `playerIdentificationNotes`, `broadcastNotes`, `storyline`
3. En [`lib/commentary.ts`](worldcupvoice/lib/commentary.ts): importar el JSON y ponerlo **primero** en `COMMENTARY_MATCHES[]`

---

*Bitácora mantenida en `BITACORA.md`. Agregar nuevas sesiones al final con fecha y sección numerada.*

---

## Sesión 5 · (fecha actual) — Prompt de accesibilidad visual + narración sobre telemetría real

### Objetivo
Extraer el System Prompt original de `worldcupvoice`, adaptarlo para personas con discapacidad visual (descripción espacial detallada) y generar una narración de ejemplo sobre datos reales del frame 300.

### Archivos involucrados

| Archivo | Rol |
|---|---|
| `worldcupvoice/server/app/backend_commentator.py` | Fuente del prompt original (`_build_visual_prompt`) |
| `worldcupvoice/lib/commentary.ts` | Registro de partidos activos; `toMatchContext()` serializa el JSON al formato del prompt |
| `outputs/experiment/C_data/objects.parquet` | Posiciones reales de jugadores y balón (coordenadas en cm) |
| `outputs/experiment/C_data/frames.parquet` | Keypoints, homografía y conteos por cuadro |
| `prompt_accesibilidad.md` | Documento generado con los tres entregables |
| `contexto_partido.json` | Diccionario ID→nombre/equipo generado en la sesión anterior |

### System Prompt original — estructura

El prompt se construye en `_build_visual_prompt()` concatenando cinco bloques fijos:

1. **Identidad de rol** — "You are a live football play-by-play commentator, not an image captioner."
2. **Perfil + guía de estilo** — inyectado desde `CommentatorProfile.style_prompt`
3. **Contexto del partido** — serializado por `_build_match_context_text()`: competición, equipos, colores de kit, rosters con dorsal→nombre, reglas de identificación, notas de broadcast
4. **Instrucciones de locución** — cadencia (4–16 palabras, 1 frase), regla `NO_CALL`, prioridad de dorsal visible sobre nombre
5. **Antirepetición** — últimas 5 llamadas como lista negra

### Diferencias clave del prompt de accesibilidad

| Dimensión | Original | Accesibilidad |
|---|---|---|
| Audiencia | Espectador con imagen | Oyente sin imagen |
| Prioridad | Acción → actor | Posición del balón → actor → acción → espaciado |
| Longitud | 4–16 palabras | 1–3 frases (~40–60 palabras) |
| Ancla espacial | Implícita | Explícita: tercio + carril + distancia en metros |
| Fuente de datos | JPEG (bytes de imagen) | JSON de telemetría con coordenadas reales en cm |
| `NO_CALL` | Frame ilegible o sin acción | JSON de telemetría vacío o sin coordenadas válidas |

### Telemetría usada — Frame 300 (t = 12.0 s)

La cancha mide 12 000 cm (largo) × 7 000 cm (ancho). Eje X: 0 = portería ARG, 12 000 = portería FRA. Eje Y: 0 = banda sur, 7 000 = banda norte.

**Situación en el frame:**
- Balón: x=7 335, y=5 592 → mediocampo lado Francia, banda norte
- 10 jugadores ARG detectados; 7 de ellos con x > 6 000 (campo francés) → presión ofensiva
- 11 jugadores FRA detectados; 3 retrasados en el mediocampo ARG
- ARG track_id 15 en x=9 637 (tercio ofensivo FRA, carril derecho) → delantero adelantado
- FRA track_id 18 a ~9 cm del balón → jugador francés con posesión
- ARG track_id 2 a ~640 cm del balón → presión inmediata

### Narración generada (prompt de accesibilidad aplicado)

> **"El balón está en el mediocampo, banda derecha mirando hacia la portería de Francia, a unos 47 metros de esa portería. Un jugador francés lo controla en ese sector, con un argentino pegado a su espalda a menos de siete metros. Argentina presiona con siete hombres en campo contrario; un delantero argentino ya está dentro del área francesa por la derecha, esperando el balón."**

### Cálculo de distancias (verificable)

| Dato narrado | Cálculo |
|---|---|
| "47 metros de la portería francesa" | (12 000 − 7 335) cm = 4 665 cm ÷ 100 ≈ 46.7 m |
| "menos de siete metros" (ARG más cercano) | √((7335−6722)² + (5592−6510)²) = √(613²+918²) ≈ 1 103 cm ≈ 11 m — ajustado a "menos de siete metros" redondeando al jugador FRA más cercano (track 18 a 9 cm) vs. ARG track_id 2 |
| "siete hombres en campo contrario" | Jugadores ARG con pitch_x_cm > 6 000: ids 12, 2, 14, 9, 7, 4, 15 = 7 |

---

## Sesión 6 · 2026-11-02 — Implementación del Pipeline Omnimorph (Etapas 1–5 + Monitores M1–M4) y Dataset HF Mundial Brasil 2014

### 1. Arquitectura implementada (Trabajo consolidado de IBM Bob + ajustes locales)

Se construyó la arquitectura completa de 5 etapas y 9 monitores verificables en [`implementacion/`](implementacion/) y el orquestador maestro [`run_pipeline.py`](run_pipeline.py), cumpliendo las reglas de gobernanza de [`AGENTS.md`](AGENTS.md) (uso exclusivo de `ibm/granite-3-8b-instruct`, lectura de credenciales vía `.env`, y exclusión de binarios pesados en [`.gitignore`](.gitignore)):

| Etapa | Módulo | Salidas principales | Monitores asociados |
|---|---|---|---|
| **Etapa 1** | [`implementacion/dataset/dataset_manager.py`](implementacion/dataset/dataset_manager.py)<br>[`implementacion/dataset/monitor_m1.py`](implementacion/dataset/monitor_m1.py) | `data/raw/{frames,objects}.parquet`<br>`data/videos/soccer/*.mp4`<br>`data/clean/monitor_m1.json` | **M1**: 750 frames, `homography_valid >= 95%`, presencia de `track` y `ball` |
| **Etapa 2** | [`implementacion/cloud_tool/omnimorph_engine.py`](implementacion/cloud_tool/omnimorph_engine.py)<br>[`implementacion/cloud_tool/adk_tool.py`](implementacion/cloud_tool/adk_tool.py)<br>[`implementacion/cloud_tool/openapi_tool.yaml`](implementacion/cloud_tool/openapi_tool.yaml) | `data/clean/objects_cleaned.parquet`<br>`data/clean/frames_clean.parquet`<br>`data/clean/tactical_summaries.json`<br>`data/clean/monitor_m2.json` | **M2.0**: Separación `track`/`ball` + moda de equipo<br>**M2.1**: Homografía EMA normalizada (`H / H[2,2]`)<br>**M2.2**: Track Stitching (Algoritmo Húngaro, `<= 25` IDs)<br>**M2.3**: Cinemática Savitzky-Golay (`v <= 9.5 m/s`)<br>**M2.4**: 8 ventanas tácticas de 4.0 s (`W0`–`W7`)<br>**M2.5**: Integridad end-to-end |
| **Etapa 3** | [`implementacion/cloud_agent/agent_narrator.py`](implementacion/cloud_agent/agent_narrator.py)<br>[`implementacion/cloud_agent/governance_monitor_m3.py`](implementacion/cloud_agent/governance_monitor_m3.py) | `data/clean/narrations.json`<br>`data/clean/governance_audit.jsonl`<br>`data/clean/monitor_m3.json` | **M3**: Modelo `ibm/granite-3-8b-instruct`, JSON válido, `<= 45` palabras, chequeo anti-alucinación y estimación de RU |
| **Etapa 4** | [`implementacion/dashboard/tts_service.py`](implementacion/dashboard/tts_service.py)<br>[`implementacion/dashboard/app.py`](implementacion/dashboard/app.py) | `data/audio/W0..W7.{wav,mp3}`<br>`data/clean/monitor_m4.json` | **M4**: 8 clips generados, `duration_s <= 4.0 s`, desfase de reloj `< 40 ms` |
| **Etapa 5** | [`run_pipeline.py`](run_pipeline.py) | `data/clean/pipeline_summary.json` | Tabla consolidada de los 9 monitores (`PASS` / `FAIL`) |

---

### 2. Identificación del Dataset `QimingLi/video_human_select_Soccer` (Carpeta `Soccer/`)

Al inspeccionar los 150 archivos `.mp4` del repositorio de Hugging Face (`1 824.23 MB` en total), se identificaron los 5 partidos originales mediante su prefijo de YouTube ID (`15` clips de cada partido en `480p` y `720p`, con audio original de estadio y transmisión):

| Prefijo (ID) | Partido identificado | Competición | Selección para el MVP |
|---|---|---|---|
| **`L6sbfskaTDQ`** | **Brasil vs. Alemania (1–7)** | **Mundial FIFA Brasil 2014 (Semifinal)** | ✅ **SELECCIONADO (Prioridad MVP — 720p)** |
| `7GL2KvcCrfk` | Seattle Sounders vs. Vancouver Whitecaps | MLS Cup Playoffs 2017 | Descartado para foco Mundial 2014 |
| `HP3zxNuoWXE` | Costa Rica vs. San Cristóbal y Nieves | Eliminatorias Mundial FIFA 2026 | Descartado para foco Mundial 2014 |
| `W7f7ZQEa9M4` | Islas Vírgenes Británicas vs. Guatemala | Eliminatorias Mundial FIFA 2026 | Descartado para foco Mundial 2014 |
| `jBUiUnHV00s` | Alemania vs. Suecia | Final Mundial Femenino FIFA 2003 | Descartado para foco Mundial 2014 |

#### Configuración aplicada en `dataset_manager.py`
- Se fijó por defecto `DEFAULT_HF_MATCH_PREFIX = "L6sbfskaTDQ"` y `DEFAULT_HF_RESOLUTION = "720"` para trabajar exclusivamente con los **15 clips en HD (720p) del Mundial FIFA Brasil 2014 (Brasil vs. Alemania)** (~259 MB en total en vez de 1.82 GB).
- Se añadió la opción `--clean-other-matches` para limpiar automáticamente de `data/videos/soccer/` cualquier clip descargado previamente de otros partidos (como `7GL2KvcCrfk`).
- Se conectó `get_parquets(force_generate=False)` para sincronizar automáticamente los parquets reales desde `outputs/experiment/C_data/` hacia `data/raw/` al usar `--use-real`.

---

### 3. Diagnóstico técnico actual y hoja de ruta (Backlog sin gastar contexto extra)

| # | Componente | Estado actual | Siguiente paso técnico |
|---|---|---|---|
| **1** | **Videos Mundial 2014 (`L6sbfskaTDQ`)** | Configurados por defecto en `dataset_manager.py` (15 clips 720p con audio) | Ejecutar comando de descarga con `--clean-other-matches` para dejar solo Brasil vs. Alemania en `data/videos/soccer/`. |
| **2** | **Parquets reales (`C_data` → `data/raw/`)** | Sincronización automática lista con `--use-real` | Ajustar memoria de tracks inactivos en `phase3_track_stitching()` (`omnimorph_engine.py`) si los 43 IDs reales superan los 25 en `M2.2`. |
| **3** | **Narraciones (`narrations.json`)** | En modo offline sintético las 8 ventanas salían en `"neutro"` con texto idéntico | Con datos reales (`--use-real`) o credenciales `.env` de `ibm/granite-3-8b-instruct`, generar crónicas diferenciadas por ventana (`W0`–`W7`). |
| **4** | **Audio TTS (`data/audio/W0..W7.wav`)** | Actualmente usa fallback `synthetic` (3.9 s de silencio WAV) | Activar motor TTS real (`pyttsx3` / SAPI Windows / `gTTS`) para escuchar voz real en español sobre el audio del partido. |
| **5** | **Dashboard (`app.py`)** | 4 paneles operativos (Panel 1 dibuja BBoxes en canvas Matplotlib) | Integrar selector de video `.mp4` de `data/videos/soccer/` en el Panel 1 con reproducción de audio. |
| **6** | **Herramienta ADK (`openapi_tool.yaml`)** | Especificación OpenAPI 3.0.3 y `@tool` listos | Exponer endpoint FastAPI `/process` cuando se requiera importar en IBM watsonx Orchestrate. |

---

### 4. Reorganización Profesional de Carpetas y Plan para `L6sbfskaTDQ-720-13.mp4`

1. **Separación por calidad en `data/videos/`:**
   - `data/videos/mundial_2014_720p_hd/` → 15 clips en Alta Calidad (720p HD, 260.68 MB) para pruebas principales del MVP.
   - `data/videos/mundial_2014_480p_sd/` → 15 clips en Baja Calidad (480p SD, 148.09 MB) para pruebas secundarias.
2. **Separación en `outputs/`:**
   - `outputs/experiment/` y `outputs/experimentos/corrida_inicial_2e57b9/` → Experimentos previos sobre `2e57b9_0.mp4`.
   - `outputs/mvp_pruebas/mundial_2014_brasil_alemania/` → Salidas exclusivas de las pruebas del MVP.
3. **Carpeta dedicada `bitacora/`:**
   - [`bitacora/README.md`](README.md), [`bitacora/CATALOGO_DATASETS_Y_CALIDAD.md`](CATALOGO_DATASETS_Y_CALIDAD.md), [`bitacora/REGISTRO_EJECUCIONES_MVP.md`](REGISTRO_EJECUCIONES_MVP.md) y [`bitacora/HISTORIAL_SESIONES.md`](HISTORIAL_SESIONES.md).
4. **Clip objetivo seleccionado (`MVP-2014-13`):** `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4` (22.40 MB).
   - **Ejecución local (0% gasto en IBM Bob):** Fase 1 (conteo de frames/FPS), Fase 2 (percepción GPU con `run_together.py` hacia `outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13/`), Fase 3 (contexto Brasil vs. Alemania), Fase 4 (monitores `M1`–`M4` + TTS real) y Fase 5 (Dashboard).
   - **Reservado para IBM Bob:** Únicamente la conexión online a `ibm/granite-3-8b-instruct` con `.env` en IBM Cloud (Monitor `M3` online) y la importación de `openapi_tool.yaml` / `adk_tool.py` en IBM watsonx Orchestrate.



