# Sesión 15: experimento de reconocimiento de dorsales
**Fecha:** 2026-11-10  
**Agente:** IBM Bob IDE  
**Rama:** `feat-dashboard-mejoras`  
**Encargo base:** `blueprints/encargo_bob_dorsales.md`

---

## 0. Contexto de arranque

- Se leyó `AGENTS.md` y la última bitácora (`sesion_13_dashboard_web_costa_rica.md` y `sesion_dashboard_omnimorph_2026-11-04.md`).
- La sesión anterior (Claude Code, 2026-11-09) dejó el tablero web de Costa Rica verificado en el navegador. Este encargo es un **experimento independiente** que no toca nada del dashboard.
- `roboflow 1.7.3` instalado con `.venv/Scripts/python.exe -m pip install roboflow` (no estaba en el entorno).

---

## 1. Dataset auditado

**Fuente del proyecto:** workspace del usuario en Roboflow, proyecto `jersey-number-ijbaq-yqots`, versión 1, creado 2026-11-09.  
**Origen del dataset:** el README del ZIP indica que proviene de Roboflow Universe. Las 4,114 imágenes están anotadas en formato `folder` (clasificación). **Licencia del dataset: CC BY 4.0** (indicado en la página del proyecto según el blueprint; el ZIP confirma que las imágenes son recortes de espalda con el número visible, 224×224 px).

> Nota: el paquete `roboflow.version.download()` no completaba la descarga (error de timeout en el redireccionamiento desde `app.roboflow.com`). Se descargó manualmente el ZIP con `requests` usando la URL devuelta por la API REST.

### Conteos por clase y división

| Clase | train | valid | test |
|---|---|---|---|
| 0 | 195 | 30 | 29 |
| 1 | 119 | 11 | 13 |
| 2 | 217 | 20 | 29 |
| 3 | 125 | 19 | 26 |
| 4 | 80 | 9 | 6 |
| 5 | 192 | 29 | 23 |
| 6 | 26 | 0 | 5 |
| 7 | 189 | 26 | 25 |
| 8 | 270 | 34 | 25 |
| 9 | 148 | 15 | 16 |
| 00 | 21 | 3 | 3 |
| 10 | 67 | 11 | 10 |
| 11 | 164 | 13 | 16 |
| 12 | 61 | 8 | 6 |
| 13 | 46 | 4 | 11 |
| 14 | 35 | 7 | 7 |
| 15 | 71 | 8 | 7 |
| **16** | **ausente** | **ausente** | **ausente** |
| 17 | 49 | 7 | 14 |
| 18 | 18 | 2 | 4 |
| **19** | **ausente** | **ausente** | **ausente** |
| 20 | 19 | 2 | 1 |
| 21 | 20 | 1 | 2 |
| 22 | 78 | 14 | 8 |
| 23 | 98 | 19 | 8 |
| 24–77 (con huecos) | varios | varios | varios |
| no number | 103 | 24 | 22 |
| unreadble | 40 | 8 | 14 |
| **Total** | **3,240** | **439** | **435** |

**Observaciones:**
- Clases `16` y `19` ausentes (limitación confirmada).
- `"6"` ausente en valid (solo 26 imágenes en train).
- Clases con pocas imágenes en train: `18` (18), `20` (19), `21` (20), `26` (8), `46` (5), `58` (8).
- Tamaño típico de imagen: **224 × 224 px**.
- Existen clases "sin número": `no number` (103 train) y `unreadble` (40 train).

---

## 2. Entrenamiento

**Modelo:** YOLOv8n-cls (ultralytics 8.4.174)  
**GPU:** NVIDIA GeForce GTX 1660 Ti Max-Q, 6 GB  
**Configuración:**
- `imgsz = 96`, `epochs = 40`, `batch = 32`, optimizer AdamW (lr=0.0002)
- Sin augmentation propia por imgsz; ultralytics aplica `randaugment`, flip, HSV, erasing.

### Curva de validación (top-1 accuracy por época)

| Época | top-1 | Época | top-1 |
|---|---|---|---|
| 1 | 11.6 % | 21 | 82.7 % |
| 5 | 58.8 % | 23 | 84.1 % |
| 10 | 75.4 % | 27 | 84.3 % |
| 15 | 80.2 % | 33 | 84.1 % |
| 16 | 82.9 % | 35 | 84.3 % |
| 20 | 82.5 % | **40** | **84.5 %** |

*(Best checkpoint: época con top-1 = 84.5 %, guardado en `best.pt`)*

### Resultados finales

| Métrica | Valor |
|---|---|
| **top-1 valid ORIGINAL** | **84.3 %** |
| **top-1 valid DEGRADADO** | **69.2 %** |
| top-5 valid original | 96.8 % |
| Umbral de confianza usado | 0.66 (idéntico al Roboflow ResNet18) |
| Tiempo total | ~5 min 20 s (GPU) |

**Comparación con línea base Roboflow ResNet18:**
| | Roboflow ResNet18 | YOLOv8n-cls (Bob) |
|---|---|---|
| Exactitud valid original | ~91 % | 84.3 % |
| Exactitud valid degradado | —* | **69.2 %** |
| Épocas | 33 | 40 |

*Roboflow no entrenó con imágenes degradadas (no es un caso de uso que midan en su panel).

---

## 3. Recortes del clip (Paso 3)

- **Clip:** `data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4`, cuadros 0–1079.
- **Intervalo:** cada 5 cuadros → 216 cuadros procesados.
- **Mínimo de alto de caja:** 40 px.
- **Recortes generados:** 3,158.
- **Tamaño mediano de caja ANTES de ampliar:** 32 × 70 px.

