# Sesión 11 — Percepción sobre Costa Rica vs. San Cristóbal y Nieves (Clip 15)
**Fecha:** 2026-11-09  
**Agente:** Gemini (Antigravity)  
**Rama:** `feat-costa-rica`  
**Encargo:** `blueprints/encargo_gemini_percepcion_costa_rica.md`

---

## 1. Cambios en scripts de percepción (Paso 1)

Se parametrizaron las etiquetas que estaban escritas a mano para Brasil vs. Alemania en:
- `scripts/run_mvp_perception.py`
- `scripts/finalize_mvp_perception.py`

Se añadieron los argumentos opcionales `--team0-label`, `--team1-label`, `--match-label` y `--project-label` conservando los valores de Brasil 2014 como predeterminados (`"Brasil (Eq 0)"`, `"Alemania (Eq 1)"`, `"Brasil vs. Alemania (1-7) — Semifinal"` y `"Omnimorph MVP — Mundial FIFA Brasil 2014"`), de modo que la ejecución sin banderas adicionales produce exactamente la misma salida anterior.

---

## 2. Comandos ejecutados (Paso 2)

### 2.1. Inferencia completa de los 6 modelos en GPU (`run_mvp_perception.py`)
```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe scripts/run_mvp_perception.py `
  --source data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4 `
  --outdir outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15 `
  --max-frames 1080 --device cuda `
  --team0-label "Costa Rica (Eq 0)" --team1-label "SKN (Eq 1)" `
  --match-label "Costa Rica vs. San Cristóbal y Nieves — Eliminatorias Concacaf 2026" `
  --project-label "Omnimorph MVP — Eliminatorias Concacaf 2026"
```

### 2.2. Ajuste de etiquetas tras verificar el mapeo de KMeans (`finalize_mvp_perception.py`, sin GPU)
Tras inspeccionar `TEAM_CLASSIFICATION.mp4` en los segundos 5, 18 y 30 y confirmar que `team_id = 0` corresponde al uniforme verde (San Cristóbal y Nieves) y `team_id = 1` al uniforme guinda/rojo oscuro (Costa Rica), se re-ensamblaron las salidas unificadas sin repetir inferencia GPU:

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe scripts/finalize_mvp_perception.py `
  --source data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4 `
  --outdir outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15 `
  --max-frames 1080 `
  --team0-label "SKN (Eq 0)" --team1-label "Costa Rica (Eq 1)" `
  --match-label "Costa Rica vs. San Cristóbal y Nieves — Eliminatorias Concacaf 2026" `
  --project-label "Omnimorph MVP — Eliminatorias Concacaf 2026"
```

---

## 3. Mapeo de equipos y sentido de ataque (para `partido.config.json`)

| `team_id` | Equipo | Código | Uniforme | Color en video | Portería que defiende | Sentido de ataque | Mediana `pitch_x` (cm) por tramo (f0–270 / f270–540 / f540–810 / f810–1080) |
|---|---|---|---|---|---|---|---|
| **`0`** | **San Cristóbal y Nieves** | `SKN` | Verde | Rosa (`#FF1493`) | Izquierda (`X = 0`) | **`+x`** (izquierda → derecha, hacia `X = 12 000`) | `6512` / `6885` / `5614` / `5681` |
| **`1`** | **Costa Rica** | `CRC` | Guinda / rojo oscuro | Azul celeste (`#00BFFF`) | Derecha (`X = 12 000`) | **`-x`** (derecha → izquierda, hacia `X = 0`) | `7153` / `8127` / `6054` / `6888` |

- En los segundos 25 a 36 (frames 750–1079) se observa el borde del área grande izquierda con la línea defensiva verde (`SKN`, `team_id = 0`) replegada defendiendo su arco (`X = 0`) ante el avance de los jugadores guindas (`CRC`, `team_id = 1`) que atacan en dirección `-x`.

---

## 4. Tabla de verificación y mediciones (Paso 3)

