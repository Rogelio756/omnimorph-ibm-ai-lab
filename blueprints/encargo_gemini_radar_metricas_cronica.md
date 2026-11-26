# Encargo para Gemini: radar, métricas y crónica (C1–C3)

**Asignado a:** Gemini (Antigravity) · **Preparado por:** Claude Code, 2026-11-25
**Plazo:** hoy, miércoles 25. A las **18:00** se decide plan A o B (§6).
**Por qué:** `docs/meta_y_funciones.md` §2 y §4.

## 0. Reglas

1. Lee `AGENTS.md`, `docs/meta_y_funciones.md` y `bob_sessions/sesion_39_meta_y_validacion.md`.
2. Rama `feat-costa-rica`. Sin `stash`, `reset --hard`, `git add -A` ni `git add .`.
3. **Antes de cada commit muestra el diff y espera la aprobación del usuario.** El push también.
4. Bob trabaja a la vez en la misma carpeta. **Solo tocas los archivos de §1.**
5. Solo IBM Granite. No leas, muestres ni copies `.env`. No vuelvas a correr YOLO ni uses la GPU.
6. Si un paso falla tres veces por la misma causa, detente y repórtalo.
7. Python: `.venv/Scripts/python.exe`. Nunca corras `run_pipeline.py` sin `--use-real`: sobrescribe `data/raw/`.

## 1. Archivos tuyos

`scripts/recalibrar_posiciones.py` (nuevo), `scripts/probar_radar.py` (nuevo), `implementacion/cloud_tool/omnimorph_engine.py`, `implementacion/cloud_agent/agent_narrator.py`, `implementacion/cloud_agent/governance_monitor_m3.py`, `implementacion/dashboard/app.py` (solo para que no truene), `scripts/render_post_engine_video.py`, `scripts/export_dashboard_data.py`, `dashboard/pages/mateo.html`, `dashboard/components/data-adapter.js`, y los datos que generan (`data/`, `dashboard/data/`, `dashboard/media/`).

**No toques:** `chat_agent.py`, `serve.py`, `probar_chat_reglas.py` ni ninguna otra página (son de Bob).

## 2. Paso 0 · Respaldo

Copia `data/raw/`, `data/clean/`, `data/audio/`, `dashboard/data/` y `dashboard/media/` a `backups/pre_recalibracion_2026-11-25/`. Confirma con `git status` que el respaldo no entra a Git.
**Listo cuando:** el número de archivos y el tamaño coinciden con el origen.

## 3. C1 · Radar

`scripts/recalibrar_posiciones.py`:
1. Lee `data/raw/frames.parquet` (`kp_x`, `kp_y`, `kp_conf`) y `data/raw/objects.parquet`.
2. Por cuadro usa los puntos con `kp_conf > 0.5` y a más de 2 px de los bordes (imagen de 1280×720).
3. Con 4 o más: `cv2.findHomography(puntos, vertices, cv2.RANSAC, 150)`. Los vértices, en cm y en el mismo orden, son los de `SoccerPitchConfiguration` de `sports/` (cancha de 12000 × 7000).
4. Con menos de 4 (unos 7 cuadros), o si sale degenerada: la última válida; al inicio, la primera válida.
5. Recalcula `pitch_x`, `pitch_y` de **todas** las filas con recuadro (también el balón y el árbitro), con el punto inferior central `((x1+x2)/2, y2)`. Para el balón usa el mismo criterio que la percepción (`BOTTOM_CENTER`).
6. Posiciones a más de 3 m fuera de la cancha: `NaN`, y que las interpole la fase 1 del motor. **Ojo:** esa fase rellena con una regla proporcional a la imagen (`omnimorph_engine.py:110-113`); cámbiala por interpolación temporal del rastro y deja `NaN` si el rastro no tiene dato.
7. Guarda la `H` nueva y `homography_valid` verdadero solo si se calculó en ese cuadro. Escribe `data/clean/radar_error.json` (contrato en §5).

