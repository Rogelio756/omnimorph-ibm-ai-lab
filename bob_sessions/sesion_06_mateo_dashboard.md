# Sesión 06 — MATEO: Nombre y Observabilidad del Dashboard

**Fecha:** 2026-11-04  
**Estado del pipeline al inicio:** 9/9 PASS · `run_pipeline.py --use-real` · 63 s · `ibm/granite-4-h-small`

---

## 1. Contexto de la sesión

El pipeline Omnimorph estaba completamente funcional (MVP-2014-13, clip_13, 1800 frames / 60 s).  
El dashboard Streamlit existía en `implementacion/dashboard/app.py` pero presentaba dos problemas críticos al abrirse:

| Problema | Causa raíz | Síntoma |
|----------|-----------|---------|
| Videos no visibles (WebSocket) | `st.video(bytes)` leía archivos de ~500 MB completos en RAM antes de enviarlos por WebSocket | Pantalla en blanco / timeout del navegador |
| Videos en `0:00` sin reproducir | `sv.VideoSink` generaba MP4 con códec `FMP4` (`mpeg4` Part 2 / `mp4v`), no soportado por `<video>` HTML5 en navegadores | Reproductor en negro en `0:00` con botón Play deshabilitado |
| Monitores no visibles | El crash del Panel 1 (video) ocurría antes del render del semáforo | Los 9 `monitor_*.json` existían y tenían PASS, pero nunca se dibujaban |
| Frame inicial `0` vacío de jugadores | `ByteTrack` inicia tracks de jugadores en `frame = 3` (`frame = 0..2` solo contiene `ball`) | Al abrir el dashboard en `Frame 0`, el visor y el radar solo mostraban el balón |

---

## 2. Cambios realizados

### 2.1 Rebrand a MATEO (`implementacion/dashboard/app.py`)

| Punto | Antes | Ahora |
|-------|-------|-------|
| Tab del navegador | `Omnimorph — Pipeline Dashboard` | `MATEO — Análisis Táctico de Fútbol` |
| Header / logo fallback | `⚽ OMNIMORPH` | `⚽ MATEO` + subtítulo completo |
| Sidebar | genérico | `## ⚽ MATEO` + caption con nombre expandido |
| Tablero de semáforos | `🚦 Tablero de Observabilidad` | `🚦 MATEO · Tablero de Observabilidad` |
| Footer | `granite-3-8b-instruct` | `granite-4-h-small` (modelo real activo) |
| Docstring módulo | 750 frames · granite-3 | 1800 frames · granite-4-h-small |

### 2.2 Fix crítico del video y códec H.264 (Panel 1 y generadores)

1. **Streaming por ruta en Streamlit:**
```python
# ANTES (carga todo el archivo en RAM → crash)
with open(post_math_video, "rb") as _vf:
    st.video(_vf.read(), format="video/mp4")

# AHORA (streaming por chunks + subtítulos WebVTT sincronizados)
st.video(str(post_math_video), subtitles=subs_arg)
```

2. **Codificación directa en `H.264 (libx264, yuv420p, faststart)` con PyAV (`av`):**
   - Los navegadores web requieren `H.264 (avc1)` y rechazan `mp4v` (`FMP4`).
   - Se actualizaron `scripts/render_post_engine_video.py` y `scripts/finalize_mvp_perception.py` para codificar en `libx264` (`yuv420p`, `movflags=faststart`).
   - Reducción de tamaño y compatibilidad total HTML5:
     - `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4`: `83.6 MB (mpeg4)` → **`21.4 MB (h264 + audio aac)`**
     - `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4`: `79.2 MB (mpeg4)` → **`34.9 MB (h264)`**

### 2.3 Separación visual: Video con Marcas (sin radar) + Video Original a la par + Radar Independiente

- **Panel 1 — Vista en paralelo (`Con Marcas + Original`):**
  - Se eliminó el radar superpuesto de la parte inferior de `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4` para dejar 100% libre la cancha con las marcas matemáticas (`M2.0` equipos estables, `M2.1` keypoints EMA, `M2.2` 22 IDs cosidos, `M2.3` velocidad Savitzky-Golay y estela del balón).
  - Selector `st.segmented_control` en Panel 1 con vista por defecto **`🔀 En paralelo (Con Marcas + Original)`** que muestra lado a lado el video con marcas MATEO y el video original sin marcas (`data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4`).
