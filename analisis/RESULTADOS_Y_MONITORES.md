# 📊 Análisis Experimental, Benchmarks GPU y Monitores de Verificación (`M1` a `M4`)

Este documento concentra los resultados experimentales medidos sobre el pipeline de Omnimorph y las especificaciones de los **Monitores de Observabilidad** que auditan cada etapa del sistema.

---

## 1. Resumen de Benchmarks de Percepción en GPU Local (`C2 vs A`)

Evaluación realizada sobre el clip de referencia `2e57b9_0.mp4` ($1920\times 1080$, $25\text{ fps}$, $750\text{ cuadros} = 30\text{ s}$) en laptop **Intel Core i7-9750H + NVIDIA GTX 1660 Ti Max-Q (6 GB VRAM)**.

| Prueba | Qué ejecuta | Tiempo Total | FPS Bucle | RAM Pico | VRAM Pico | Fidelidad vs Original (`A`) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **`A_data`** | Los 6 modos originales en serie | $2,328\text{ s}$ ($38.8\text{ min}$) | — | $5.5\text{ GB}$ | $\le 1.5\text{ GB}$ | Referencia base ($100\%$) |
| **`C_data`** | Un solo proceso (cada modelo corre 1 vez/cuadro, sin video) | **$1,316\text{ s}$ ($21.9\text{ min}$)** | $0.68\text{ FPS}$ | $5.8\text{ GB}$ | $2.5\text{ GB}$ | **$100\%$ idéntico (`IoU = 1.0`)** |
| **`C2_video`** | 3 hilos en paralelo (decode $\rightarrow$ GPU $\rightarrow$ draw/write 6 videos) | **$1,335\text{ s}$ ($22.2\text{ min}$)** | $0.68\text{ FPS}$ | $5.9\text{ GB}$ | $2.4\text{ GB}$ | **$100\%$ idéntico (`IoU = 1.0`)** |

### Desglose de Tiempo de Cómputo por Agente (Media / p95 por cuadro)

| Agente | Rol | Media (ms) | p95 (ms) | % del Tiempo Total |
| :--- | :--- | :---: | :---: | :---: |
| **`A3` · BALL DETECTION** | YOLOv8 + `InferenceSlicer` ($640\times 640$) | $754.2\text{ ms}$ | $820.0\text{ ms}$ | **$51.0\%$** |
| **`A5` · TEAM CLASSIFICATION** | SigLIP $\rightarrow$ UMAP $\rightarrow$ KMeans($k=2$) | $463.2\text{ ms}$ | $494.1\text{ ms}$ | **$31.0\%$** |
| **`A2` · PLAYER DETECTION** | YOLOv8x a $1280\times 1280\text{ px}$ | $187.8\text{ ms}$ | $193.9\text{ ms}$ | $13.0\%$ |
| **`A1` · PITCH DETECTION** | YOLOv8x-pose ($32$ puntos clave) | $63.9\text{ ms}$ | $77.0\text{ ms}$ | $4.0\%$ |
| **`A4` · PLAYER TRACKING** | ByteTrack (`track_id` persistente) | $6.0\text{ ms}$ | $9.9\text{ ms}$ | $< 1.0\%$ |
| **`A6` · HOMOGRAFÍA** | OpenCV `findHomography` + RANSAC | $1.1\text{ ms}$ | $1.7\text{ ms}$ | $< 1.0\%$ |

---

## 2. Caso Testigo del Ruido de Homografía (Frame 300, $t = 12.0\text{ s}$)

En los datos crudos antes de aplicar `omnimorph-engine`, la falta de memoria en $H_t$ provoca picos de velocidad no físicos:

| Objeto / Jugador | Equipo | `pitch_x` (cm) | `pitch_y` (cm) | Velocidad Cruda (Diferencia Finita) | Diagnóstico |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Balón (`A3`)** | — | $7335$ | $5592$ | — | Posición de referencia |
| **FRA `track_id=18`** | `1` (FRA) | $7337$ | $5565$ | $600\text{ cm/s}$ ($21.6\text{ km/h}$) | Conduciendo el balón |
| **ARG `track_id=2`** | `0` (ARG) | $6722$ | $6510$ | $187\text{ cm/s}$ ($6.7\text{ km/h}$) | Presionando |
| **FRA `track_id=19`** | `1` (FRA) | $7877$ | $6541$ | **$1383\text{ cm/s}$ ($49.7\text{ km/h}$)** | **Outlier por salto de homografía $H_t$ (Corregido por P1+P2)** |
| **Árbitro (`tid=21`)** | `null` | $3858$ | $1505$ | $78\text{ cm/s}$ ($2.8\text{ km/h}$) | Casi estático |

---

## 3. Sistema de Monitores de Observabilidad por Etapa (`M1` a `M4`)

Para garantizar que cada operación se cumpla antes de pasar a la siguiente etapa, el sistema implementa **9 puntos de control (Monitores)**:

| ID Monitor | Etapa Supervisada | Métricas Auditadas | Umbral de Aprobación (`PASS`) |
| :--- | :--- | :--- | :--- |
| **`M1`** | **1) Percepción GPU Local** | Cuadros procesados, validez de homografía, IoU `C2 vs A` | `750/750` frames, `homography_valid == 100%`, `IoU >= 0.99` |
| **`M2.0`** | **2) Recepción Cloud ADK** | Columnas de `frames.parquet` y `objects.parquet`, detección de `fps` | $100\%$ de columnas requeridas presentes, `fps == 25` |
| **`M2.1`** | **2) Fase 1: Fuentes y Equipos** | Filas `track` ($17,232$), filas `ball` ($687$), varianza de `team_clean` | `det_rows_discarded == 17,951` y `team_flicker_tracks == 0` |
| **`M2.2`** | **2) Fase 2: Homografía `P1`** | Norma de Frobenius inter-frame $\|\Delta H_t\|_F$ y límites de cancha | Reducción de *jitter* $> 20\%$ y coordenadas dentro de $12000\times 7000\text{ cm}$ |
| **`M2.3`** | **2) Fase 3: Track Stitching `P3`** | Conteo de `track_id` antes vs. después del Algoritmo Húngaro | Reducción de $39$ IDs a $\approx 22\text{–}25$ sin mezclar equipos (`ARG != FRA`) |
| **`M2.4`** | **2) Fase 4: Cinemática `P2`** | Velocidad máxima (`speed_mps`) y aceleración (`acceleration_mps2`) | `max_player_speed_mps <= 9.5` ($34.2\text{ km/h}$) y `max_acc <= 5.0` |
| **`M2.5`** | **2) Fase 5: Ventanas JSON** | Cantidad de ventanas de $4.0\text{ s}$ y peso en bytes por ventana | $8$ ventanas generadas (`W01..W08`), cada una `< 600 bytes` |
| **`M3`** | **2) LLM `watsonx.ai` + Gobernanza** | Modelo usado, esquema JSON, longitud de narración, costo RU | Modelo `ibm/granite-3-8b-instruct`, $\le 45$ palabras/ventana, `0` alucinaciones |
| **`M4`** | **3) Dashboard Local + TTS** | Desfase temporal $|t_{\text{video}} - t_{\text{radar}}|$ y duración del audio TTS | Desfase $< 40\text{ ms}$ ($1\text{ frame}$) y `duration_s <= 4.0 s` por ventana |
