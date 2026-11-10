# Sesión 17 — Página Partido de Costa Rica vs. San Cristóbal y Nieves y generalización del frontend (Gemini)

**Fecha:** 2026-11-09  
**Agente:** Gemini (Antigravity)  
**Rama:** `feat-costa-rica`  
**Encargo de referencia:** `blueprints/encargo_gemini_pagina_partido.md`

---

## 1. Resumen de cambios realizados

### Paso 1: Conversión de `PLANTILLA_datos_partido.xlsx` al formato JSON del partido
Se generaron los tres archivos estructurados en `data/partidos/costa_rica_skn_eliminatorias_2026/partido/`:
- `contexto_partido.json`:
  - `partido_info` con los datos oficiales de la Jornada 1 del Grupo B (2024-06-06, 20:30 local, Estadio Nacional de Costa Rica, asistencia 15 700, cuarteta arbitral guatemalteca encabezada por Julio César de Jesús Luna Guzmán, marcador final `4-0`, descanso `1-0`, segundo tiempo `3-0`).
  - `equipos` con las claves `costa_rica` (`team_id: 1`, `CRC`) y `san_cristobal_y_nieves` (`team_id: 0`, `SKN`), respetando estrictamente los `team_id` definidos en `partido.config.json`.
  - Plantillas completas de 23 jugadores por selección (46 en total) con minutos calculados únicamente a partir de las columnas `Minuto entra` / `Minuto sale` de `Alineaciones` (titular sin cambio = `90`, titular sustituido al minuto $M$ = $M$, suplente que ingresa al minuto $M$ = $90 - M$, suplente sin ingreso = `0`) y lista de `eventos` extraída de la pestaña `Eventos` y capitanía.
  - Bloque `procedencia` con `origen: "PLANTILLA_datos_partido.xlsx"`, `recopilado_por: "Gemini (IA)"`, `validado: false` y las 15 fuentes públicas (`F1`–`F15`) con sus URLs canónicas.
- `estadisticas_partido.json`:
  - `resumen_comparativo` para `primer_tiempo`, `segundo_tiempo` y `tiempo_completo` con las claves `costa_rica` y `san_cristobal_y_nieves`.
- `cronologia_goles.json`:
  - Los 4 goles del partido (`40'` Orlando Galo, `49'` Orlando Galo, `82'` Josimar Alcócer, `84'` Andy Rojas) con sus asistentes y descripción breve.

### Paso 2: Generalización de `export_partido()` en `scripts/export_dashboard_data.py`
- `gol_muller/gol_muller_min11.json`, `assets/mapa_8_goles.svg`, `assets/radar_gol_muller.svg` y `PROCEDENCIA.md` pasaron a ser opcionales: solo se incluyen o copian si existen en la carpeta del partido activo, y se limpian de `dashboard/data/partido/` cuando no aplican.
- Se agregaron a `dashboard/data/partido/partido.json`:
  - `equipos_orden`: claves de equipo ordenadas por `team_id` (`0, 1`), resultando `["san_cristobal_y_nieves", "costa_rica"]` para Costa Rica y `["brasil", "alemania"]` para Brasil.
  - `colores`: mapa de `color_ui` tomado de `partido.config.json` vía `implementacion.partido_config` (`#FF1493` para SKN y `#00BFFF` para CRC).
  - `validado`: `false` para Costa Rica (desde `procedencia.validado`) y `true` por defecto cuando el partido no tiene bloque `procedencia` (Brasil).
  - `procedencia` y `vistos_en_clip` (cuando existen en el partido activo, cruzando `rastros_dorsales*.json`).

### Paso 3: Generalización de `partido.js`, `fichero.js` y `partido.html`
- **`dashboard/components/partido.js`:**
  - Eliminado `EQUIPOS` escrito a mano y las referencias fijas a Brasil, Alemania, Müller y Mineirão.
  - Aplicación dinámica de `--color-team-a` y `--color-team-b` desde `D.colores` y `D.equipos_orden`.
  - Construcción dinámica de las pestañas según los datos disponibles: `Ficha previa`, `Fichero`, `Comparativa` (muestra una única columna `Total` por selección y gráfico de barras `Total` cuando 1T y 2T son `null`), `Los 4 goles` (sin mapa SVG cuando no hay coordenadas) y ocultación automática de la pestaña `muller` cuando `D.gol_muller` no existe.
  - Aviso superior de calidad (`#hub-calidad`): cuando `D.validado === false`, muestra *"Datos públicos recopilados por IA con sus fuentes, pendientes de validación por el equipo de análisis."* con enlace interactivo a la lista desplegable de las 15 fuentes (`#fuentes-partido`) en `Ficha previa`.
  - Imagen del estadio: se omitió en Costa Rica por no contar con descarga de archivo libre en el entorno aislado (`dashboard/assets/estadio/`), conservando `mineirao.jpg` con su crédito para Brasil.
- **`dashboard/components/fichero.js`:**
  - Eliminado `EQUIPOS` fijo y estado inicial `equipo: 'brasil'`; ahora usa `datos.equipos_orden` (seleccionando inicialmente `equipos_orden[0]`, es decir, `San Cristóbal y Nieves` en Costa Rica y `Brasil` en Brasil).
  - Añadida la insignia `"Visto en el clip"` para los 10 jugadores identificados en `rastros_dorsales_borrador.json` (7 de Costa Rica y 3 de San Cristóbal y Nieves).
