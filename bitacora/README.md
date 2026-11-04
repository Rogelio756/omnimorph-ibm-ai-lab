# Bitácora General del Proyecto — Omnimorph

> **Directorio oficial de registro y trazabilidad:** `bitacora/`  
> Contiene el índice de sesiones, el catálogo de datasets por calidad, la estructura de salidas (`experimentos` vs `mvp_pruebas`) y el historial cronológico completo.

---

## 1. Organización Profesional del Proyecto

### 1.1 Separación de Datos por Calidad (`data/videos/`)
Todos los clips seleccionados pertenecen al partido **Brasil vs. Alemania (1–7)** de la Semifinal del **Mundial FIFA Brasil 2014** (`L6sbfskaTDQ`), separados estrictamente por resolución y calidad:

| Carpeta | Calidad / Resolución | Uso asignado | Archivos (`.mp4` con audio) | Peso total |
| :--- | :--- | :--- | :---: | :---: |
| [`data/videos/mundial_2014_720p_hd/`](../data/videos/mundial_2014_720p_hd/) | **Alta Calidad (720p HD)** | **Pruebas principales del MVP** (Percepción YOLOv8x, Inferencia de Balón `InferenceSlicer`, SigLIP y Dashboard) | 15 (`L6sbfskaTDQ-720-1.mp4` … `15.mp4`) | **260.68 MB** |
| [`data/videos/mundial_2014_480p_sd/`](../data/videos/mundial_2014_480p_sd/) | **Baja Calidad (480p SD)** | Pruebas ligeras de streaming, baja latencia o validación de degradación visual | 15 (`L6sbfskaTDQ-480-1.mp4` … `15.mp4`) | **148.09 MB** |

---

### 1.2 Separación de Salidas: Experimentos vs. Pruebas del MVP (`outputs/`)

| Ruta | Propósito | Contenido |
| :--- | :--- | :--- |
| [`outputs/experiment/`](../outputs/experiment/) | **Experimentos A / B / C / C2** (Benchmark arquitectónico inicial sobre `2e57b9_0.mp4`) | Telemetría real base (`C_data/frames.parquet`, `objects.parquet`, `timings.parquet`), logs de GPU/RAM y videos comparativos |
| [`outputs/experimentos/corrida_inicial_2e57b9/`](../outputs/experimentos/corrida_inicial_2e57b9/) | **Corridas individuales de los 6 modos** sobre el clip base `2e57b9_0.mp4` | `PITCH_DETECTION.mp4`, `PLAYER_DETECTION.mp4`, `BALL_DETECTION.mp4`, `PLAYER_TRACKING.mp4`, `TEAM_CLASSIFICATION.mp4`, `RADAR.mp4`, `frames/` y `metrics.jsonl` |
| [`outputs/mvp_pruebas/mundial_2014_brasil_alemania/`](../outputs/mvp_pruebas/mundial_2014_brasil_alemania/) | **Salidas exclusivas de las pruebas del MVP (Mundial Brasil 2014)** | Parquets de percepción (`frames.parquet`, `objects.parquet`, `timings.parquet`), métricas y videos renderizados de cada clip `L6sbfskaTDQ-720-*` |

---

## 2. Índice de Registros en `bitacora/`

1. [`bitacora/CATALOGO_DATASETS_Y_CALIDAD.md`](CATALOGO_DATASETS_Y_CALIDAD.md) — Inventario detallado de los 30 clips del Mundial 2014 (720p HD vs. 480p SD) y pesos exactos.
2. [`bitacora/REGISTRO_EJECUCIONES_MVP.md`](REGISTRO_EJECUCIONES_MVP.md) — Tabla de control de corridas del MVP, estado de los 9 monitores (`M1`, `M2.0–M2.5`, `M3`, `M4`) y tiempos de inferencia.
3. [`bitacora/HISTORIAL_SESIONES.md`](HISTORIAL_SESIONES.md) — Bitácora técnica acumulada desde la Sesión 1 hasta la Sesión 6.
