# Registro de Ejecuciones y Pruebas del MVP — Omnimorph

Este documento registra todas las corridas de percepción y del pipeline Omnimorph, separando claramente los **Experimentos de Referencia** de las **Pruebas del MVP (Mundial FIFA Brasil 2014)**.

---

## 1. Corridas de Experimentos Previos (`outputs/experiment/` y `outputs/experimentos/`)

| ID Corrida | Video Fuente | Resolución / Frames | Carpeta de Salida | Estado Percepción | Notas |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **EXP-01** | `sports/examples/soccer/data/2e57b9_0.mp4` | 1920×1080 · 750 frames (25 fps) | `outputs/experimentos/corrida_inicial_2e57b9/` | ✅ Completado | Evaluación individual de los 6 modos (`PITCH`, `PLAYER`, `BALL`, `TRACKING`, `TEAM`, `RADAR`). |
| **EXP-02 (A/B/C/C2)** | `sports/examples/soccer/data/2e57b9_0.mp4` | 1920×1080 · 750 frames (25 fps) | `outputs/experiment/C_data/`<br>`outputs/experiment/C_video/`<br>`outputs/experiment/C2_video/` | ✅ Completado | Pipeline unificado en 1 proceso (`1 316 s` en `C_data`). Generó los primeros `frames.parquet` y `objects.parquet` reales. |
| **PIPE-SINT-01** | Telemetría sintética (750 frames) | Simulación 120×70 m | `data/clean/` | ✅ 9/9 PASS | Corrida end-to-end de validación de arquitectura en `5.0 s` (M1, M2.0–M2.5, M3 offline, M4 sintético). |

---

## 2. Corridas de las Pruebas del MVP — Mundial FIFA Brasil 2014 (`outputs/mvp_pruebas/mundial_2014_brasil_alemania/`)

| ID Prueba MVP | Clip Seleccionado (Alta Calidad 720p HD) | Carpeta de Salida | Percepción GPU (`run_mvp_perception.py`) | Pipeline Omnimorph (`M1`–`M4`) | Observaciones |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **MVP-2014-13** | `data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4` | `outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13/` | ✅ **1800/1800 frames (60.0 s)**<br>6 JSONs + 6 MP4s + Video/JSON Unificado (`1979.9 s`) | ✅ **9/9 PASS (`4.5 s`)**<br>`M1`, `M2.0–M2.5`, `M3`, `M4` | **Clip principal del MVP completado de punta a punta** (198 IDs originales cosidos a 22 dorsales en `M2.2`, 8 ventanas tácticas y 8 audios TTS sincronizados). |

### 2.1 Tiempos Reales por Modelo en GPU (GTX 1660 Ti — 1800 frames / 60.0 s)
| Etapa / Modelo | Tiempo (s) | Artefacto JSON | Artefacto Video MP4 |
| :--- | :---: | :--- | :--- |
| `[1/6] PITCH_DETECTION` (YOLOv8x-pose) | `118.78 s` | `json_por_modelo/PITCH_DETECTION.json` | `videos_por_modelo/PITCH_DETECTION.mp4` |
| `[2/6] PLAYER_DETECTION` (YOLOv8x) | `436.96 s` | `json_por_modelo/PLAYER_DETECTION.json` | `videos_por_modelo/PLAYER_DETECTION.mp4` |
| `[3/6] BALL_DETECTION` (InferenceSlicer 640×640) | `860.02 s` | `json_por_modelo/BALL_DETECTION.json` | `videos_por_modelo/BALL_DETECTION.mp4` |
| `[4/6] PLAYER_TRACKING` (ByteTrack) | `27.82 s` | `json_por_modelo/PLAYER_TRACKING.json` | `videos_por_modelo/PLAYER_TRACKING.mp4` |
| `[5/6] TEAM_CLASSIFICATION` (SigLIP + UMAP + KMeans) | `443.29 s` | `json_por_modelo/TEAM_CLASSIFICATION.json` | `videos_por_modelo/TEAM_CLASSIFICATION.mp4` |
| `[6/6] RADAR` (Homografía + Proyección 2D) | `52.60 s` | `json_por_modelo/RADAR.json` | `videos_por_modelo/RADAR.mp4` |
| `[UNIFICADO]` Video + JSON + Parquets | `40.55 s` | `TELEMETRIA_UNIFICADA_COMPLETA.json` | `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4` |

### 2.2 Resultados de los 9 Monitores sobre `L6sbfskaTDQ-720-13.mp4` (`run_pipeline.py --use-real`)
* **Tiempo total del pipeline**: `4.5 s` (Engine: `1.73 s`)
* **Telemetría procesada**: `1800` frames (`60.0 s` @ 30 FPS), `26 909` objetos (`10 818` filas `track`, `572` filas `ball`).