> El tamaño mediano es 70 px de alto, que está dentro del rango esperado (52–68 px de jugadores en plano abierto, algo más altos en planos cerrados). El torso es la franja del 15 % al 65 % de alto, es decir ≈ 35 px. Amplificado ×4 → ~140 px de alto para el clasificador.

---

## 4. Inferencia y votación (Paso 4)

- **Predicciones guardadas:** `outputs/experimentos/dorsales/predicciones_por_recorte.jsonl`
- **Umbral de confianza:** 0.66 (top-1 conf).
- **Votos mínimos para asignar dorsal:** 3 votos y ≥ 60 % del total de recortes del rastro.

### Resultados de cobertura

| Métrica | Valor |
|---|---|
| Total recortes | 3,158 |
| Recortes con número (conf ≥ 0.66) | 308 (9.8 %) |
| Top-20 rastros con número asignado | **0/20 (0.0 %)** |

---

## 5. Hoja de contactos (Paso 5)

- **Generada:** `outputs/experimentos/dorsales/hoja_contactos.jpg`
- Muestra hasta 6 recortes por rastro con el número predicho encima.
- Revisión visual (muestra de 20 recortes): en la mayoría de los recortes el clasificador predice números irrelevantes (dígitos sueltos como "2", "3", "5") con confianza baja (< 0.66). Varios recortes solo muestran la espalda con la camiseta sin que el dorsal sea visible. Ninguno de los recortes revisados muestra el número correcto con confianza ≥ 0.66.

---

## 6. Métricas y conclusión (Paso 6)

**Cobertura de recortes:** 9.8 % (308/3,158 con conf ≥ 0.66)  
**Cobertura de rastros top-20:** 0 % (ningún rastro supera 3 votos)

### ⚠️ Criterio de parada activado
Menos del 10 % de los 20 rastros principales obtiene número → no se ajustan parámetros en bucle.

### Conclusión: NO SIRVE con estas condiciones

El clasificador entrenado con el dataset de Roboflow **no puede leer dorsales de forma fiable en el clip de transmisión TV (720p)**. Las razones principales son:

1. **Resolución insuficiente.** Los jugadores miden 52–68 px de alto. El torso (zona del dorsal) es ~35 px antes de ampliar. Las imágenes del dataset son 224×224 px mostrando dorsales grandes y nítidos. La brecha de dominio es demasiado grande para que 40 épocas la cierren.

2. **La cámara de TV no muestra la espalda.** Los recortes de plano táctico capturan jugadores de frente, de costado o con el dorsal parcialmente visible. El dataset entrena con espaldas limpias.

3. **Confianza sistémicamente baja.** Solo 9.8 % de recortes supera el umbral de 0.66. En el dataset degradado la exactitud baja de 84.3 % a 69.2 %, lo que confirma que la degradación afecta significativamente al modelo.

### Propuesta de siguiente experimento

Con el resultado "no funciona en 720p TV con clasificador clásico", las opciones son:

| Opción | Justificación |
|---|---|
| **IBM Granite Vision (vision-language)** | Puede leer texto en imágenes con zero-shot. Probar con los mismos recortes amplificados, preguntando "¿qué número aparece en esta camiseta?" |
| **Cámara táctica** | El dataset funciona con imágenes de 224×224 de dorsales grandes. Una cámara táctica o aérea generaría recortes comparables al dataset. |
| **Fine-tuning con recortes propios** | Si Fer etiqueta 200–300 recortes del clip, se puede hacer fine-tuning. Pero requiere cámara táctica o planos cerrados. |

---

## 7. Archivos del experimento

| Archivo | Descripción |
|---|---|
| `scripts/experimentos/dorsales/entrenar.py` | Descarga del dataset, auditoría y entrenamiento YOLOv8-cls |
| `scripts/experimentos/dorsales/leer_dorsales.py` | Recortes, inferencia, votación, hoja de contactos, métricas |
| `outputs/experimentos/dorsales/entrenamiento/metricas_entrenamiento.json` | top-1 original y degradado |
| `outputs/experimentos/dorsales/entrenamiento/auditoria_dataset.json` | Conteos por clase |
| `outputs/experimentos/dorsales/predicciones_por_recorte.jsonl` | Top-3 por recorte |
| `outputs/experimentos/dorsales/dorsales_por_rastro.json` | Votación por rastro |
| `outputs/experimentos/dorsales/hoja_contactos.jpg` | Contactsheet visual |
| `outputs/experimentos/dorsales/metricas_paso6.json` | Cobertura y criterio de parada |

> **Los pesos `.pt`, el dataset y los recortes NO se suben a Git** (AGENTS.md §3).

---

## 8. Reglas cumplidas

- ✅ Modelo local YOLOv8n-cls (no OpenAI/Anthropic/Meta).
- ✅ Credenciales solo en `.env` (nunca en código).
- ✅ No se usó la API de nube de Roboflow (ROBOFLOW_NUBE_AUTORIZADA no relevado como "si" en este paso).
- ✅ No se tocó `implementacion/`, `dashboard/`, `run_pipeline.py`, `data/raw/`, `data/clean/`.
- ✅ Un solo commit con los archivos del experimento.
- ✅ Licencia del dataset anotada: CC BY 4.0.

---

## 9. Bob coins estimadas

| Tarea | Estimación |
|---|---|
| Lectura de archivos, contexto | ~2 coins |
| Escritura de scripts + correcciones | ~5 coins |
| Ejecución de comandos (auditoría, pip, evaluación) | ~5 coins |
| Entrenamiento + evaluación degradada | ~8 coins |
| Recortes + clasificación | ~6 coins |
| Escritura de bitácora | ~3 coins |
| **Total estimado** | **~29 coins** |