| # | Comprobación | Resultado medido | Estado |
|---|---|---|---|
| **1** | **Salidas completas** | En `outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15/`:<br>• 6 JSON en `json_por_modelo/`: `PITCH_DETECTION.json` (1 818.2 KB), `PLAYER_DETECTION.json` (5 687.2 KB), `BALL_DETECTION.json` (277.1 KB), `PLAYER_TRACKING.json` (4 955.3 KB), `TEAM_CLASSIFICATION.json` (4 878.3 KB), `RADAR.json` (2 907.6 KB)<br>• 6 MP4 en `videos_por_modelo/`: `PITCH_DETECTION.mp4` (26.1 MB), `PLAYER_DETECTION.mp4` (33.9 MB), `BALL_DETECTION.mp4` (23.7 MB), `PLAYER_TRACKING.mp4` (29.9 MB), `TEAM_CLASSIFICATION.mp4` (33.2 MB), `RADAR.mp4` (34.9 MB)<br>• Raíz: `TELEMETRIA_UNIFICADA_COMPLETA.json` (2 845.2 KB), `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4` (H.264, 39.5 MB), `frames.parquet` (583.4 KB), `objects.parquet` (1 044.0 KB, 40 891 filas) | **OK** |
| **2** | **Cuadros procesados** | `len(pd.read_parquet("frames.parquet")) = 1080` (segundos 0.0 a 36.0 a 29.97 fps; `VideoSink` reporta 29.00 fps enteros en cabecera OpenCV). | **OK (1080)** |
| **3** | **Equipos** | **`team_id = 0` → San Cristóbal y Nieves (verde)** (7 972 detecciones trackeadas); **`team_id = 1` → Costa Rica (guinda)** (7 949 detecciones trackeadas).<br>• **s = 5 (frame 150):** 8 jugadores SKN (`tid` 1, 3, 8, 9, 11, 22, 25, 29) en `team_id=0` y 10 jugadores CRC (`tid` 2, 6, 12, 18, 20, 26, 27, 28, 30, 33) en `team_id=1`. **0 jugadores mal asignados de equipo.**<br>• **s = 18 (frame 540):** 5 jugadores SKN (`tid` 8, 25, 29, 36, 42) en `team_id=0` y 6 jugadores CRC (`tid` 6, 28, 30, 37, 57, 58) en `team_id=1`. **0 jugadores mal asignados de equipo.**<br>• **s = 30 (frame 900):** 9 jugadores SKN (`tid` 25, 67, 73, 77, 93, 96, 98, 99, 101) en `team_id=0` y 5 jugadores CRC (`tid` 28, 60, 69, 70, 74) en `team_id=1`. **2 errores en ese cuadro:**<br>  1. `tid = 29` cambió de persona en un cruce previo (era un jugador verde de SKN en s=5 y s=18, y en s=30 sigue al dorsal #14 guinda de CRC con `team_id=1`, además de solaparse con el árbitro `tid=7`).<br>  2. `tid = 59` (dorsal #17 guinda de CRC) aparece en ese cuadro clasificado como `referee` (`class_id=3`, amarillo) al cruzarse con el dorsal #21 de CRC (`tid=69`).<br>• **Global en los 1080 cuadros:** de 84 `track_id` de clase `player`, 62 mantienen el mismo `team_id` en el 100 % de sus apariciones y 22 sufren algún parpadeo puntual de `team_id` (en 19 de ellos son solo 1 a 7 cuadros aislados; el único con mezcla prolongada es `tid=29` con 595 cuadros en `0` y 320 en `1` por cambio de identidad tras cruce). | **OK (con observaciones)** |
| **4** | **Porteros y árbitro** | • **Árbitro central (amarillo, `tid=7` en f3..956 y `tid=105` en f965..1079) y juez de línea superior (`tid=80` / `tid=100`):** detectados como `referee` (`class_id=3`) en **1 050 de 1 080 cuadros** (1 021 cuadros con track activo, 1 507 filas en `objects.parquet`), con `team = NaN` (fuera de ambos equipos). Sin embargo, en **55 cuadros** el árbitro central (`tid=7`) fue clasificado momentáneamente por YOLO como `player` (36 cuadros asignado a `team_id=0` y 19 a `team_id=1`), y en `tid=105` ocurrió en 7 cuadros.<br>• **Porteros (`class_id=1`, `goalkeeper`):** **0 detecciones en los 1 080 cuadros.** Durante los 36 segundos el plano táctico se mantiene entre el mediocampo y tres cuartos de cancha sin enfocar nunca las áreas chicas ni las porterías, por lo que ningún portero entra en cuadro. | **Árbitro separado (94.1 % como `referee`); porteros no visibles en el clip** |
| **5** | **Homografía** | **1 080 / 1 080 cuadros (100.00 %)** con matriz `H` válida (`homography_valid = True`, `n_kp_visible` mín = 19, mediana = 22, máx = 31).<br>• Nota técnica para Etapa 2 (M2.1): si se filtra por confianza `kp_conf >= 0.5`, **1 078 / 1 080 cuadros (99.81 %)** tienen ≥ 4 keypoints de alta confianza (mediana = 8 keypoints). | **100.00 % (≥ 90 %)** |
| **6** | **Radar** | De **17 428 proyecciones cenitales** en `objects.parquet` (`source == 'track'`):<br>• **16 810 (96.45 %)** caen estrictamente dentro de `0–12 000 × 0–7 000 cm`.<br>• **17 220 (98.81 %)** caen dentro del margen con bandas (`-500–12 500 × -500–7 500 cm`), ya que 409 puntos corresponden al juez de línea en la banda norte (`pitch_y` entre `-120` y `0 cm`) o jugadores junto a la banda sur (`pitch_y` entre `7 000` y `7 500 cm`).<br>• **208 puntos (1.19 %)** en 147 cuadros presentan saltos fuera de `±5 m` (casos más severos en frames `27–28`, `141–145`, `698` y `1015`). Causa: `run_mvp_perception.py` usa `mask = (kp_x > 1) & (kp_y > 1)` sin umbral de confianza, incluyendo ~11 keypoints de baja confianza (`kp_conf < 0.5`) que `YOLOv8x-pose` deja pegados al borde derecho de la imagen (`x ≈ 1280`). | **96.45 % dentro de cancha (98.81 % con bandas)** |
| **7** | **Tracking** | • **Total `track_id` distintos:** **112** (rango `1` a `114`; 84 aparecen como `player`, 41 como `referee` y 26 como `ball`). Supera el ideal de `< 40` debido a re-identificaciones de ByteTrack cuando los jugadores salen por los bordes durante el paneo o se cruzan.<br>• **Cambios de clase dentro de un mismo `track_id`:** 39 de los 112 `track_id` cambian de clase en algún cuadro (33 alternan puntualmente entre `player` y `referee`, y 6 entre `ball` y `player` cuando el balón pasa por los pies). | **112 IDs distintos (fragmentación alta de ByteTrack crudo)** |
| **8** | **Balón** | **860 / 1 080 cuadros (79.63 %)** con balón detectado (`ball_found = True`, 2 547 detecciones crudas en `InferenceSlicer`). | **79.63 % (860/1080)** |
| **9** | **Costo (Tiempo y VRAM)** | • **Tiempo total `run_mvp_perception.py`:** **1 311.19 s (21 min 51 s)**<br>  - `PITCH_DETECTION`: 69.09 s<br>  - `PLAYER_DETECTION`: 214.69 s<br>  - `BALL_DETECTION`: 479.48 s<br>  - `PLAYER_TRACKING`: 19.86 s<br>  - `TEAM_CLASSIFICATION`: 452.53 s<br>  - `RADAR`: 44.44 s<br>  - `UNIFIED_EXPORT`: 31.10 s (`finalize_mvp_perception.py` tomó 56.17 s incluyendo transcodificación H.264)<br>• **VRAM pico medida (`nvidia-smi`):** **945 MiB** (~0.92 GiB). | **1 311.19 s / 945 MiB VRAM** |

Las capturas de verificación de los puntos 3, 4 y 6 quedaron guardadas en `outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15/capturas/` (`team_s05_f0150.png`, `team_s18_f0540.png`, `team_s30_f0900.png`, `radar_s05_f0150.png`, `radar_s18_f0540.png`, `radar_s30_f0900.png`, `unificado_s05_f0150.png`, `unificado_s18_f0540.png`, `unificado_s30_f0900.png`, además de cuadros diagnósticos adicionales).

---

## 5. Problemas detectados y puntos no verificables

1. **Keypoints de baja confianza en el borde derecho (`x ≈ 1280`):** `YOLOv8x-pose` predice entre 1 y 14 keypoints con coordenadas pegadas al borde derecho de la imagen (`x > 1265`) y baja confianza (`kp_conf < 0.5`). Como `RADAR` en `run_mvp_perception.py` filtra únicamente con `(kp_x > 1) & (kp_y > 1)` sin exigir `kp_conf >= 0.5`, esos puntos entran a `ViewTransformer` y comprimen ligeramente el radar crudo o provocan saltos en cuadros puntuales (ej. frame 698). El motor `omnimorph_engine.py` (Etapa 2, M2.1) sí aplica filtro de confianza y suavizado EMA, por lo que podrá corregirlo al leer `frames.parquet`.
2. **Cruces `player` ↔ `referee` y robo de ID (`tid = 29`):** Cuando dos jugadores se solapan o pasan junto al árbitro (por ejemplo, `tid=29` con `tid=7`, o `tid=59` con `tid=69` en el segundo 30), `ByteTrack` puede transferir el `track_id` entre jugadores de distinto equipo o `YOLOv8x` etiqueta durante pocos cuadros a un jugador guinda como `referee` (`class_id=3`). La moda de equipo por track y el Track Stitching de Etapa 2 (M2.0 y M2.2) son necesarios para limpiar estos cruces.
3. **Clasificación de porteros no verificable en este clip:** Ninguno de los dos porteros aparece en pantalla durante los primeros 36 segundos (`frames 0..1079`), por lo que no hubo instancias de `class_id = 1` (`goalkeeper`) para evaluar `resolve_goalkeepers_team_id`.
4. **Inyección de `ball` en `PLAYER_TRACKING`:** Como `PLAYER_DETECTION` también detecta ocasionalmente la clase `ball` (`class_id = 0`, 192 filas en `track`), `ByteTrack` le asigna `track_id` a algunas detecciones de balón (26 IDs de los 112 totales). El monitor M2.0 en `omnimorph_engine.py` ya filtra `class_id` antes del seguimiento táctico.