- **`dashboard/pages/partido.html`:**
  - Eliminados los textos fijos de Alemania y Gol de Müller del HTML inicial para que sean poblados dinámicamente por `partido.js`.

---

## 2. Datos que quedaron en `null` (por ser `SIN DATO` en la plantilla)

Siguiendo la regla estricta de no estimar ni completar ningún dato ausente en las fuentes públicas:

1. **`contexto_partido.json`:**
   - `partido_info.condiciones_climaticas`: `null` (clima nocturno no reportado en actas públicas).
   - `partido_info.resultado.clasificado`: `null` (partido de fase de grupos, Jornada 1).
2. **`estadisticas_partido.json`:**
   - En `primer_tiempo` y `segundo_tiempo`: todas las métricas salvo `marcador` y `goles` (`1-0` en 1T y `3-0` en 2T) quedaron en `null` para ambos equipos (`posesion_pct`, `tiros_totales`, `tiros_a_puerta`, `tiros_fuera`, `tiros_bloqueados`, `tiros_dentro_area`, `tiros_fuera_area`, `pases_completados`, `pases_intentados`, `pases_completados_intentados`, `precision_pases_pct`, `corners`, `faltas_cometidas`, `fueras_de_juego`, `tarjetas_amarillas`, `tarjetas_rojas`, `atajadas_portero`, `recuperaciones`, `xg_esperado`).
   - En `tiempo_completo`: `recuperaciones` quedó en `{"costa_rica": null, "san_cristobal_y_nieves": null}`. Todas las demás 18 métricas totales tienen su valor oficial (`F1, F9, F10`).
3. **`cronologia_goles.json`:**
   - Para los 4 goles: `segundo_oficial: null`, `tipo_jugada: null`, `xg: null`, `coordenadas_campo_cm: null`, `distancia_porteria_m: null`, `pie_remate: null`, `zona_remate: null`, `nota_tactica: null`.
   - Para el 3.º gol (`82'` Josimar Alcócer, jugada individual tras robo al arquero): `asistente: null`.

---

## 3. Comprobación de regresión con Brasil (`brasil_alemania_2014`)

1. **Comparación de `partido.json` contra `git show 11dd40a~1:dashboard/data/partido/partido.json`:**
   - Exportando con `$env:OMNIMORPH_PARTIDO = "brasil_alemania_2014"`, todas las claves previas (`partido`, `equipos`, `estadisticas`, `goles`, `gol_muller`) son **idénticas byte a byte** en estructura y valores al último `partido.json` de Brasil (`11dd40a~1`), apareciendo únicamente las tres claves nuevas requeridas (`equipos_orden: ["brasil", "alemania"]`, `colores: {"brasil": "#F5A623", "alemania": "#F5F3EE"}`, `validado: true`).
2. **Comprobación visual en el navegador:**
   - Con Brasil activo se muestran las 5 pestañas (`Ficha previa`, `Fichero`, `Comparativa 1T / 2T`, `Los 8 goles`, `Gol de Müller`), la fotografía de `mineirao.jpg`, la tabla comparativa de 6 columnas numéricas (`1T`, `2T`, `Total` para cada equipo) y los mapas SVG de los 8 goles y del gol de Müller.
3. **Restauración del partido activo:**
   - Al finalizar la prueba se volvió a ejecutar `.\.venv\Scripts\python.exe scripts\export_dashboard_data.py --solo-partido` con `costa_rica_skn_eliminatorias_2026` activo, verificando que `dashboard/data/partido/partido.json` quede exportado para Costa Rica y sin los SVG de Brasil.

---

## 4. Verificación en navegador y rutas de capturas (fuera de Git)

Se verificó `http://localhost:8600/pages/partido.html` en Chrome headless tanto en escritorio (`1440×950`) como en vista móvil (`375×812`), comprobando **0 errores de consola**, **0 excepciones JS** y **0 menciones** a `Brasil`, `Alemania`, `Müller` o `Mineirão` en todas las pestañas de Costa Rica.

Capturas generadas en `outputs/capturas_partido_sesion17/` (directorio `outputs/` ignorado en Git):
- `outputs/capturas_partido_sesion17/crc_desktop_ficha.png` — Ficha previa (escritorio) con marcador 4–0, árbitros, entrenadores y desplegable de 15 fuentes públicas.
- `outputs/capturas_partido_sesion17/crc_desktop_fichero.png` — Fichero inicial con San Cristóbal y Nieves (`equipos_orden[0]`) en color `#FF1493`.
- `outputs/capturas_partido_sesion17/crc_desktop_fichero_crc.png` — Fichero de Costa Rica en color `#00BFFF` e insignias `"Visto en el clip"`.
- `outputs/capturas_partido_sesion17/crc_desktop_comparativa.png` — Comparativa con gráfico `Total` y tabla de una sola columna `Total` por selección.
- `outputs/capturas_partido_sesion17/crc_desktop_goles.png` — Pestaña `Los 4 goles` sin mapa SVG y con relato por gol.
- `outputs/capturas_partido_sesion17/crc_movil_ficha.png`, `crc_movil_fichero.png`, `crc_movil_comparativa.png`, `crc_movil_goles.png` — Vistas responsivas en móvil (`375 px`).
- `outputs/capturas_partido_sesion17/bra_desktop_ficha.png`, `bra_desktop_muller.png` — Comprobación de las 5 pestañas de Brasil 1–7 Alemania.