- **Panel 2 — Radar Cenital 2D en la visual de al lado (`VIDEO_RADAR_POST_MATEMATICA.mp4`):**
  - Se generó el video dedicado `VIDEO_RADAR_POST_MATEMATICA.mp4` (`2.8 MB`, H.264) exclusivamente con el Radar Cenital 2D suavizado, sus estelas y el indicador `TOMA ABIERTA / TOMA CERRADA`, ubicado en el Panel 2 junto al radar interactivo por fotograma.
- **Reloj Maestro inicializado en `frame = 3`:**
  - Arranca automáticamente en el primer fotograma con jugadores activos (`frame = 3`) para mostrar los 22 jugadores desde la carga inicial.

### 2.4 Audio TTS continuo + Subtítulos WebVTT + Transcriptor Sincronizado (Panel 1 y Panel 4)

- **Audio Maestro de 60 s (`data/audio/NARRACION_COMPLETA_60S.wav`):**
  - Ensambla los 8 clips `W0.wav`–`W7.wav` en sus timestamps exactos (`t0 = 0.00s, 5.57s, 11.13s, ..., 38.97s`) e incrusta la pista de audio AAC directamente dentro de `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4`.
- **Subtítulos WebVTT (`data/clean/narrations_es.vtt`):**
  - Generados automáticamente desde `data/clean/narrations.json` y conectados a `st.video(..., subtitles=...)` en el Panel 1.
- **Transcriptor Completo Sincronizado en Panel 4:**
  - Incluye el reproductor del Audio Maestro continuo de 60 s, el reproductor individual de la ventana activa y el transcriptor completo (`W0`–`W7`) con marcas de tiempo que resalta en verde (`🟢 EN CURSO`) la ventana activa.

### 2.5 Nueva página de Observabilidad (`implementacion/dashboard/pages/1_Observabilidad.py`)

Página Streamlit multipage que se abre en la barra lateral como segunda página del dashboard MATEO.

**Contenido:**
- **Resumen global**: badge 9/9 PASS, tiempo total, timestamp de última ejecución
- **Tab M1 · Percepción**: frames procesados, tracks, homografía, detecciones de balón
- **Tab M2.0–M2.5 · Engine**: cada sub-monitor en expander con sus métricas detalladas
- **Tab M3 · Gobernanza IBM**: modelo usado, llamadas validadas, latencia, RU consumidas, tabla del `governance_audit.jsonl`
- **Tab M4 · TTS & Sync**: tabla duración/desfase por ventana + reproductor de los 8 clips `.wav`

---

## 3. Estructura final del dashboard

```
implementacion/dashboard/
├── app.py                         ← MATEO · Dashboard principal (4 paneles)
└── pages/
    └── 1_Observabilidad.py        ← MATEO · Tablero de monitores M1–M4
```

---

## 4. Cómo lanzar MATEO

```powershell
# Desde el directorio del proyecto
.\.venv\Scripts\streamlit run implementacion\dashboard\app.py
```

Streamlit detecta automáticamente la carpeta `pages/` y añade la segunda página en la barra lateral.

---

## 5. Estado de procesos locales al cierre de sesión

