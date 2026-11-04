# Resultados y Monitores — Análisis del Pipeline Omnimorph

## 1. Estado consolidado de monitores (última corrida)

| Monitor | Nombre | Estado | Detalle |
|---------|--------|--------|---------|
| M1 | Observabilidad de Percepción | PASS | 750/750 frames, homografía 100% |
| M2.0 | Separación track/ball | PASS | track ≥ 1, ball ≥ 1 |
| M2.1 | Homografía EMA normalizada | PASS | 750/750 válidas |
| M2.2 | Track Stitching | PASS | n_stitched ≤ 25 |
| M2.3 | Cinemática Savitzky-Golay | PASS | ≥ 95% v ≤ 9.5 m/s |
| M2.4 | Ventanas Tácticas | PASS | 8/8 ventanas generadas |
| M2.5 | Integridad pipeline | PASS | 0 errores end-to-end |
| M3 | Auditoría LLM | PASS | granite-3-8b-instruct, ≤45 palabras |
| M4 | Sincronización TTS | PASS | duration ≤ 4.0 s, desfase < 40 ms |

---

## 2. Resultados de telemetría — Video 2e57b9_0.mp4

### 2.1 frames.parquet (750 filas)

| Columna | Descripción | Rango observado |
|---------|-------------|----------------|
| `frame` | 0–749 | 0–749 |
| `t` | tiempo en s | 0.0–29.96 |
| `n_det` | detecciones totales | 20–28 |
| `n_track` | jugadores trackeados | 18–25 |
| `ball_found` | balón detectado | True en 687/750 (91.6%) |
| `homography_valid` | H calculable | True en 750/750 (100%) |
| `n_kp_visible` | keypoints visibles | 18–32 (media 25.9) |

### 2.2 objects.parquet (35 870 filas)

| source | filas | descripción |
|--------|-------|-------------|
| `det` | 17 951 | detecciones crudas (YOLOv8x) |
| `track` | 17 232 | jugadores trackeados (ByteTrack) |
| `ball` | 687 | posiciones de balón |

### 2.3 Track Stitching

- `track_id` originales: hasta 43 IDs distintos
- `track_id_stitched` post-costura: ≤ 25 IDs (≤ jugadores en cancha)
- Caso testigo `track_id=19`: frame 300, equipo FRA, pitch_x≈7877 cm, pitch_y≈6541 cm

---

## 3. Ventanas tácticas (8 × 4.0 s)

| Ventana | t0–t1 | Equipo dominante | Presión |
|---------|-------|-----------------|---------|
| W0 | 0.0–4.0 s | ARG | neutro |
| W1 | 4.0–8.0 s | ARG | ataque |
| W2 | 8.0–12.0 s | ARG | ataque |
| W3 | 12.0–16.0 s | ARG | ataque |
| W4 | 16.0–20.0 s | FRA | defensa |
| W5 | 20.0–24.0 s | FRA | defensa |
| W6 | 24.0–28.0 s | neutro | neutro |
| W7 | 28.0–32.0 s | ARG | ataque |

---

## 4. Cuellos de botella identificados

| Etapa | ms/frame (media) | % del total |
|-------|-----------------|-------------|
| Ball detection (InferenceSlicer) | 749.7 | 51% |
| Team classification (SigLIP+UMAP) | 460.8 | 31% |
| Player detection (YOLOv8x) | 185.3 | 13% |
| Pitch detection (YOLOv8x-pose) | 54.0 | 4% |
| Tracking (ByteTrack) | 5.8 | <1% |
| Homography | 1.1 | <1% |

---

## 5. Análisis de gobernanza LLM (M3)

- Modelo usado: `ibm/granite-3-8b-instruct` ✓
- Ventanas procesadas: 8/8
- Narraciones con ≤ 45 palabras: 8/8 (100%)
- Chequeo anti-alucinación: 8/8 coinciden con dominant_team
- Latencia media: ~1200 ms (modo online), ~5 ms (modo offline)
- Tokens de entrada (media): ~350 tokens/ventana
- Tokens de salida (media): ~80 tokens/ventana

---

## 6. Monitor M4 — Sincronización TTS

- Clips de audio generados: 8/8
- Duración media: 2.8 s (máx: 3.7 s)
- Todos `duration_s <= 4.0 s`: ✓
- Desfase de reloj medio: 12 ms (< 40 ms umbral)

---

## 7. Dependencias del pipeline

```
pandas >= 1.5
numpy >= 1.24
scipy >= 1.10
pyarrow >= 10.0
scikit-learn >= 1.2
python-dotenv >= 1.0
pyttsx3 >= 2.90        # TTS local primario
ibm-watsonx-ai >= 1.0  # LLM (IBM watsonx.ai)
streamlit >= 1.30      # Dashboard
huggingface_hub >= 0.20  # Descarga bajo demanda
datasets >= 2.0          # Parquet de HuggingFace
```

Todas estas dependencias están disponibles en el `.venv` del proyecto.
