# Encargo para IBM Bob: experimento de reconocimiento de dorsales

**Asignado a:** IBM Bob IDE
**Preparado por:** Claude Code, 2026-11-09
**Tipo:** experimento con límite de tiempo. Medir y reportar, no integrar al producto.
**Presupuesto:** máximo ~40 Bob coins. Si se acerca, detente y reporta lo que tengas.

---

## 0. Antes de empezar

1. Lee `AGENTS.md` y la última bitácora de `bob_sessions/`.
2. **Misma carpeta y misma rama que Claude Code y Gemini: `feat-costa-rica`.** No cambies de rama, ni hagas `stash`, `reset`, `git add -A` o `git add .`. Para el commit, nombra tus archivos.
3. Usa `.\.venv\Scripts\python.exe` (ya trae `ultralytics`, `supervision`, `opencv` y CUDA) y `$env:PYTHONIOENCODING = "utf-8"`. El paquete `roboflow` **no** está instalado: instálalo con `.\.venv\Scripts\python.exe -m pip install roboflow` y anota la versión en la bitácora.
4. **Requisito del usuario, no tuyo.** Necesitas una cuenta de Roboflow y estas variables en `.env`, que se leen con `python-dotenv`. Tú no creas cuentas ni escribes claves, nombres de workspace ni versiones en el código.
   ```
   ROBOFLOW_API_KEY=<clave privada>
   ROBOFLOW_WORKSPACE=<workspace del usuario, el que aparece en la URL de app.roboflow.com>
   ROBOFLOW_PROJECT=<proyecto del fork, normalmente numbers-xil6i>
   ROBOFLOW_VERSION=<número de la versión generada, normalmente 1>
   ```
   **No uses `inference-sdk` ni `run_workflow`:** llaman al modelo genérico en la nube, no entrenado para dorsales, y gastan créditos. Descarga el dataset con el paquete `roboflow`:
   ```python
   from roboflow import Roboflow
   rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
   proyecto = rf.workspace(os.environ["ROBOFLOW_WORKSPACE"]).project(os.environ["ROBOFLOW_PROJECT"])
   proyecto.version(int(os.environ["ROBOFLOW_VERSION"])).download("folder", location="outputs/experimentos/dorsales/dataset")
   ```
   El proyecto es de **clasificación**, así que el formato es `folder`: una carpeta por clase en `train/`, `valid/` y `test/`.

## 1. Pregunta que debe responder el experimento

> ¿Un clasificador de dorsales entrenado con el dataset "jersey number" puede leer los números en nuestro clip de transmisión de TV (720p, jugadores de 52–68 px de alto) lo bastante bien como para ponerle número a los rastros principales?

**El resultado vale aunque sea "no".** Con números, un "no funciona en 720p, pero sí en cámara táctica" es una conclusión útil.

**Comparación con Roboflow:** el usuario ya entrenó en Roboflow un **ResNet18 de clasificación** (`jersey-number-ijbaq-yqots-1-resnet18-t1`, versión 1 del dataset, entrada 224×224, licencia Apache 2.0). **Roboflow no permite descargar los pesos de este tipo de modelo**, así que solo se puede usar por su API en la nube.
- **Tu modelo local es el camino principal.** Para que la comparación sea justa, además del YOLOv8-cls puedes entrenar un `torchvision` ResNet18 preentrenado con entrada 224×224, si alcanza el presupuesto.
- **Uso de la nube de Roboflow, solo con permiso explícito:** únicamente si `.env` tiene `ROBOFLOW_NUBE_AUTORIZADA=si`. En ese caso, manda los mismos recortes del paso 3 al modelo `jersey-number-ijbaq-yqots/1` con el paquete `inference-sdk` (método `infer` o el que indique la documentación del modelo de clasificación, no `run_workflow`), aplica la misma votación del paso 4 y pon ambos modelos lado a lado. **Máximo 3,000 recortes** (unos 0.2 créditos, a 0.0625 por cada 1,000) y registra cuántos enviaste. Si la variable no existe o no dice `si`, no llames a la API.
- **Línea base de Roboflow** (leída por el usuario en el panel; son valores aproximados, tomados de las gráficas):
  - Exactitud de validación ≈ **91 %**: estable entre 89 y 92 % desde la época 15. Entrenó 33 épocas y la pérdida bajó de 3.0 a ~0.1.
  - Umbral óptimo de F1: **66 %**.
  - Por clase, en el conjunto de prueba al 66 %: casi perfectas 0, 1, 10, 12, 14, 17 y 18. Más errores en 11 (~4 de 16), 13 (~2 de 11) y 15 (~2 de 7). Mal en "00", que solo tiene 3 imágenes.
  - **Clases del proyecto** (consultadas por la API el 2026-11-09): 46 clases, 4,105 imágenes, licencia del dataset CC BY 4.0, versión 1 con 4,114 imágenes.
    - Dígitos del 0 al 9: la clase "0" es el **dígito 0**, no "sin número".
    - Números del 10 al 77, con huecos. "00" tiene 27 imágenes.
    - **Dos clases de "sin número":** `no number` (149) y `unreadble` (62, con esa errata). En el paso 4, cualquiera de las dos cuenta como "sin número".
    - **Del 1 al 23 faltan el 16 y el 19:** si un jugador lleva uno de esos dorsales, nunca se leerá bien. Anótalo como limitación.
    - **Clases con pocas imágenes**, en las que se esperan más errores: 6 (31), 18 (24), 20 (22) y 21 (23).
