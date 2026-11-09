# Sesión 12: Costa Rica como partido activo y pipeline completo
**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`
**Parte de:** sesión 10 (configuración) y sesión 11 (percepción de Gemini)

---

## 1. Revisión del trabajo de Gemini (sesión 11)

- **Commits:** `385212c` y `8e169ea` en la rama correcta, sin push. `scripts/run_mvp_perception.py` no estaba en Git, así que el commit lo agrega completo (905 líneas). Se revisó y no trae credenciales.
- **Mapeo de equipos:** se comprobó en `capturas/unificado_s30_f0900.png`. Los jugadores de verde salen como equipo 0 y los de guinda como equipo 1.
- **Sentido de ataque:** cuadra con el radar, donde SKN está replegado a la izquierda en s 25-36. También cuadra con el video, que a los 72 s, fuera de la ventana, muestra un balón parado de Costa Rica frente a la portería izquierda.

## 2. Configuración

- **`costa_rica_skn_eliminatorias_2026/partido.config.json`:**
  - `team_id 0` = San Cristóbal y Nieves (SKN), ataca hacia `+x`.
  - `team_id 1` = Costa Rica (CRC), ataca hacia `-x`.
- **`partido_activo.json`:** pasa a `costa_rica_skn_eliminatorias_2026`.
- **Volver a Brasil:** basta con poner `brasil_alemania_2014` y correr el pipeline. Los datos de Brasil también están en `backups/pre_costa_rica_2026-11-09/`.

## 3. Resultado de `run_pipeline.py --use-real`

- **Monitores:** 9 de 9 en PASS en 24.4 s.
- **Datos de entrada:** 1080 frames y 40 891 objetos. El dataset se sincronizó desde la carpeta de percepción de Costa Rica.
- **M3:** 8 llamadas a `ibm/granite-4-h-small`, 8 en PASS y 0 offline.
- **Tracking:** se pasa de 112 IDs crudos a 93 después de la costura. Siguen siendo muchos para unas 25 personas.
- **Ventanas:** 8 de 4.5 s. SKN domina en W0–W3 y W6; W4, W5 y W7 quedan neutras.

## 4. Observaciones

1. **Regla de dominio:** domina el equipo cuyo centroide pasa la mitad de la cancha. En este clip el juego está casi todo en el centro (centroides entre 5 600 y 8 300 cm), así que cualquier avance de SKN cuenta como dominio. Las narraciones dicen "San Cristóbal y Nieves domina" en la mayoría de las ventanas. Es fiel a la métrica, pero es una lectura pobre del juego. Puede mejorar con posesión del balón o con la jugada que entregue el equipo de análisis (pestaña Clip_15).
2. **Fragmentación del tracking:** 93 IDs después de la costura. Afecta al fichero de jugadores y a cualquier métrica por jugador.
3. **Velocidades:** la mediana de `v_mps` en `objects_cleaned` es alta, tanto en Costa Rica (10 m/s) como en el respaldo de Brasil (7.3 m/s). Es anterior a esta sesión y no se investigó.

## 5. Sin verificar / pendiente

- El dashboard web (`dashboard/`) sigue con los datos exportados de Brasil, porque `scripts/export_dashboard_data.py` no se ha corrido. Streamlit lee `data/clean`, que ya es Costa Rica, pero sus etiquetas siguen diciendo Brasil.
- El chatbot sigue con los datos de Brasil hasta que llegue la plantilla del equipo de análisis.
- No se escuchó el audio TTS generado.