**Identidades:** la unión de rastros usa posiciones, y `rastros_dorsales.json` depende de `track_id_stitched`. **No la recalcules:** toma la relación `track_id → track_id_stitched` del `objects_cleaned.parquet` del respaldo (112 → 93; cada `track_id` tiene un solo destino) y aplícala. Así Rogers, Madrigal y los demás conservan su nombre.

**Pruebas** (`scripts/probar_radar.py`, sale con código 0 o 1):
- Error con punto excluido: para cada punto con confianza > 0.9, quítalo, ajusta con los demás (mínimo 5) y mide la distancia en metros. **Mediana ≤ 3 m.** Referencia de Claude: 1.9 m; método viejo, 9.7 m.
- En los cuadros 30, 72, 719, 929 y 1064, la mediana de `pitch_x` de todos los jugadores es **menor que 6000**.
- En el cuadro 300, la mediana de `pitch_x` de CRC es mayor que 6000.
- Los pares `track_id → track_id_stitched` son idénticos a los del respaldo.

## 3b. C1b · Calibración por líneas (25/11, reemplaza la H de C1)

La revisión contra el video encontró que los puntos del modelo no caen sobre las líneas reales. `scripts/calibrar_lineas.py` (de Claude, ya corrido; no lo cambies) deja `data/clean/calibracion_lineas.npz` (`H`, `valida`, `cobertura`) y `data/clean/radar_error.json`.

1. `recalibrar_posiciones.py`: usa `H` del npz. Donde `valida` es falso (1074–1079, toma cerrada) las posiciones son `NaN`, `homography_valid` es falso y no se interpola ni se arrastra nada en esos cuadros. Ya **no** escribe `radar_error.json`. Si falta el npz, termina con error claro.
2. Sin `except Exception: pass`: si algo falla, que se vea.
3. Identidades: guarda `data/partidos/costa_rica_skn_eliminatorias_2026/mapa_rastros.json` (versionable) desde el respaldo, y que el motor lea ese archivo con ruta absoluta desde la raíz. `backups/` no está en Git. Úsalo solo si el partido activo coincide.
4. Motor: conserva el orden original de las filas tras interpolar. Interpola huecos de hasta 15 cuadros por rastro y el balón igual; lo demás queda `NaN`.
5. Metros reales: la cancha es de 105 × 68 m. `x_m = pitch_x * 105/12000`, `y_m = pitch_y * 68/7000`. Aplica también en las métricas de C2.
6. `probar_radar.py`: reemplaza la prueba 1 por tres: (a) los 23 puntos de `scripts/radar_puntos_a_mano.json` con la H de `data/raw/frames.parquet`: mediana ≤ 1 m y máximo ≤ 2 m (referencia: 0.2 y 1.4); (b) `radar_error.json`: mediana ≤ 3 m y método «área grande sin usarla para calibrar»; (c) ninguna posición de rastro a más de 3 m fuera. Conserva las de los cuadros y las identidades, y pruébalas también con `pitch_x_smooth`.
7. Los JSON se escriben con `allow_nan=False`.

## 4. C2 · Métricas, y C3 · Crónica

**Motor, fase 5.** Con las posiciones suavizadas, por equipo y tramo:
- `posicion_m`: mediana de la distancia a la portería propia (según el sentido de ataque del config).
- `pct_campo_rival`: % de observaciones en la mitad rival.
- `largo_m`, `ancho_m`: en cada cuadro con 4 o más jugadores del equipo, percentil 90 menos percentil 10 en x y en y; la mediana de esos cuadros.
- `territorio`: con `a` y `b` = `pct_campo_rival` de cada equipo, gana el equipo con diferencia mayor que 20 puntos; si no, `"repartido"`. La misma regla para los dos.

**Equipo y clase:** por moda de cada `track_id` dentro de cada tramo (no de todo el clip: el rastro 29 cambia de equipo cerca del cuadro 740). Los árbitros por moda no cuentan.