- Anota en la bitácora tus cifras al lado de estas.
- **No mandes recortes de nuestro video a la API de Roboflow** sin permiso del usuario: gasta créditos y saca imágenes del equipo.

## 2. Datos

| Qué | Dónde |
|---|---|
| Dataset | Proyecto de clasificación **"jersey number"** en el workspace del usuario (4,114 imágenes según Roboflow). Variables `ROBOFLOW_*` en `.env`. Anota en la bitácora el proyecto de origen en Roboflow Universe y su licencia, que aparecen en la página del proyecto |
| Clip | `data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4`, cuadros 0–1079 |
| Rastros limpios | `data/clean/objects_cleaned.parquet`: columnas `frame`, `track_id_stitched`, `team_mode`/`team`, `x1,y1,x2,y2`, `class_id` (3 = árbitro) |
| Equipos | `team_id 0` = San Cristóbal y Nieves (verde), `team_id 1` = Costa Rica (guinda) |
| Verdad de referencia | Pestaña `Quien_es_quien` de `data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx`, cuando Fer la llene. Mientras tanto, la hoja de contactos del paso 5 sirve para revisar a ojo |

**Qué verificar del dataset** en el paso 1, porque todavía no se revisó:

- **Clases:** qué números trae y cuántas imágenes tiene cada uno. Si faltan dorsales comunes (1–23), un rastro con ese número nunca se leerá bien.
- **Clase "sin número":** si existe una clase para espalda sin dorsal visible o número tapado. Sin ella, el clasificador siempre elige algún número y hay que filtrar por confianza.
- **Tipo de imagen:** las vistas previas son recortes de espalda con el número grande. Nuestros recortes serán mucho más pequeños y borrosos.

## 3. Pasos

### Paso 1: conseguir y auditar el dataset

1. El usuario ya tiene el proyecto en su workspace. Si no hay ninguna versión generada, pídele que haga *Generate Version* sin augmentations.
2. Descárgala en formato `folder` con el paquete `roboflow` a `outputs/experimentos/dorsales/dataset/`. Esa carpeta no va a Git.
3. Reporta el número de imágenes por clase y por división, el tamaño típico de imagen y las clases que faltan del 1 al 23.

**Criterio:** una tabla de clases con conteos en la bitácora.

### Paso 2: entrenar

- Un clasificador **YOLOv8n-cls o YOLOv8s-cls** con `ultralytics` (`yolo classify train`), `imgsz=96` o `128`, unas 30–50 épocas, en GPU.
- **Augmentation para parecerse a nuestro video:** reducir y volver a ampliar (por ejemplo, a 20–28 px de alto y de vuelta), blur y compresión JPEG. Puedes hacerlo con un preprocesado propio, generando una copia degradada del set de entrenamiento.
- Reporta la exactitud de validación **dos veces**: con las imágenes originales y con las de validación degradadas igual que nuestro video. La segunda cifra es la que importa.
- Guarda pesos y métricas en `outputs/experimentos/dorsales/entrenamiento/`.

