# Sesión 02 — IBM Bob IDE
## Experimento A/B/C/C2: Pipeline Unificado de Percepción
**Fecha:** 2026-10-13
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA
**Equipo:** Rogelio Leonardo Mendez Macias
**Herramientas IBM utilizadas:** IBM Bob IDE

---

## Objetivo de la sesión

Medir si ejecutar los 6 modos de percepción en un único proceso (compartiendo modelos y decodificación de video) es más rápido y produce los mismos datos que ejecutarlos en serie independiente.

---

## Trabajo realizado con IBM Bob IDE

IBM Bob asistió en el diseño del experimento comparativo, la implementación de `run_together.py` y la validación de equivalencia entre las pruebas A y C.

### Diseño experimental

| Prueba | Descripción | Script |
|---|---|---|
| **A_data** | 6 modos en serie, sin video, capturando datos | `capture_a.py` |
| **C_data** | Un proceso unificado, un paso de decodificación | `run_together.py --no-video` |
| **C_video** | C_data + escritura de 6 videos anotados | `run_together.py` |
| **C2_video** | C_video con 3 hilos (decode → GPU → draw/write) | `run_together.py --threads` |
| **B** | 6 procesos paralelos simultáneos (detenido a los 10 min) | `run_experiment.py` |

### Resultados de rendimiento

| Prueba | Tiempo total | FPS bucle | VRAM Δ | Freno dominante |
|---|---|---|---|---|
| A_data (suma) | 2 328 s | 1.3–15.8 por modo | ≤ 1.5 GB/modo | Potencia (SwPowerCap) |
| **C_data** | **1 316 s (−43%)** | 0.683 | 2.5 GB | Potencia |
| C_video | 1 520 s | 0.578 | 2.4 GB | Potencia |
| C2_video | 1 335 s | 0.677 | 2.4 GB | Potencia |
| B | Detenida a 600 s | — | 5.8 GB | Termico (65%) |

### Validacion de equivalencia C vs A — 100% en todos los chequeos

- 17 951 / 17 951 cajas con IoU medio = 1.0 (PLAYER_DETECTION)
- 687 / 687 detecciones de balon emparejadas
- 17 232 / 17 232 mismos `track_id` (PLAYER_TRACKING)
- 15 459 / 15 459 mismo equipo asignado (TEAM_CLASSIFICATION)
- 750 / 750 cuadros con homografia valida (RADAR)
- 19 407 / 19 407 keypoints a 0.0 px de diferencia (PITCH)

### Cuellos de botella identificados (ms/frame, media)

| Etapa | ms/frame | % del total |
|---|---|---|
| decode | 6.6 | 0.5% |
| pitch | 54.0 | 3.7% |
| player | 185.3 | 12.7% |
| **ball (InferenceSlicer)** | **749.7** | **51.2%** |
| tracking | 5.8 | 0.4% |
| **teams (SigLIP+UMAP+KMeans)** | **460.8** | **31.5%** |
| homography | 1.1 | 0.1% |

### Datos exportados a parquet

| Archivo | Contenido |
|---|---|
| `objects.parquet` | Una fila por objeto y cuadro (frame, source, track_id, class_id, team, x1..y2, pitch_x, pitch_y) |
| `frames.parquet` | Una fila por cuadro (keypoints x32, matriz H, n_det, ball_found) |
| `timings.parquet` | ms por etapa por cuadro |

### Hallazgo sobre throttling

El limitante real es el **cap de potencia (~55 W, Max-Q)**: 95% de las muestras activan `SwPowerCap`. El freno termico es casi nulo (< 0.2%). Solo en B (6 procesos simultaneos) el freno termico domino (65%).

---

## Arquitectura resultante — `run_together.py`

```
Pipeline  →  Renderer  →  Recorder
  pitch_model     draw() x6    objects.parquet
  player_model    write() x6   frames.parquet
  ball_model                   timings.parquet
  tracker
  team_classifier
```

Tres clases con responsabilidades separadas, estado compartido por sesion, dict inmutable por cuadro como contrato entre etapas.

---

## Tokens y metricas de sesion

| Metrica | Valor |
|---|---|
| Herramienta | IBM Bob IDE |
| Modelo asistente | IBM Bob |
| Tarea principal | Diseno e implementacion del pipeline unificado run_together.py |
| Archivos analizados | 8 archivos Python |
| Archivos generados | run_together.py, capture_a.py, run_experiment.py + 3 parquet |
| Reduccion de tiempo | -43% (2328 s -> 1316 s) |