Quita `block_height_m`, `block_compactness_m`, `transition_speed_mps` y `pressure_context`. `dominant_team` = `territorio` (o `"neutro"`), por compatibilidad. En `app.py` usa `.get(...)`.
**Prueba:** intercambiar los equipos y el sentido de ataque da el resultado espejo.

**M2.1:** agrega el error de `radar_error.json`; falla si la mediana pasa de 3 m. Datos sintéticos: se omite con aviso.

**Narrador.** El prompt recibe los números de **ambos** equipos y el territorio. Pide describir dónde está cada equipo y qué espacio ocupa; máximo 30 palabras. Prohíbe: posesión, presiona, domina, controla, lucha, intención de los jugadores y todo lo que no esté en los datos. El modo offline cumple lo mismo.

**M3.** Falla si la crónica o el análisis usa una palabra prohibida (posesión, presi-, domin-, control-, sin distinguir acentos), si afirma que está adelantado un equipo distinto del de `territorio`, o si usa un número que no está en los datos. **Prueba:** tres textos falsos (uno por regla) dan FAIL y uno correcto da PASS.

**Regenerar, en este orden:**
1. `recalibrar_posiciones.py` y `probar_radar.py`
2. `run_pipeline.py --use-real` (Granite: ~0.6 RU)
3. `scripts/render_post_engine_video.py` (quita «Altura bloque | Compac» de `:514` y pon las métricas nuevas)
4. `scripts/export_dashboard_data.py`
5. `scripts/export_transmision.py`

**`mateo.html`:** sustituye «Altura del bloque» y «Compacidad» por posición, largo, ancho y % en campo rival de **los dos** equipos; «Presión» por el territorio. `:477` y `:616`: «Comprobaciones del proceso: 9 de 9». `:762`: si no hay jugadores al inicio, «Cargando posiciones», no «Toma cerrada». «Con marcas» no debe tapar el marcador de TV. En 375 px, que el botón del chat no tape texto.

**Puerta final:** `probar_radar.py` 0 · 9/9 con los criterios nuevos · `probar_transmision.py --hasta 7` 0 · `probar_chat_reglas.py` 34 o más OK (después de integrar lo de Bob) · MATEO y Transmisión sin errores de consola.
**Puerta humana:** una hoja con los 8 tramos (cuadro del video, radar y frase) para que Fer y el usuario los aprueben. Si una frase contradice el video, se corrige el dato o el prompt, nunca el video.

## 5. Contrato con Bob (no lo cambies sin avisar)

`tactical_summaries.json`, por tramo:
```json
{"window_id":"W0","t0":0.0,"t1":4.5,"territorio":"CRC","dominant_team":"CRC",
 "equipos":{"SKN":{"posicion_m":44.0,"pct_campo_rival":8,"largo_m":20.1,"ancho_m":31.5},
            "CRC":{"posicion_m":79.0,"pct_campo_rival":86,"largo_m":22.4,"ancho_m":28.0}}}
```
Los valores son de ejemplo. `dashboard/data/mateo_data.json` lleva los mismos `equipos` y `territorio` en cada ventana.

`data/clean/radar_error.json`, copiado a `dashboard/data/metodo.json` como `radar_error`:
```json
{"mediana_m":1.9,"p90_m":5.6,"pct_mayor_5m":12,"puntos":4413,"cuadros":975,"metodo":"punto excluido"}
```

## 6. Corte de las 18:00

Avisa a las 18:00 con: salida de `probar_radar.py`, resultado de los 9 monitores y la hoja de los 8 tramos.
**Plan B:** si C1 no pasa, restaura el respaldo completo y no subas nada de datos. Si C1 pasa pero C3 no, deja radar y métricas y **no** publiques la crónica nueva: avisa para decidir qué tramos se retiran.

## 7. Al terminar

Registra tu sesión en `bob_sessions/` (siguiente número libre) y agrega **solo tu fila** al índice.
