# Reporte de capacidades — roboflow/sports (examples/soccer)

Fecha: 2026-10-08 · Repo evaluado: https://github.com/roboflow/sports, commit `42c80c06` (2025-05-27)
Todo se corrió localmente, sin entrenar nada, sobre el video de muestra `2e57b9_0.mp4`
(1920×1080, 25 fps, 750 cuadros = 30 s, video **completo**, sin recortar).

> **Resumen:** los 6 modos corren en esta laptop **en GPU**, pero **no “tal cual”**.
> El repo no fija versiones de dependencias; con la versión actual de `supervision` (0.30.9) fallan 3 de 6 modos.
> Con `supervision==0.25.1` corren 5 de 6; `BALL_DETECTION` además necesita `supervision<=0.23`.
> Velocidad: de 0.95 FPS (balón) a 9.6 FPS (cancha). Nada es tiempo real en esta GPU.

---

## 1. Especificaciones del equipo

| Componente | Valor |
|---|---|
| SO | Windows 11 Enterprise 10.0.26100 (64 bits) |
| CPU | Intel Core i7-9750H @ 2.60 GHz, 6 núcleos / 12 hilos |
| RAM | 23.8 GB (≈8 GB libres al empezar) |
| GPU | NVIDIA GeForce GTX 1660 Ti with Max-Q Design, 6 GB VRAM, driver 561.09 (CUDA 12.6) · más Intel UHD 630 |
| CUDA Toolkit (nvcc) | No instalado (no se necesita: PyTorch trae su runtime) |
| Python | 3.12.10 global (también 3.11). El venv reporta 3.12.2 |
| Disco | C: 259.7 GB libres · D: 402.3 GB libres |
| Entorno usado | venv `.venv`, torch 2.14.1+cu126, torchvision 0.29.1+cu126, ultralytics 8.4.174, transformers 5.19.0, umap-learn 0.5.12, scikit-learn 1.9.1, supervision (ver §6) |

Durante las pruebas la GPU tenía 1.2–2.0 GB ocupados por otras apps (Chrome, Slack, VS Code, etc.). Eso también se usaba para el escritorio, así que las cifras son de "uso normal de laptop", no de un benchmark limpio.

---

## 2. Tabla de modos

Corrida de referencia: **corrida 2** (`supervision==0.25.1`) para 5 modos y **corrida 3** (`supervision==0.23.0`) para `BALL_DETECTION`. Dispositivo: **GPU (cuda)** en todos.

- **FPS sostenido** = cuadros procesados ÷ tiempo desde el primer cuadro escrito. Excluye la carga de modelos y el ajuste del clasificador de equipos.
- **FPS total** = 750 ÷ tiempo total, todo incluido.
- **RAM** = pico de RSS del proceso. **VRAM** = pico de `nvidia-smi` menos la línea base de ese momento. **torch** = `torch.cuda.max_memory_allocated`.

