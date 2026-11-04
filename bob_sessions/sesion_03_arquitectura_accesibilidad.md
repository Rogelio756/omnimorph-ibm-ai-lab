# Sesión 03 — IBM Bob IDE
## Análisis Arquitectónico Formal + Prompt de Accesibilidad Visual
**Fecha:** 2026-10-15
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA
**Equipo:** Rogelio Leonardo Mendez Macias
**Herramientas IBM utilizadas:** IBM Bob IDE

---

## Objetivo de la sesión

1. Actuar como Arquitecto de Software Principal: recomendar metodología y patrones arquitectónicos para el sistema Omnimorph.
2. Analizar el repositorio `worldcupvoice` (comentario deportivo en tiempo real por IA).
3. Adaptar el System Prompt de `worldcupvoice` para usuarios con discapacidad visual usando datos reales de telemetría (frame 300, `2e57b9_0.mp4`).

---

## Trabajo realizado con IBM Bob IDE

### Parte A — Arquitectura del sistema Omnimorph

IBM Bob analizó la deuda técnica y recomendó la metodología **Iterative Incremental sobre Pipeline Unificado**.

#### Deuda técnica catalogada

| Area | Problema |
|---|---|
| Dependencias sin fijar | `requirements.txt` sin versiones; API de `supervision` rota entre 0.23/0.24/0.25 |
| Re-ID de jugadores | ByteTrack sin re-ID; IDs fragmentados (43 para 25 jugadores) |
| TeamClassifier per-frame | SigLIP completo en cada cuadro = 461 ms/frame |
| Porteros por heuristica | Centroide en pixeles, no features visuales |
| Homografia sin suavizado | ViewTransformer recalculado cada cuadro — parpadeo en RADAR |
| No-determinismo | UMAP y KMeans sin semilla en el original |

#### Patrones de diseno recomendados por IBM Bob

1. **Pipeline con etapas nombradas** — permite insertar nuevas etapas sin reescribir el orquestador
2. **Producer-Consumer con backpressure** — `queue.Queue(maxsize=8)` para solapar decode con GPU
3. **Shared-State Singleton por sesion** — `Pipeline` encapsula modelos; reconstruccion solo al inicio
4. **Separacion Inference / Rendering / Recording** — `--no-video` para benchmarks puros
5. **Immutable Frame State** — dict por cuadro; ninguna etapa lo modifica

#### Iteraciones priorizadas

| Prioridad | Objetivo | Impacto estimado |
|---|---|---|
| 1 | Fijar versiones en requirements.txt | Elimina ruptura mas frecuente |
| 2 | Cache de embeddings SigLIP entre cuadros | -31% del tiempo de bucle |
| 3 | Suavizado temporal de la matriz H | Elimina parpadeo en RADAR |
| 4 | Velocidad y distancia desde pitch_x, pitch_y | Feature sobre datos ya existentes |
| 5 | Re-ID (StrongSORT o BoT-SORT) | Elimina fragmentacion de IDs |
| 6 | Posesion de balon por proximidad | Feature analitica sobre parquet |

---

### Parte B — Analisis de `worldcupvoice`

IBM Bob analizo el repositorio `worldcupvoice` (Next.js + FastAPI + Agora RTC + OpenAI Vision + TTS).

Flujo identificado:
```
OBS/encoder → RTMP → Agora Media Gateway → canal RTC
  → agente Python muestrea frames (I420 → JPEG base64)
  → OpenAI Vision (gpt-5.4-mini)
  → TTS (Fish Audio / ElevenLabs / OpenAI TTS)
  → audio PCM de vuelta al canal RTC
```

---

### Parte C — Prompt de accesibilidad visual

IBM Bob adapto el System Prompt de `worldcupvoice` para usuarios con discapacidad visual.

#### Datos reales del frame 300 (`2e57b9_0.mp4`, t = 12.0 s)

| Elemento | Posicion en cancha (pitch_x, pitch_y cm) | Observacion |
|---|---|---|
| Balon | 7 335, 5 592 | Mediocampo lado Francia, banda norte |
| ARG track_id 15 | 9 637, aprox. | Tercio ofensivo FRA, carril derecho (delantero adelantado) |
| FRA track_id 18 | ~7 326, ~5 583 | A 9 cm del balon — jugador frances con posesion |
| ARG track_id 2 | ~6 722, ~6 510 | A 640 cm del balon — presion inmediata |
| ARG en campo contrario | 7 jugadores con pitch_x > 6 000 | Presion ofensiva de Argentina |

#### Narracion generada (prompt de accesibilidad)

> "El balon esta en el mediocampo, banda derecha mirando hacia la porteria de Francia, a unos 47 metros de esa porteria. Un jugador frances lo controla en ese sector, con un argentino pegado a su espalda a menos de siete metros. Argentina presiona con siete hombres en campo contrario; un delantero argentino ya esta dentro del area francesa por la derecha, esperando el balon."

#### Diferencias clave respecto al prompt original

| Dimension | Original | Accesibilidad |
|---|---|---|
| Audiencia | Espectador con imagen | Oyente sin imagen |
| Prioridad | Accion — actor | Posicion del balon — actor — accion — espaciado |
| Longitud | 4-16 palabras | 1-3 frases (~40-60 palabras) |
| Ancla espacial | Implicita | Explicita: tercio + carril + distancia en metros |
| Fuente de datos | JPEG | JSON de telemetria con coordenadas reales en cm |

---

## Tokens y metricas de sesion

| Metrica | Valor |
|---|---|
| Herramienta | IBM Bob IDE |
| Modelo asistente | IBM Bob |
| Tareas completadas | Arquitectura formal + analisis worldcupvoice + prompt accesibilidad |
| Archivos generados | `prompt_accesibilidad.md`, `contexto_partido.json` |
| Cancha de referencia | 12 000 x 7 000 cm (120 x 70 m) |
| Frame testigo | Frame 300, t=12.0 s, `2e57b9_0.mp4` |