| Proceso / Artefacto | Estado | Ubicación |
|---------------------|--------|-----------|
| `data/clean/objects_cleaned.parquet` | ✅ Activo en disco | 10 818 tracks + 572 balls (clip_13 real) |
| `data/clean/frames_clean.parquet` | ✅ Activo en disco | 1 800 frames @ 30 FPS = 60 s |
| `data/clean/tactical_summaries.json` | ✅ Activo en disco | 8 ventanas W0–W7 |
| `data/clean/narrations.json` | ✅ Activo en disco | 8 narraciones online · granite-4-h-small |
| `data/audio/W0–W7.wav` | ✅ Activo en disco | 8 clips TTS español ~3.9 s c/u |
| `data/audio/NARRACION_COMPLETA_60S.wav` | ✅ Activo en disco | Audio maestro continuo de 60 s sincronizado |
| `data/clean/narrations_es.vtt` | ✅ Activo en disco | Subtítulos WebVTT sincronizados (`W0`–`W7`) |
| `data/clean/monitor_m*.json` | ✅ 9/9 PASS | M1, M2 (6 sub), M3, M4 |
| `outputs/clip_13/VIDEO_OMNIMORPH_POST_MATEMATICA.mp4` | ✅ En disco (`21.4 MB`) | Video H.264 con marcas (sin radar) + audio TTS AAC |
| `outputs/clip_13/VIDEO_RADAR_POST_MATEMATICA.mp4` | ✅ En disco (`2.8 MB`) | Video H.264 exclusivo del Radar Cenital 2D (Panel 2) |
| `outputs/clip_13/VIDEO_UNIFICADO_TODOS_JUNTOS.mp4` | ✅ En disco (`34.9 MB`) | Video H.264 percepción cruda (6 modelos) |
| `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4` | ✅ En disco | Video H.264 original sin marcas (vista paralela Panel 1) |
| Servidor Streamlit (`app.py`) | ✅ Activo (`:8501`) | Dashboard MATEO corriendo en `http://localhost:8501` |
| Servidor FastAPI + ngrok (`api_server.py`) | ⏳ No activo | Pendiente: lanzar para Orchestrate |

---

## 6. Pendiente y Hoja de Ruta (próximas sesiones)

1. **Terminar los experimentos restantes en local (GPU / clips pendientes)** y generar sus artefactos limpios (`data/clean/`, `data/audio/`, videos H.264 sin radar y radar 2D independiente).
2. **Fase 1 Cloud — Despliegue para la prueba en IBM Cloud:**
   - Empaquetar y desplegar el MVP demostrable en **IBM Cloud Code Engine** (`deploy_code_engine.py` + contenedor ligero con los artefactos pre-procesados en GPU) e integrar `openapi_tool.yaml` en **IBM watsonx Orchestrate**.
3. **Fase 2 Cloud — Portafolio personal en Vercel:**
   - Una vez concluida la prueba en IBM, construir el frontend web estático/interactivo sincronizado al milisegundo (3 videos H.264 en paralelo + métricas + transcriptor TTS) para desplegarlo en **Vercel**.

---

## 7. Respaldo y Blindaje para continuar en IBM Bob

Para continuar iterando sobre la plataforma en **IBM Bob** sin riesgo de perder el estado funcional actual, se dejaron configurados dos mecanismos de protección:

### 7.1 Snapshot de código en Git (rama y tag `mateo-v1-estable`)
Todo el código del dashboard MATEO (`implementacion/dashboard/app.py`, `implementacion/dashboard/pages/1_Observabilidad.py`, `.streamlit/config.toml`), los scripts generadores H.264 (`scripts/render_post_engine_video.py`, `scripts/finalize_mvp_perception.py`) y esta sesión (`bob_sessions/sesion_06_mateo_dashboard.md`) quedaron guardados en un commit limpio y respaldados en la rama/tag `mateo-v1-estable`:

```powershell
# Ver diferencias contra la versión estable en cualquier momento:
git diff mateo-v1-estable

# Restaurar solo el dashboard si alguna edición nueva falla:
git checkout mateo-v1-estable -- implementacion/dashboard/
```

### 7.2 Respaldo local de artefactos de `clip_13` (`backups/clip_13_estable/`)
Si durante las pruebas en IBM Bob se ejecuta `run_pipeline.py` sin `--use-real` (lo cual sobreescribiría `data/clean/` y `data/audio/` con datos sintéticos), todos los archivos reales de `clip_13` están respaldados en `backups/clip_13_estable/`:
- `backups/clip_13_estable/clean/` — 11 archivos (`2.17 MB`: parquets limpios, `tactical_summaries.json`, `narrations.json`, `narrations_es.vtt`, `governance_audit.jsonl`, `monitor_m1..m4.json`)
- `backups/clip_13_estable/audio/` — 9 archivos (`3.82 MB`: `W0.wav`–`W7.wav` y `NARRACION_COMPLETA_60S.wav`)
- `backups/clip_13_estable/videos_clip_13/` — 3 videos H.264 (`59.12 MB`: `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4`, `VIDEO_RADAR_POST_MATEMATICA.mp4`, `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4`)

Para restaurar todos los datos, audios y videos de `clip_13` en 1 segundo:
```powershell
.\.venv\Scripts\python.exe scripts/restore_clip13_backup.py
```