| Monitor | Nombre | Métrica Observada en `clip_13` | Estado |
| :--- | :--- | :--- | :---: |
| **M1** | Observabilidad de Percepción y Dataset | `1800` frames, `10 818` tracks, `572` balls, homografía cruda `59.5%` | ✅ **PASS** |
| **M2.0** | Separación track/ball y moda de equipo | `198` `track_ids` originales con moda de equipo asignada | ✅ **PASS** |
| **M2.1** | Homografía EMA normalizada | `1071/1800` crudas + `1800/1800` (`100%`) con continuidad `H_ema` | ✅ **PASS** |
| **M2.2** | Track Stitching (Algoritmo Húngaro) | Reducción de `198` IDs fragmentados → **`22` dorsales cosidos** (`<= 25`) | ✅ **PASS** |
| **M2.3** | Cinemática Savitzky-Golay (`v <= 9.5 m/s`) | `100%` de velocidades suavizadas y acotadas a `<= 9.5 m/s` | ✅ **PASS** |
| **M2.4** | Ventanas Tácticas | `8` ventanas (`W0`–`W7`) cubriendo los `60.0 s` del clip | ✅ **PASS** |
| **M2.5** | Integridad del pipeline completo | `objects_cleaned.parquet`, `frames_clean.parquet`, `tactical_summaries.json` | ✅ **PASS** |
| **M3** | Auditoría LLM y `watsonx.governance` | `ibm/granite-4-h-small` (`8/8` ventanas validadas, `0.5287 RU`, latencia media `1170 ms`) | ✅ **PASS** |
| **M4** | Sincronización TTS y Dashboard | `8/8` clips `.wav` (`3.90 s` c/u `<= 4.0 s`, desfase `0.4 ms`) | ✅ **PASS** |

---

## 3. Plan de Trabajo y División de Responsabilidades (Local vs. IBM Bob)

### 3.1 Fases de Ejecución sobre `L6sbfskaTDQ-720-13.mp4`
1. **Fase 1 (Inspección técnica):** Contar frames, FPS y duración de `L6sbfskaTDQ-720-13.mp4` para alinear con el requisito de 750 frames del Monitor `M1`.
2. **Fase 2 (Modelos de Percepción en GPU local):** Ejecutar `YOLOv8x` (cancha, jugadores, balón con `InferenceSlicer`), `ByteTrack` y `SigLIP + UMAP + KMeans` hacia `outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13/`.
3. **Fase 3 (Adaptación de Contexto):** Configurar identidad del partido Brasil (`BRA`) vs. Alemania (`GER`) — Semifinal Mundial FIFA 2014.
4. **Fase 4 (Pipeline Omnimorph Local + TTS Real):** Conectar parquets reales de `clip_13`, validar Monitores `M1` y `M2.0–M2.5`, y generar voz real en español (`W0.wav`–`W7.wav`) validando `M4`.
5. **Fase 5 (Dashboard Sincronizado):** Visualizar `L6sbfskaTDQ-720-13.mp4` con audio original, radar 2D, métricas tácticas y voz TTS en `implementacion/dashboard/app.py`.

### 3.2 División para Ahorro de Contexto / Coins de IBM Bob
* **Trabajo Local (Aquí + GPU GTX 1660 Ti — 0% consumo en Bob):**
  * Fases 1, 2, 3, 4 (modo offline/TTS local) y 5 (Dashboard Streamlit).
* **Trabajo Reservado Exclusivamente para IBM Bob (Recta final IBM Cloud):**
  1. ✅ **COMPLETADO** — Conexión Online de `ibm/granite-4-h-small` (Etapa 3 / Monitor M3): corrida oficial online con `WATSONX_SPACE_ID` (trial Orchestrate AWS), 8/8 PASS, `0.5287 RU`.
  2. ✅ **COMPLETADO** — Servidor FastAPI + túnel ngrok para Orchestrate: `implementacion/cloud_tool/api_server.py` + `launch_ngrok.py` creados y validados (`POST /process` → 200 PASS, 1.6 s).
  3. ⏳ **PENDIENTE** — Importar `openapi_tool.yaml` en watsonx Orchestrate UI (`dl.watson-orchestrate.ibm.com` → Skills & Tools → Add tool → Import from OpenAPI). Ver instrucciones en §5.

---

## 4. Comandos Estándar para `L6sbfskaTDQ-720-13.mp4`