| Modo | Qué hace | ¿Corrió? | FPS sostenido | FPS total | Tiempo total | Preparación | RAM pico | VRAM (Δ / torch) | Observaciones |
|---|---|---|---|---|---|---|---|---|---|
| `PITCH_DETECTION` | 32 puntos clave de la cancha (YOLOv8x-pose) | **Sí** | 9.58 | 6.41 | 117 s | 39 s | 1.6 GB | +0.8 GB / 0.6 GB | Bien en líneas visibles. Los puntos fuera de cuadro se apilan en el borde derecho de la imagen. Algún punto aislado mal ubicado (ej. #32 en medio campo, cuadro 700) |
| `PLAYER_DETECTION` | Cajas para balón / portero / jugador / árbitro (YOLOv8x, imgsz 1280) | **Sí** | 3.49 | 2.91 | 258 s | 43 s | 1.6 GB | +1.2 GB / 0.8 GB | Detecta casi a todos los jugadores, árbitro y jueces de línea. No marca al cuerpo técnico en la banda (correcto). El balón a veces sí, a veces no. Jugadores encimados comparten cajas |
| `BALL_DETECTION` | Balón con modelo dedicado + `InferenceSlicer` (cortes de 640×640) + rastro | **Sí, con supervision 0.23.0.** Falla con 0.25.1 y 0.30.9 | 0.95 | 0.91 | 827 s | 41 s | **5.6 GB** | +1.1 GB / 0.6 GB | El rastro sigue bien el balón en pases a ras de suelo (cuadros 300 y 500). Es el modo más lento y el que más RAM usa |
| `PLAYER_TRACKING` | Detección + ByteTrack (IDs persistentes) | **Sí** | 3.29 | 2.76 | 272 s | 44 s | 1.6 GB | +1.5 GB / 0.8 GB | IDs estables en tramos cortos. Hay **fragmentación**: con ~25 personas en el campo los IDs llegan a 43 en el cuadro 450 (corrida 1), o sea, se reasignan IDs nuevos. Este modo no distingue equipos |
| `TEAM_CLASSIFICATION` | Tracking + equipos con SigLIP → UMAP → KMeans(2), ajustado por video | **Sí** (falla con supervision 0.30.9) | 1.12 | 0.80 | 940 s | **269 s** | 1.9 GB | +1.7 GB / 1.2 GB | Separa bien blancos vs. oscuros en los cuadros revisados. Los porteros se asignan por cercanía al centroide del equipo (heurística): el portero rojo #10 (cuadro 100) quedó con el equipo oscuro, **probable error**. Árbitros en amarillo, correcto |
| `RADAR` | Todo lo anterior + homografía a vista cenital (minimapa) | **Sí** (falla con supervision 0.30.9) | 0.99 | 0.74 | 1019 s | **260 s** | 1.9 GB | +2.2 GB / 1.7 GB | La proyección es coherente con la escena: la mayoría de puntos caen en la zona correcta. Hay puntos sueltos en bordes y área chica que no corresponden, y parpadeo entre cuadros (el propio README lo lista como pendiente: "Add smoothing… flickering in RADAR mode") |

**Preparación** (`setup`) en `TEAM_CLASSIFICATION` y `RADAR` incluye: detectar jugadores en 1 de cada 60 cuadros, extraer embeddings SigLIP, UMAP y KMeans. SigLIP (`google/siglip-base-patch16-224`, ~780 MB) ya estaba en caché en la corrida 2; en la primera ejecución se descarga.

### Variación entre corridas (mismos modos, misma máquina)

| Modo | FPS sostenido corrida 1 (sv 0.30.9) | FPS sostenido corrida 2 (sv 0.25.1) |
|---|---|---|
| PITCH_DETECTION | 13.07 | 9.58 |
| PLAYER_DETECTION | 4.97 | 3.49 |
| PLAYER_TRACKING | 4.81 | 3.29 |

Bajó ~27–32 % en la segunda corrida, que se hizo después de ~25 min de carga continua en GPU. **No medí temperaturas ni relojes**, así que no puedo afirmar que fue throttling térmico; es la hipótesis más probable en una laptop Max-Q. Tomen las cifras como un rango, no como un número fijo.

### Errores exactos

| Corrida | Modo | Error |
|---|---|---|
| 1 (sv 0.30.9) | BALL_DETECTION | `TypeError: InferenceSlicer.__init__() got an unexpected keyword argument 'overlap_filter_strategy'` |
| 1 (sv 0.30.9) | TEAM_CLASSIFICATION | `TypeError: 'NoneType' object is not iterable` en `main.py:316` (`detections.tracker_id` es `None` en los primeros cuadros) |
| 1 (sv 0.30.9) | RADAR | Mismo error, `main.py:366` |
| 2 (sv 0.25.1) | BALL_DETECTION | Mismo `TypeError` de `overlap_filter_strategy` (el parámetro se eliminó en supervision 0.24) |

Logs completos en `runs/run*/logs/` y métricas crudas en `runs/run*/metrics.jsonl`.

---

## 3. Observaciones de los videos de salida

Cuadros revisados: 100, 300, 500 y 700 de cada video (en `outputs/frames/`). Son observaciones visuales de muestra, **no** una evaluación cuantitativa: no hay ground truth y no calculé precisión ni recall.

- **Jugadores no detectados:** en los cuadros revisados no vi jugadores de campo omitidos. Los casos dudosos son jugadores encimados (dos personas en una caja o etiquetas superpuestas, cuadro 300 cerca del círculo central).
- **Balón perdido:** en `PLAYER_DETECTION` el balón aparece en unos cuadros y en otros no. El modelo dedicado de `BALL_DETECTION` lo sigue mejor (rastro continuo en 300 y 500), pero cuesta ~4× más tiempo. No medí el % de cuadros con balón.
- **Cambios de ID:** en `PLAYER_TRACKING` los IDs se mantienen entre cuadros cercanos, pero la numeración crece por encima del número de personas (hasta 43). Hay reasignaciones tras oclusiones o salidas de cuadro. No hay re-identificación.
- **Errores al separar equipos:** los jugadores de campo quedan bien separados (blanco vs. azul oscuro). El punto débil son los **porteros**, que el código asigna por distancia a los centroides de cada equipo, no por apariencia (ver `resolve_goalkeepers_team_id` en `main.py`).
- **Proyección a la cancha:** la homografía depende de los puntos clave visibles. Los puntos fuera de cuadro se dibujan apilados en el borde. En `RADAR` hay puntos esporádicos mal proyectados y parpadeo.
- **Rectángulo negro** arriba a la derecha: **viene del video original**, lo comprobé en el cuadro 450 de la fuente (`runs/source_0450.jpg`). No es un error del modelo.

---

## 4. Clasificación de capacidades

| Capacidad | Estado | Evidencia / comentario |
|---|---|---|
| Detección de jugadores, porteros, árbitros | **Ya lo tenemos** | `PLAYER_DETECTION` corrió y se ve bien en los cuadros revisados |
| Detección de puntos clave de la cancha | **Ya lo tenemos** | `PITCH_DETECTION` |
| Seguimiento de jugadores (IDs) | **Hay que ajustarlo** | Funciona, pero fragmenta IDs; falta re-ID |
| Detección y seguimiento del balón | **Hay que ajustarlo** | Funciona solo con supervision ≤0.23 y a 0.95 FPS / 5.6 GB RAM |
| Separación de equipos | **Hay que ajustarlo** | Bien para jugadores de campo. Porteros por heurística. Requiere ~4.5 min de ajuste por video |
| Proyección a vista cenital (radar / coordenadas en cancha) | **Hay que ajustarlo** | Funciona con parpadeo y outliers; sin suavizado |
| Rendimiento en tiempo real | **Hay que ajustarlo** | 0.95–9.6 FPS en esta GPU; el video es de 25 fps |
| Fijación de dependencias / instalación reproducible | **Hay que ajustarlo** | El repo no fija versiones; ver §6 |
| Mapa de control territorial (Voronoi) y trayectorias en cancha | **Hay que ajustarlo** (existe en la librería, no en `main.py`) | `draw_pitch_voronoi_diagram` y `draw_paths_on_pitch` en `sports/annotators/soccer.py`. No los ejecuté |
| Detección de pases | **No existe en el repo** | Búsqueda en el código: no hay lógica de eventos |
| Detección de tiros | **No existe en el repo** | — |
| Posesión de balón | **No existe en el repo** | Hay balón y jugadores por separado, pero nada que asigne posesión |
| Lectura de dorsales (OCR) | **No existe en el repo** (para fútbol) | El README general enlaza un dataset de dorsales de **básquetbol**, pero no hay código ni modelo |
| Re-identificación de jugadores | **No existe en el repo** | El README la lista como "challenge" |
| Velocidad / distancia recorrida | **No existe en el repo** | Las coordenadas del radar lo permitirían, pero no está implementado |
| Exportar datos (CSV/JSON de posiciones) | **No existe en el repo** | El roadmap del README lo lista como pendiente |

---

## 5. Licencias

| Componente | Licencia | Fuente donde lo verifiqué | Estado |
|---|---|---|---|
| Repo `roboflow/sports` (código) | **MIT** (Copyright 2024 Roboflow) | Archivo `sports/LICENSE` del repo clonado; `setup.py` (`license='MIT'`) | Confirmado |
| Pesos `football-player/ball/pitch-detection.pt` | **AGPL-3.0** (Ultralytics YOLOv8) | Metadatos dentro de cada `.pt` (`license: 'AGPL-3.0 (https://ultralytics.com/license)'`, entrenados con ultralytics 8.2.10–8.2.64, base `yolov8x` / `yolov8x-pose`). README de examples/soccer: "YOLOv8, is distributed under the AGPL-3.0 license". [LICENSE de ultralytics](https://github.com/ultralytics/ultralytics/blob/main/LICENSE) | Confirmado |
| Librería `ultralytics` (necesaria para correr los pesos) | **AGPL-3.0** | [LICENSE de ultralytics](https://raw.githubusercontent.com/ultralytics/ultralytics/main/LICENSE) | Confirmado |
| SigLIP `google/siglip-base-patch16-224` | **Apache-2.0** | [Model card en Hugging Face](https://huggingface.co/google/siglip-base-patch16-224) (metadato `license: apache-2.0`) | Confirmado |
| `supervision` | MIT | README de examples/soccer, que enlaza su LICENSE | Según el README; no abrí el archivo LICENSE |
| Datasets de Roboflow Universe con que se entrenaron los pesos | **No confirmada** | Roboflow Universe devolvió 403 a la descarga automática y el navegador integrado no pudo leer la página | **No pude confirmarla** |
| Videos de muestra (`2e57b9_0.mp4`, etc.) | **No confirmada** | Según el README vienen de la competencia de Kaggle [DFL – Bundesliga Data Shootout](https://www.kaggle.com/competitions/dfl-bundesliga-data-shootout). Las reglas de Kaggle no se pudieron leer (página dinámica; el navegador falló con "Policy check temporarily unavailable"). Los videos se bajan de un Google Drive de Roboflow sin licencia indicada | **No pude confirmarla**. Son imágenes de partidos de la Bundesliga (DFL); asumir uso restringido hasta revisar las reglas |

**Implicación importante:** los pesos y `ultralytics` son **AGPL-3.0**. Si el sistema se ofrece como servicio en red o se distribuye, la AGPL obliga a publicar el código fuente, o bien a comprar la licencia comercial de Ultralytics. Esto hay que revisarlo con legal antes de usarlos en producto.

**Pendiente manual:** abrir con una sesión de Kaggle la pestaña *Rules* de la competencia y la página del dataset en Roboflow Universe para confirmar estas dos licencias.

---

## 6. Problemas encontrados en Windows y cómo se resolvieron

1. **pip fallaba al instalar torch** con `OSError: [WinError 1005] El volumen no contiene un sistema de archivos reconocido: 'E:\Android\SDK\cmdline-tools\tools\bin'`. El PATH del sistema incluye rutas en `E:`, una unidad ilegible, y pip revisa el PATH al instalar los ejecutables de consola.
   **Solución:** `pip install --no-warn-script-location ...` y quitar las entradas de `E:` del PATH **solo en esa sesión**. No se modificó el sistema. *Recomendación:* limpiar esas entradas del PATH de Windows.
2. **Incompatibilidad con `supervision`** (no es exclusivo de Windows). `requirements.txt` no fija versiones:
   - 0.30.9 (la más reciente): fallan BALL, TEAM_CLASSIFICATION y RADAR.
   - 0.25.1: funcionan todos menos BALL.
   - 0.23.0: BALL funciona (con aviso de parámetro obsoleto).
   No probé los 6 modos con 0.23.0, así que no sé si una sola versión sirve para todo.
3. **`setup.sh` es de bash.** No lo ejecuté; hice las mismas descargas con `gdown` desde el venv. Solo bajé los 3 modelos y el video `2e57b9_0.mp4`; los otros 4 videos de muestra no se usaron.
4. **`main.py` abre ventanas `cv2.imshow`** en cada cuadro. Para medir sin abrir ventanas en el escritorio usé `scripts/run_mode.py`, que llama a las mismas funciones `run_*` de `main.py` (sin modificarlo) y escribe el video con el mismo `sv.VideoSink`.
5. **Archivos fuera de `omnimorph-pruebas`** (avisar):
   - `C:\Users\Dell G3\AppData\Roaming\Ultralytics\settings.json`: lo creó ultralytics en la primera inspección de los modelos, antes de fijar `YOLO_CONFIG_DIR`.
   - Caché de pip en `%LOCALAPPDATA%\pip\cache`, con el wheel de torch de 2.6 GB. Se puede liberar con `.venv\Scripts\python.exe -m pip cache purge`.
6. Instalar supervision 0.23.0 agregó `opencv-python-headless` junto a `opencv-python`. No causó errores en esta prueba.

---

## 7. Comandos exactos para reproducir

En **PowerShell**, desde `C:\Users\Dell G3\Downloads`:

```powershell
# 1. Carpeta, repo y venv
New-Item -ItemType Directory -Force omnimorph-pruebas | Out-Null
Set-Location omnimorph-pruebas
git clone https://github.com/roboflow/sports.git
git -C sports checkout 42c80c06b6b65a7f89455b89fe31cdf4c38ba227
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# (solo si tu PATH tiene unidades ilegibles, como E: aquí)
$env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notlike 'E:\*' }) -join ';'

# 2. PyTorch con CUDA 12.6 (descarga de ~2.6 GB)
.\.venv\Scripts\python.exe -m pip install --no-warn-script-location --index-url https://download.pytorch.org/whl/cu126 torch==2.14.1+cu126 torchvision==0.29.1+cu126

# 3. Paquete sports + requirements del ejemplo + psutil (para las métricas)
.\.venv\Scripts\python.exe -m pip install --no-warn-script-location ./sports -r sports/examples/soccer/requirements.txt psutil
.\.venv\Scripts\python.exe -m pip install --no-warn-script-location supervision==0.25.1

# 4. Equivalente de setup.sh: modelos y un video
New-Item -ItemType Directory -Force sports\examples\soccer\data | Out-Null
$g = ".\.venv\Scripts\gdown.exe"; $d = "sports\examples\soccer\data"
& $g -O "$d\football-ball-detection.pt"   "https://drive.google.com/uc?id=1isw4wx-MK9h9LMr36VvIWlJD6ppUvw7V"
& $g -O "$d\football-player-detection.pt" "https://drive.google.com/uc?id=17PXFNlx-jI7VjVo_vQnB1sONjRyvoB-q"
& $g -O "$d\football-pitch-detection.pt"  "https://drive.google.com/uc?id=1Ma5Kt86tgpdjCTKfum79YMgNnSjcoOyf"
& $g -O "$d\2e57b9_0.mp4"                 "https://drive.google.com/uc?id=19PGw55V8aA6GZu5-Aac5_9mCy3fNxmEf"

# 5. Correr los 6 modos con métricas (necesita Git Bash; deja los videos en outputs\<MODO>.mp4)
bash scripts/run_all.sh cuda

# 6. BALL_DETECTION necesita supervision<=0.23
.\.venv\Scripts\python.exe -m pip install --no-warn-script-location supervision==0.23.0
$env:HF_HOME = "$PWD\.hf_cache"; $env:YOLO_CONFIG_DIR = "$PWD\.ultralytics"
.\.venv\Scripts\python.exe scripts\run_mode.py --mode BALL_DETECTION --source sports\examples\soccer\data\2e57b9_0.mp4 --target outputs\BALL_DETECTION.mp4 --device cuda

# 7. Cuadros para revisión visual
.\.venv\Scripts\python.exe scripts\extract_frames.py 100 300 500 700
```

Para correr un modo **tal como lo documenta el repo** (abre una ventana de vista previa; `q` para salir):

```powershell
Set-Location sports\examples\soccer
..\..\..\.venv\Scripts\python.exe main.py --source_video_path data/2e57b9_0.mp4 --target_video_path ../../../outputs/RADAR_main.mp4 --device cuda --mode RADAR
```

---

## 8. Estructura de la carpeta

```
omnimorph-pruebas/
├── REPORTE.md                  ← este archivo
├── .venv/                      ← entorno virtual (no se tocó el Python global)
├── .hf_cache/                  ← SigLIP (~780 MB)
├── sports/                     ← repo clonado (sin modificar); modelos y video en sports/examples/soccer/data/
├── .sv023/                     ← supervision 0.23.0 aislado (solo para BALL original, vía PYTHONPATH)
├── scripts/
│   ├── run_mode.py             ← corre un modo y mide tiempo/FPS/memoria
│   ├── run_all.sh              ← corre los 6 modos
│   ├── extract_frames.py       ← saca cuadros para revisión
│   ├── run_together.py         ← §9: prueba C / C2 (6 modos en un proceso, parquet, ms por etapa)
│   ├── capture_a.py            ← §9: datos de un modo original (A) para validar
│   ├── validate.py             ← §9: compara datos C vs A
│   ├── run_experiment.py       ← §9: orquesta C_data → C_video → C2 → B → A_data → validación
│   ├── summarize_experiment.py ← §9: tablas a partir de outputs/experiment/
│   ├── exp_common.py           ← §9: semillas, nvidia-smi cada 1 s, parquet
│   └── monitor.py              ← §9: monitor en vivo en terminal
├── outputs/                    ← videos finales <MODO>.mp4, metrics.jsonl, frames/
│   └── experiment/             ← §9: una carpeta por fase, gpu_*.csv, ram_*.csv, phases.jsonl, summary.md
├── logs/                       ← log de la última corrida por modo
└── runs/
    ├── run1_supervision-0.30.9/  ← corrida "tal cual" (3 fallos) con sus videos y logs
    ├── run2_supervision-0.25.1/  ← métricas y logs de la corrida de referencia
    └── run3_ball_supervision-0.23.0/
```

---

## 9. Experimento: los 6 modos sobre el mismo video al mismo tiempo

Fecha: 2026-10-13 · mismo equipo y mismo video (`2e57b9_0.mp4`, 750 cuadros) · GPU en todas las pruebas.
Datos crudos: `outputs/experiment/` (tablas completas en `outputs/experiment/summary.md`).

> **Resumen.**
> - **C (un proceso, cada modelo una vez por cuadro) da exactamente los mismos datos que A** (los 6 modos originales uno por uno): 100 % de cajas con IoU > 0.95 (IoU medio 1.0), 100 % mismos `track_id`, 100 % mismos equipos y keypoints a 0.0 px, en los 750 cuadros.
> - **C tarda 43 % menos que A** en condiciones iguales (solo datos, mismo día): 1,316 s contra 2,328 s (1.77× más rápido).
> - **C2 (con hilos) genera los 6 videos en 1,335 s, 12 % menos que C con videos (1,520 s).** Su bucle es casi igual al de C sin videos, así que dibujar y escribir queda escondido detrás del trabajo de la GPU.
> - **B (6 procesos a la vez) no sirve en esta laptop.** En 10 min solo terminó 1 de 6 videos (PITCH). TEAM_CLASSIFICATION y RADAR no llegaron a procesar ni un cuadro. No hubo error de memoria, pero la GPU llegó a 5.8 de 6 GB.
> - Nada es tiempo real: C2 va a ~0.68 FPS y el video es de 25 FPS. El balón (51 %) y los equipos (31 %) se llevan el 82 % del tiempo por cuadro.

### 9.1 Diseño

| Prueba | Qué es | Script |
|---|---|---|
| **A_data** | Los 6 modos **originales** de `main.py` uno por uno, sin video. Captura los datos que cada modo pasa a sus anotadores; no modifica `main.py`. BALL corre con supervision 0.23.0; los demás, con 0.25.1 | `capture_a.py` |
| **C_data** | Un solo proceso: el video se decodifica una vez y cada modelo corre una vez por cuadro (cancha, jugadores, balón, SigLIP); el resultado se reparte a los 6 modos. Sin video (`--no-video`) | `run_together.py --no-video` |
| **C_video** | Igual que C_data, pero además dibuja y escribe los 6 videos como `main.py` | `run_together.py` |
| **C2_video** | C_video con 3 hilos: decodificación → GPU/CPU → dibujo y escritura (colas de 8 cuadros) | `run_together.py --threads` |
| **B** | 6 procesos `run_mode.py` lanzados a la vez (BALL con supervision 0.23 vía `PYTHONPATH=.sv023`). Se detienen a los 10 min | `run_experiment.py` |

Orden de corrida, como se acordó: C_data → C_video → C2_video → B → A_data (los datos de A solo se necesitaban para validar) → validación.

Controles:
- **Semillas** fijas (42) en UMAP (`random_state`) y KMeans (`random_state`), en A y en C, mediante una subclase de `TeamClassifier`. El repo original no fija semillas, así que dos corridas del original pueden asignar equipos distintos.
- **Enfriamiento** antes de cada fase: mínimo 2 min y hasta que la GPU baje a ≤ 65 °C (máximo 10 min). Todas las fases empezaron entre 63 y 65 °C.
- **nvidia-smi cada 1 s** (temperatura, reloj SM y de memoria, potencia, memoria, uso y motivo de freno) en `gpu_<fase>.csv`. **RAM del sistema cada 1 s** en `ram_<fase>.csv`.
- Chrome, Slack y otras apps cerradas antes de la corrida. RAM libre al empezar las fases: 6.2–11.5 GB.
- Única adaptación del código en C: `InferenceSlicer(overlap_filter=...)` en lugar de `overlap_filter_strategy=...`. El alias se eliminó en supervision 0.24; comparé el código de `InferenceSlicer.__call__` entre 0.23.0 y 0.25.1 y es idéntico.

### 9.2 Validación C vs A (datos, no píxeles)

Criterios: cajas emparejadas por cuadro y clase (asignación húngara sobre IoU) con IoU > 0.95; mismo `track_id` y mismo equipo en las cajas emparejadas; keypoints visibles en ambos a < 3 px. Un chequeo pasa si ≥ 99 % cumple. **Resultado: 100 % en todos los chequeos, en C_data, C_video y C2_video.**

| Chequeo (C_video vs A, 750 cuadros) | Resultado |
|---|---|
| PLAYER_DETECTION: cajas con pareja IoU > 0.95 | 17,951 / 17,951 (IoU medio 1.0) |
| BALL_DETECTION: balón con pareja IoU > 0.95 | 687 / 687 (C con supervision 0.25.1 vs A con 0.23.0) |
| PLAYER_TRACKING: cajas / mismo `track_id` | 17,232 / 17,232 · 17,232 / 17,232 |
| TEAM_CLASSIFICATION: cajas / `track_id` / mismo equipo | 17,164 / 17,164 · 17,164 / 17,164 · 15,459 / 15,459 |
| RADAR: cajas / `track_id` / mismo equipo | igual que TEAM_CLASSIFICATION |
| PITCH y RADAR: keypoints a < 3 px | 19,407 / 19,407 (máx. 0.0 px) · misma visibilidad 24,000 / 24,000 |
| RADAR: cuadros con homografía válida | A = 750, C = 750 |

Detalle por chequeo en `outputs/experiment/<prueba>/validation.json`.

### 9.3 Tiempos

| Prueba | Total | Preparación | Bucle | FPS bucle | RAM pico | VRAM pico (Δ nvidia-smi / torch) |
|---|---|---|---|---|---|---|
| A_data (suma de los 6) | **2,328 s** (38.8 min) | 394 s (TEAM + RADAR, ~193 s c/u) | — | 1.3–15.8 según el modo | 5.5 GB (BALL) | ≤ 1.5 GB por modo |
| **C_data** | **1,316 s** (21.9 min) | 219 s | 1,098 s | 0.68 | 5.8 GB | 2.5 / 2.3 GB |
| C_video | 1,520 s (25.3 min) | 222 s | 1,298 s | 0.58 | 5.9 GB | 2.4 / 2.3 GB |
| **C2_video** | **1,335 s** (22.2 min) | 227 s | 1,108 s | 0.68 | 5.9 GB | 2.4 / 2.3 GB |
| B | detenida a los 600 s | — | — | — | RAM libre mín. 3.5 GB | 5.8 GB de 6 GB en total |

- **C vs A (misma condición, sin video):** −1,012 s (−43 %). El ahorro coincide con el trabajo repetido que C elimina: el modelo de jugadores corría en 4 modos y ahora en 1 (≈ 416 s), SigLIP + UMAP por cuadro en 2 modos → 1 (≈ 346 s), la preparación de equipos 2 → 1 (≈ 170 s) y el modelo de cancha 2 → 1 (≈ 40 s). Suma estimada: ≈ 970 s.
- **No medí A con video el mismo día.** La referencia con video es la corrida del 2026-10-08 (§2): 3,433 s en total, con condiciones distintas (barras tqdm activas, otra temperatura inicial). Por eso no reporto un "C_video vs A con video" directo. Si se toma esa cifra, C2 tardaría 61 % menos, pero es una comparación entre días distintos.
- La preparación de C (~220 s) es casi toda **carga de SigLIP: 170 s**, aunque el modelo ya está en `.hf_cache`. *Hipótesis no verificada:* `transformers` consulta Hugging Face Hub en red al cargar. Probar con `HF_HUB_OFFLINE=1`.

**ms por cuadro y por etapa (media / p95):**

| Etapa | C_data | C_video | C2_video |
|---|---|---|---|
| decode | 6.6 / 8.6 | 7.4 / 10.3 | 10.0 / 13.3 |
| pitch (cancha) | 54.0 / 57.6 | 54.3 / 59.1 | 63.9 / 77.0 |
| player (jugadores) | 185.3 / 189.9 | 184.9 / 190.7 | 187.8 / 193.9 |
| **ball** (slicer 640×640) | **749.7** / 810.9 | **757.6** / 827.1 | **754.2** / 820.0 |
| tracking (ByteTrack) | 5.8 / 8.5 | 6.3 / 10.2 | 6.0 / 9.9 |
| **teams** (SigLIP + UMAP + KMeans) | **460.8** / 491.8 | **461.5** / 489.1 | **463.2** / 494.1 |
| homography | 1.1 / 1.7 | 1.2 / 1.9 | 1.1 / 1.7 |
| draw (6 videos) | — | 99.8 / 141.7 | 119.0 / 156.5 (en otro hilo) |
| write (6 videos) | — | 156.5 / 208.8 | 161.8 / 212.3 (en otro hilo) |

En C2, dibujo y escritura (~280 ms) corren en paralelo con la GPU (~1,450 ms), por eso casi no suman tiempo. Más hilos no ayudarían: el cuello de botella es la GPU (balón + equipos).

### 9.4 GPU: temperatura, reloj y potencia

| Fase | T máx | Reloj SM con GPU ocupada (mediana / mín) | Potencia media ocupada | Muestras ocupadas con freno por **potencia** / **térmico** |
|---|---|---|---|---|
| C_data | 87 °C | 1,290 / 750 MHz | 55.9 W | 95.5 % / 0.1 % |
| C_video | 86 °C | 1,320 / 630 MHz | 52.8 W | 81.3 % / 0.0 % |
| C2_video | 87 °C | 1,290 / 765 MHz | 56.1 W | 95.5 % / 0.2 % |
| B | 87 °C | 1,740 / 1,455 MHz | 57.4 W | 23.1 % / **65.3 %** |
| A_data | 87 °C | 1,275 / 765 MHz | 55.5 W | 95.0 % / 0.2 % |

"Ocupada" = muestras con uso de GPU ≥ 50 %. Freno según `clocks_event_reasons`: potencia = `SwPowerCap` (0x4); térmico = `SwThermalSlowdown` / `HwThermalSlowdown` (0x20 / 0x40).

- En A y C el límite es la **potencia** (~55 W, tope de la versión Max-Q), no la temperatura: el reloj se queda en ~1,290 MHz aunque el máximo es ~1,800. Esto corrige la hipótesis de §2 ("probablemente throttling térmico"): con estos datos, lo que domina es el **límite de potencia**.
- Hay deriva dentro de una misma corrida: el tiempo de GPU por cuadro (cancha + jugadores + balón + equipos) sube ~7 % entre los cuadros 0–149 y 600–749 (C_data: 1,398 → 1,503 ms).
- Solo en B aparece freno térmico en la mayoría de las muestras.

### 9.5 Prueba B (6 procesos a la vez, detenida a los 10 min)

| Modo | Estado a los 600 s | Avance | RSS pico |
|---|---|---|---|
| PITCH_DETECTION | terminó OK a los 575 s | 750 / 750 | 1.6 GB |
| PLAYER_DETECTION | detenido | 300 / 750 | 1.7 GB |
| BALL_DETECTION | detenido | 75 / 750 | 2.0 GB |
| PLAYER_TRACKING | detenido | 25 / 750 | 1.7 GB |
| TEAM_CLASSIFICATION | detenido | 0: no salió de la preparación | 2.1 GB |
| RADAR | detenido | 0: no salió de la preparación | 1.7 GB |

- **Error documentado: ninguno.** No hubo `CUDA out of memory` ni excepciones; la única causa de parada fue el timeout. Logs en `outputs/experiment/B/<MODO>.log`.
- Memoria de GPU al **94 %** (5,796 / 6,144 MiB), uso al 100 % y RAM libre mínima de 3.5 GB. Supongo que el controlador de Windows (WDDM) pasó memoria a la RAM compartida en lugar de fallar, pero no lo verifiqué.
- PITCH sola tardó 117 s con video (§2); en B tardó 575 s (≈ 4.9× más lenta).
- No investigué por qué PLAYER_TRACKING avanzó mucho menos que PLAYER_DETECTION (25 contra 300 cuadros) con el mismo modelo.

### 9.6 Datos exportados (parquet)

En `outputs/experiment/C_data/`, `C_video/` y `C2_video/` (los tres tienen los mismos datos). Lo pedido como "un parquet por cuadro" está en **una tabla larga con una fila por objeto y cuadro**, más una tabla por cuadro para lo que es del cuadro (keypoints, homografía), en vez de 750 archivos:

| Archivo | Filas | Columnas |
|---|---|---|
| `objects.parquet` | 35,870 (det 17,951 · track 17,232 · ball 687) | `frame, t, source (det/track/ball), track_id, class_id, class_name, team (0/1; nulo para árbitro y balón), x1, y1, x2, y2, conf, pitch_x, pitch_y` (cm en la cancha, con la homografía del cuadro) |
| `frames.parquet` | 750 | `frame, t, n_det, n_track, ball_found, homography_valid, homography_error, n_kp_visible, kp_x[32], kp_y[32], kp_conf[32], H[9]` |
| `timings.parquet` | 750 | `frame` y ms de `decode, pitch, player, ball, tracking, teams, homography, draw, write` |

Datos de este video: balón encontrado en 687 de 750 cuadros, homografía válida en 750 de 750, 25.9 keypoints visibles por cuadro en promedio y 39 `track_id` distintos.

### 9.7 Limitaciones

- **Una sola repetición por prueba**, en orden fijo. El enfriamiento iguala la temperatura inicial, pero no el resto de la carga del sistema.
- A_data no escribe video, así que la comparación pareja del mismo día es **C_data vs A_data**. No medí A con video ese día.
- La validación prueba que C reproduce a A **con semillas fijas**. No dice nada sobre la calidad de las detecciones; sigue sin haber ground truth (§3).
- En C, si una homografía no se puede calcular, el cuadro se marca como inválido y la corrida sigue; `main.py` en ese caso lanzaría una excepción. En este video no pasó (750 / 750 válidas).

### 9.8 Cambios en el entorno durante esta prueba

- `.venv`: `supervision` vuelve a **0.25.1** (estaba en 0.23.0 tras la corrida 3) y se instaló **`pyarrow` 26.0.0**.
- `.sv023/`: supervision 0.23.0 instalado con `pip --target --no-deps`. Solo se usa con `PYTHONPATH=.sv023` para BALL original.
- `C:\Users\Dell G3\AppData\Roaming\Ultralytics\settings.json` se volvió a crear al revisar versiones sin `YOLO_CONFIG_DIR` (error mío). Todos los scripts de §9 fijan `YOLO_CONFIG_DIR` y `HF_HOME` dentro del proyecto.
- Espacio en disco: ~890 MB en `outputs/experiment/` (sobre todo los 12 videos de C_video y C2_video).

### 9.9 Video combinado (todos los modelos en una imagen)

`outputs/experiment/TODOS_JUNTOS.mp4` (1920×1080, 750 cuadros) dibuja sobre el video original, en la misma imagen: keypoints de la cancha, jugadores, porteros y árbitros con el color de su equipo y su `track_id`, el rastro del balón y un radar pequeño (15 % del ancho, abajo al centro). **No vuelve a correr los modelos:** se genera desde los parquet de C2 (`scripts/render_combined.py`, ~2 min; `--radar-size` cambia el tamaño del radar). Como C2 = A (§9.2), muestra los mismos resultados que los 6 modos originales.

`outputs/experiment/TODOS_JUNTOS_whatsapp.mp4` es la versión para compartir: H.264 Main, 1280×720, yuv420p, 10.6 MB (`scripts/export_whatsapp.py`, con PyAV/libx264; no requiere ffmpeg instalado).

### 9.10 Cómo reproducir

```powershell
# todo el experimento (~2 h 15 min); orden C_data, C_video, C2_video, B, A_data, validate
.\.venv\Scripts\python.exe -u scripts\run_experiment.py > outputs\experiment\orchestrator.log
# en otra terminal, monitor en vivo
.\.venv\Scripts\python.exe scripts\monitor.py
# tablas de resumen
$env:PYTHONIOENCODING = "utf-8"; .\.venv\Scripts\python.exe scripts\summarize_experiment.py > outputs\experiment\summary.md

# piezas sueltas
.\.venv\Scripts\python.exe scripts\run_together.py --outdir outputs\experiment\C2_video --threads   # agrega --no-video para solo datos
.\.venv\Scripts\python.exe scripts\validate.py --a outputs\experiment\A_data --c outputs\experiment\C2_video
```
