# Sesión 01 — IBM Bob IDE
## Evaluación inicial del repositorio `roboflow/sports`
**Fecha:** 2026-10-08
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA
**Equipo:** Rogelio Leonardo Mendez Macias
**Herramientas IBM utilizadas:** IBM Bob IDE

---

## Objetivo de la sesión

Evaluar el repositorio `roboflow/sports` (commit `42c80c06`) sobre el video de muestra `2e57b9_0.mp4` (1920×1080, 25 fps, 750 frames = 30 s) e identificar los modelos de percepción disponibles para construir el pipeline Omnimorph.

Hardware: Intel i7-9750H · GTX 1660 Ti Max-Q 6 GB · 23.8 GB RAM · Windows 11.

---

## Trabajo realizado con IBM Bob IDE

### Análisis del repositorio
IBM Bob asistió en la lectura y análisis del código fuente de `roboflow/sports`, identificando:
- 6 modos de percepción: `PITCH_DETECTION`, `PLAYER_DETECTION`, `BALL_DETECTION`, `PLAYER_TRACKING`, `TEAM_CLASSIFICATION`, `RADAR`
- Incompatibilidad crítica con `supervision >= 0.24` (parámetro `overlap_filter_strategy` eliminado)
- Dependencia no fijada en `requirements.txt`

### Resultados de evaluación por modo

| Modo | Resultado | FPS | Notas |
|---|---|---|---|
| `PITCH_DETECTION` | PASS | 9.58 | YOLOv8x-pose |
| `PLAYER_DETECTION` | PASS | 3.49 | YOLOv8x imgsz=1280 |
| `BALL_DETECTION` | PASS (sv 0.23.0) | 0.95 | InferenceSlicer, falla con sv>=0.24 |
| `PLAYER_TRACKING` | PASS | 3.29 | ByteTrack |
| `TEAM_CLASSIFICATION` | PASS | 1.12 | SigLIP + UMAP + KMeans |
| `RADAR` | PASS | 0.99 | Homografía + proyección 2D |

### Archivos generados

- `scripts/run_mode.py` — wrapper sin GUI con métricas de tiempo/FPS/RAM/VRAM
- `scripts/run_all.sh` — orquestación de los 6 modos
- `scripts/extract_frames.py` — extracción de cuadros para revisión visual

### Problemas resueltos

1. `supervision` sin versión fija → `pip install supervision==0.23.0`
2. `main.py` abría ventanas `cv2.imshow` → reemplazado por `scripts/run_mode.py`
3. PATH del sistema con rutas en unidad `E:` ilegible → filtrado de PATH antes de `pip install`
4. `setup.sh` en bash → replicado con `gdown` en PowerShell

---

## Decisión de arquitectura

IBM Bob recomendó adoptar el pipeline unificado `run_together.py` (pipeline C_data) en lugar de los 6 modos independientes, reduciendo el tiempo total en 43% (2328 s → 1316 s).

---

## Tokens y métricas de sesión

| Métrica | Valor |
|---|---|
| Herramienta | IBM Bob IDE |
| Modelo asistente | IBM Bob |
| Tarea principal | Análisis y diagnóstico del repositorio roboflow/sports |
| Archivos analizados | 12 archivos Python + requirements.txt |
| Archivos generados | 3 scripts nuevos |