**Criterio:** exactitud top-1 de validación, original y degradada. **Los pesos `.pt` no van a Git** (`AGENTS.md` §3).

### Paso 3: recortes del clip

- Cada 5 cuadros, toma los jugadores de `objects_cleaned.parquet` (sin árbitros) con caja de al menos 40 px de alto.
- Recorta el **torso**: la franja vertical del 15 % al 65 % de la caja, con un margen de 10 %. Amplíalo ×4 con `INTER_CUBIC`.
- Guarda los recortes en `outputs/experimentos/dorsales/recortes/` con el nombre `f{frame}_t{track_id_stitched}.png`.

**Criterio:** número de recortes y tamaño mediano antes de ampliar.

### Paso 4: inferencia y votación por rastro

- Clasifica cada recorte y guarda en `predicciones_por_recorte.jsonl` las tres clases más probables, con `frame`, `track_id_stitched`, `team`, `top3` (número → probabilidad) y `numero`. Este último solo se llena si la clase más probable supera **0.66** (el umbral óptimo de F1 que calculó Roboflow para el ResNet18) y no es `no number` ni `unreadble`; si no, es `null`. Si tu modelo tiene otro umbral óptimo en validación, repórtalo y usa ese para tu modelo.
- Para cada rastro, un número **gana** si tiene al menos 3 votos y al menos el 60 % del total. Si no, el rastro queda "sin número".
- Escribe `dorsales_por_rastro.json` con `track_id_stitched`, `team`, `numero` (o `null`), `votos` (número → cuenta), `n_recortes` y `segundos_visible`.

### Paso 5: revisión visual

Genera `hoja_contactos.jpg`: por rastro, hasta 6 recortes con el número predicho encima. Así el usuario o Fer pueden ver de un vistazo si el modelo acierta.

### Paso 6: medir

- **Cobertura:** % de recortes con `numero` no nulo y % de rastros (de los 20 con más tiempo visible) que obtienen número.
- **Precisión:** cuando exista `Quien_es_quien`, % de rastros con el número correcto. Si todavía no existe, revisa a ojo 20 recortes de la hoja de contactos y reporta cuántos están bien, aclarando que es una muestra.
- **Números imposibles:** cruza con las alineaciones de la plantilla si Gemini ya las llenó. Un número que no existe en el equipo de ese color es un error seguro.

## 4. Cuándo parar (para cuidar las coins)

- Si la exactitud de validación **degradada** es menor que 50 %, **detente** después del paso 2 y reporta.
- Si menos del 10 % de los 20 rastros principales obtiene número, **no ajustes parámetros en bucle.** Reporta y propón el siguiente experimento, por ejemplo IBM Granite Vision para leer el número o probar con video de cámara táctica.

## 5. Entregables

1. **Código:**
   - `scripts/experimentos/dorsales/entrenar.py`: pasos 1 y 2.
   - `scripts/experimentos/dorsales/leer_dorsales.py`: pasos 3 a 6.

   Ambos con argumentos y sin claves en el código.
2. **Bitácora:** `bob_sessions/sesion_15_dorsales_bob.md`, con la tabla de clases, la exactitud de validación (original y degradada, y la de Roboflow si el usuario la pasa), las métricas del paso 6, 3 o 4 ejemplos de aciertos y errores (rutas a recortes), coins gastadas y conclusión: ¿sirve, no sirve, o sirve con qué condición?
3. **Índice:** la fila nueva en `bob_sessions/README.md`.
4. **Un commit** solo con esos archivos. Mensaje: `feat(experimento): medir clasificacion de dorsales con dataset de Roboflow`. **Sin push.**

## 6. Lo que NO debes hacer

- No toques `implementacion/`, `dashboard/`, `run_pipeline.py`, `data/raw/`, `data/clean/`, `data/partidos/` ni los scripts existentes.
- No integres nada al tablero ni al engine: es un experimento.
- No subas a Git pesos, recortes, el dataset, videos ni `.env`.
- Cita en la bitácora el dataset de origen y su licencia, tal como aparecen en Roboflow.
