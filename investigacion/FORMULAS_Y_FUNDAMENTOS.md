# Fórmulas y Fundamentos — Omnimorph Engine

## 1. Coordenadas de cancha

La cancha FIFA estándar se modela como:
- **Largo:** 120 m = 12 000 cm  (eje X)
- **Ancho:** 70 m = 7 000 cm    (eje Y)
- Origen: portería ARG (x=0) → portería FRA (x=12 000)

### 1.1 Homografía

La homografía H es una matriz 3×3 que proyecta puntos de imagen (píxeles) a coordenadas
de cancha (cm). Se normaliza para garantizar estabilidad numérica:

```
H_norm = H / H[2,2]
```

**Suavizado EMA (Exponential Moving Average):**
```
H_ema[t] = α * H[t] + (1 - α) * H_ema[t-1],   α = 0.3
```

El Monitor M2.1 verifica que `homography_valid >= 95%` en el clip.

---

## 2. Track Stitching (Algoritmo Húngaro)

Para resolver la fragmentación de IDs de ByteTrack (hasta 43 IDs para 25 jugadores),
se aplica el algoritmo húngaro para asignar IDs cosidos (`track_id_stitched`).

**Costo de reasignación:**
```
cost(i, j) = dist_eucl(pos_i, pos_j) + λ * |equipo_i - equipo_j|
```

donde `λ = 1000` penaliza cambios de equipo.

**Umbral de stitching:** `max_dist = 300 cm` (3 m de cancha).

El Monitor M2.2 verifica que `n_stitched_ids <= 25` (número plausible de jugadores).

---

## 3. Cinemática Savitzky-Golay

Para suavizar posiciones y calcular velocidades reales:

```python
from scipy.signal import savgol_filter

pitch_x_smooth = savgol_filter(pitch_x, window_length=9, polyorder=3)
pitch_y_smooth = savgol_filter(pitch_y, window_length=9, polyorder=3)

vx = diff(pitch_x_smooth) * fps          # cm/s
vy = diff(pitch_y_smooth) * fps          # cm/s
v  = sqrt(vx² + vy²) / 100              # m/s
```

**Restricción física:** `v <= 9.5 m/s` (velocidad máxima humana en fútbol).
Valores superiores se marcan como `CLIP` y se limitan a 9.5 m/s.

El Monitor M2.3 verifica que ≥ 95% de velocidades estén en rango fisiológico.

---

## 4. Ventanas Tácticas de 4.0 s

El video de 30 s se divide en 8 ventanas de 4.0 s:

```
Ventana k: frames [k*100, (k+1)*100),  t_0 = k*4.0 s,  t_1 = (k+1)*4.0 s
```

Para cada ventana se calculan:

| Métrica | Fórmula |
|---------|---------|
| `block_height_m` | std(pitch_y ARG) + std(pitch_y FRA) |
| `block_compactness_m` | mean pairwise dist de la línea defensiva |
| `transition_speed_mps` | mean(v_balón) en la ventana |
| `pressure_context` | `"ataque"` si centroide_ARG > 6000 cm, `"defensa"` si < 6000, `"neutro"` |
| `dominant_team` | `"ARG"` si centroide_ARG > 6000, `"FRA"` si centroide_FRA < 6000 |

El Monitor M2.4 verifica que se generen exactamente 8 ventanas.

---

## 5. Separación track/ball y moda de equipo

Fase 1 del engine:
1. Separar filas `source == 'track'` (jugadores trackeados) de `source == 'ball'`
2. Para cada `track_id_stitched`, asignar equipo por moda de `team_id` a lo largo del clip:
   ```python
   team = objects[objects.track_id == tid].team_id.mode()[0]
   ```
3. Jugadores con `class_name == 'referee'` → equipo nulo

El Monitor M2.0 verifica que existen filas `source == 'track'` y `source == 'ball'`.

---

## 6. Monitor M1 — Observabilidad de Dataset

| Chequeo | Umbral |
|---------|--------|
| Frames totales | == 750 |
| `homography_valid` | >= 95% (≥ 712 frames) |
| Presencia de `source == 'track'` | ≥ 1 fila |
| Presencia de `source == 'ball'` | ≥ 1 fila |

Salida: `data/clean/monitor_m1.json` con `"status": "PASS"` o `"FAIL"`.

---

## 7. Monitor M3 — Auditoría LLM

| Chequeo | Regla |
|---------|-------|
| Modelo | DEBE ser `ibm/granite-3-8b-instruct` |
| Formato JSON | `{window_id, t0, t1, analisis_tactico, narracion_es}` |
| Longitud narración | `len(narracion_es.split()) <= 45` palabras |
| Anti-alucinación | `equipo_dominante` == `dominant_team` en tactical_summaries |

Salida: `data/clean/governance_audit.jsonl` con una línea por ventana.

---

## 8. Monitor M4 — Sincronización TTS

| Chequeo | Umbral |
|---------|--------|
| Duración audio | `duration_s <= 4.0 s` |
| Desfase de reloj | `< 40 ms` |
| Archivos generados | == 8 (uno por ventana) |

Salida: `data/clean/monitor_m4.json` con `"status": "PASS"` o `"FAIL"`.