### Fase 1: Contar frames, FPS y resolución del video
```powershell
.\.venv\Scripts\python.exe -c "import cv2; cap=cv2.VideoCapture('data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4'); f=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps=cap.get(cv2.CAP_PROP_FPS); print(f'Clip 13 -> Frames: {f} | FPS: {fps:.2f} | Duracion: {f/fps:.1f} s | Resolucion: {int(cap.get(3))}x{int(cap.get(4))}')"
```

### Fase 2: Extraer telemetría real (Modelos de Percepción YOLO + SigLIP + ByteTrack)
```powershell
.\.venv\Scripts\python.exe scripts/run_together.py `
  --source data/videos/mundial_2014_720p_hd/L6sbfskaTDQ-720-13.mp4 `
  --outdir outputs/mvp_pruebas/mundial_2014_brasil_alemania/clip_13 `
  --device cuda --no-video
```
*(Si también deseas generar los 6 videos anotados `.mp4`, quita `--no-video` y usa `--threads`).*

### Fase 4: Ejecutar el Pipeline Omnimorph (Etapas 1 a 4 + Monitores M1 a M4)
```powershell
.\.venv\Scripts\python.exe run_pipeline.py --use-real
```

---

## 5. Despliegue en IBM watsonx Orchestrate — Guía Paso a Paso

### 5.1 Archivos clave
| Archivo | Función |
| :--- | :--- |
| `implementacion/cloud_tool/api_server.py` | Servidor FastAPI que expone `POST /process` |
| `implementacion/cloud_tool/launch_ngrok.py` | Lanza uvicorn + abre túnel ngrok público |
| `implementacion/cloud_tool/openapi_tool.yaml` | Spec OpenAPI 3.0 para importar en Orchestrate |
| `implementacion/cloud_tool/adk_tool.py` | Decorador `@tool` ADK con fallback local |

### 5.2 Paso 1 — Arrancar el servidor con túnel ngrok
```powershell
# (Opcional) añade a .env tu authtoken para sesión de 24h+
# NGROK_AUTHTOKEN=<tu-token-de-ngrok.com>

.\.venv\Scripts\python.exe implementacion/cloud_tool/launch_ngrok.py
```
El script imprimirá algo como:
```
✅ TÚNEL ACTIVO
URL pública: https://xxxx-yyyy-zzzz.ngrok-free.app
Endpoint   : https://xxxx-yyyy-zzzz.ngrok-free.app/process
OpenAPI JSON: https://xxxx-yyyy-zzzz.ngrok-free.app/openapi.json
```
También actualizará automáticamente `openapi_tool.yaml` con la URL real.

### 5.3 Paso 2 — Importar la herramienta en IBM watsonx Orchestrate
1. Abre: **[https://dl.watson-orchestrate.ibm.com](https://dl.watson-orchestrate.ibm.com)**
2. Menú lateral: **Skills & Tools** → botón **Add tool**
3. Selecciona **Import from OpenAPI file** (o "from URL")
4. Opción A — *Subir archivo*: selecciona `implementacion/cloud_tool/openapi_tool.yaml`
5. Opción B — *Desde URL*: pega `https://xxxx.ngrok-free.app/openapi.json`
6. Orchestrate detectará automáticamente la operación `process_parquet_tool` (POST /process)
7. Haz clic en **Add tool** → confirma

### 5.4 Paso 3 — Añadir la skill al agente y probar
1. En el agente (o crea uno nuevo), ve a **Tools** → **Add** → selecciona **process_omnimorph_parquets**
2. En el chat del agente escribe:
   > `"Analiza el clip del Mundial 2014 (data/raw/frames.parquet)"`
3. El agente invocará `POST /process` con `frames_path` y `objects_path`
4. Recibirás las 8 ventanas tácticas + estado PASS de los 6 monitores M2.x

### 5.5 Verificación de smoke-test local (sin Orchestrate)
```powershell
$py = "c:\Users\Dell G3\Documents\omnimorph-pruebas\.venv\Scripts\python.exe"
& $py -c "
import sys, os; sys.path.insert(0,'c:/Users/Dell G3/Documents/omnimorph-pruebas'); os.chdir('c:/Users/Dell G3/Documents/omnimorph-pruebas')
from implementacion.cloud_tool.api_server import app
from fastapi.testclient import TestClient
import warnings; warnings.filterwarnings('ignore')
c = TestClient(app)
r = c.post('/process', json={'frames_path':'data/raw/frames.parquet','objects_path':'data/raw/objects.parquet'})
d = r.json()
print('Status:', d['status'], '| Windows:', len(d['tactical_summaries']), '| Elapsed:', d['elapsed_s'], 's')
"
```
Salida esperada: `Status: PASS | Windows: 8 | Elapsed: ~1.6 s`
