# Catálogo de Datasets y Clasificación por Calidad — Mundial FIFA Brasil 2014

**Fuente original:** Hugging Face [`QimingLi/video_human_select_Soccer`](https://huggingface.co/datasets/QimingLi/video_human_select_Soccer/tree/main/Soccer)  
**Partido seleccionado para el MVP:** Semifinal Copa Mundial de la FIFA Brasil 2014 — **Brasil vs. Alemania (1–7)**  
**Prefijo identificador:** `L6sbfskaTDQ`  
**Audio:** Todos los clips incluyen pista de audio original (sonido ambiente de estadio + narración de transmisión).

---

## 1. Grupo A — Alta Calidad (`720p HD`) → Uso Principal en el MVP
**Ubicación:** `data/videos/mundial_2014_720p_hd/`  
**Recomendación técnica:** Usar este grupo para la extracción de telemetría con `YOLOv8x` (`imgsz=1280`), detección de balón con `InferenceSlicer` (`640×640`) y clasificación de equipos con `SigLIP`.

| # | Archivo | Resolución | Peso (MB) | Ruta relativa |
| :---: | :--- | :---: | :---: | :--- |
| 1 | `L6sbfskaTDQ-720-1.mp4` | 1280×720 (HD) | 12.70 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-1.mp4` |
| 2 | `L6sbfskaTDQ-720-2.mp4` | 1280×720 (HD) | 13.99 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-2.mp4` |
| 3 | `L6sbfskaTDQ-720-3.mp4` | 1280×720 (HD) | 17.14 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-3.mp4` |
| 4 | `L6sbfskaTDQ-720-4.mp4` | 1280×720 (HD) | 20.67 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-4.mp4` |
| 5 | `L6sbfskaTDQ-720-5.mp4` | 1280×720 (HD) | 21.89 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-5.mp4` |
| 6 | `L6sbfskaTDQ-720-6.mp4` | 1280×720 (HD) | 17.99 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-6.mp4` |
| 7 | `L6sbfskaTDQ-720-7.mp4` | 1280×720 (HD) | 15.98 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-7.mp4` |
| 8 | `L6sbfskaTDQ-720-8.mp4` | 1280×720 (HD) | 14.57 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-8.mp4` |
| 9 | `L6sbfskaTDQ-720-9.mp4` | 1280×720 (HD) | 16.50 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-9.mp4` |
| 10 | `L6sbfskaTDQ-720-10.mp4` | 1280×720 (HD) | 17.62 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-10.mp4` |
| 11 | `L6sbfskaTDQ-720-11.mp4` | 1280×720 (HD) | 17.05 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-11.mp4` |
| 12 | `L6sbfskaTDQ-720-12.mp4` | 1280×720 (HD) | 17.26 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-12.mp4` |
| 13 | `L6sbfskaTDQ-720-13.mp4` | 1280×720 (HD) | 22.40 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4` |
| 14 | `L6sbfskaTDQ-720-14.mp4` | 1280×720 (HD) | 18.55 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-14.mp4` |
| 15 | `L6sbfskaTDQ-720-15.mp4` | 1280×720 (HD) | 16.37 MB | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-15.mp4` |

**Total Alta Calidad (720p HD):** 15 clips · **260.68 MB**

---

## 2. Grupo B — Baja Calidad (`480p SD`) → Uso Secundario / Benchmark de Degradación
**Ubicación:** `data/videos/mundial_2014_480p_sd/`  
**Recomendación técnica:** Reservar únicamente para pruebas de robustez a baja resolución o previsualización ligera.

| # | Archivo | Resolución | Peso (MB) | Ruta relativa |
| :---: | :--- | :---: | :---: | :--- |
| 1 | `L6sbfskaTDQ-480-1.mp4` | 854×480 (SD) | 7.41 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-1.mp4` |
| 2 | `L6sbfskaTDQ-480-2.mp4` | 854×480 (SD) | 7.84 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-2.mp4` |
| 3 | `L6sbfskaTDQ-480-3.mp4` | 854×480 (SD) | 9.88 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-3.mp4` |
| 4 | `L6sbfskaTDQ-480-4.mp4` | 854×480 (SD) | 11.70 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-4.mp4` |
| 5 | `L6sbfskaTDQ-480-5.mp4` | 854×480 (SD) | 12.76 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-5.mp4` |
| 6 | `L6sbfskaTDQ-480-6.mp4` | 854×480 (SD) | 10.49 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-6.mp4` |
| 7 | `L6sbfskaTDQ-480-7.mp4` | 854×480 (SD) | 9.28 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-7.mp4` |
| 8 | `L6sbfskaTDQ-480-8.mp4` | 854×480 (SD) | 8.46 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-8.mp4` |
| 9 | `L6sbfskaTDQ-480-9.mp4` | 854×480 (SD) | 9.56 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-9.mp4` |
| 10 | `L6sbfskaTDQ-480-10.mp4` | 854×480 (SD) | 10.25 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-10.mp4` |
| 11 | `L6sbfskaTDQ-480-11.mp4` | 854×480 (SD) | 9.93 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-11.mp4` |
| 12 | `L6sbfskaTDQ-480-12.mp4` | 854×480 (SD) | 9.83 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-12.mp4` |
| 13 | `L6sbfskaTDQ-480-13.mp4` | 854×480 (SD) | 12.71 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-13.mp4` |
| 14 | `L6sbfskaTDQ-480-14.mp4` | 854×480 (SD) | 10.62 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-14.mp4` |
| 15 | `L6sbfskaTDQ-480-15.mp4` | 854×480 (SD) | 9.27 MB | `data/videos/mundial_2014_480p_sd/L6sbfskaTDQ-480-15.mp4` |

**Total Baja Calidad (480p SD):** 15 clips · **148.09 MB**
