# Plan: Página Partido — datos de Fer
**Basado en:** `blueprints/encargo_bob_pagina_partido_fer.md`
**Rama:** `feat-costa-rica` · Sin commit ni push · Sin tocar `chat_agent.py`, `chat_verificador.py`, `importar_datos_fer.py`
**Presupuesto:** ~40 Bob coins

---

## Decisiones de diseño aprobadas

| Decisión | Opción elegida |
|---|---|
| Colores de equipos | Campo `color_uniforme` en `partido.config.json` + CSS vars `--color-partido-a/b` separados de `--color-team-a/b` |
| Mini-cancha (Goles) | Punto sobre rectángulo sin dirección, con etiqueta de zona |
| Eventos | Pestaña nueva «Eventos» |
| SVGs de Fer | `esquemas_tacticos.svg` y `uniformes_y_zonas.svg` en Ficha; `timeline_partido.svg` en la pestaña Eventos |

---

## Contexto técnico clave

- `export_dashboard_data.py` → `export_partido()` escribe `dashboard/data/partido/partido.json`.
- `partido.js` → `iniciar()` lee `D.colores` y hace `root.setProperty('--color-team-a', ...)`. Esos vars alimentan `.swatch--bra/.bar--bra` en `match-hub.css`.
- `CLASES_EQ = ['bra', 'ger']` en `partido.js` y `fichero.js` mapean el índice del equipo a la clase CSS.
- `color_ui` (SKN `#FF1493`, CRC `#00BFFF`) debe quedar **intacto** — lo usan Mateo y los vídeos.
- Brasil (`brasil_alemania_2014`) no tiene `color_uniforme`, `eventos`, `metricas_adicionales` ni `rendimiento_individual_destacado`: cada bloque nuevo debe ocultarse si falta el dato.
- `coordenadas_fifa` escala 0–100; x crece hacia la portería rival (todos los goles CRC tienen x ≥ 79).
- Los 3 SVG de Fer están en `data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/assets/`.

---

## Sub-tasks

### ST-1 — Exportar `eventos` y `colores_uniforme` en `export_dashboard_data.py`
**Status:** [ ] pending

**Intent:** El JS necesita `D.eventos` y `D.colores_uniforme` en `partido.json`. Los SVG de Fer también deben copiarse a `dashboard/data/partido/`.

**Expected Outcomes:**
- `partido.json` incluye clave `eventos` (array de los 30 eventos) si `eventos_partido.json` existe.
- `partido.json` incluye clave `colores_uniforme` (dict equipo→hex) si existe en el config.
- Los 3 SVG de Fer (`esquemas_tacticos.svg`, `uniformes_y_zonas.svg`, `timeline_partido.svg`) están en `dashboard/data/partido/`.
- Brasil: si no hay `eventos_partido.json` ni `color_uniforme`, las claves simplemente no aparecen.

**Todo:**
1. En `export_partido()`, leer `eventos_partido.json` si existe y añadirlo a `data["eventos"]`.
2. En `export_partido()`, leer `color_uniforme` por equipo desde `PARTIDO.equipo(i)` y construir `data["colores_uniforme"]` si al menos un equipo lo tiene.
3. Ampliar la lista `opcionales` para incluir los 3 SVG de Fer desde `fer_validacion/assets/`.
4. Añadir `color_uniforme` al objeto de cada equipo en `partido.config.json` de Costa Rica.
5. Añadir `color_uniforme` a la clase `Equipo` en `implementacion/partido_config.py` (campo opcional, `None` por defecto).
6. Correr `export_dashboard_data.py --solo-partido` y verificar el JSON resultante.

**Archivos:** `scripts/export_dashboard_data.py`, `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json`, `implementacion/partido_config.py`

---

### ST-2 — Tokens de color de uniforme: `partido.config.json` + CSS + `partido.js`
**Status:** [ ] pending

**Intent:** Que la página Partido use los colores reales del uniforme (CRC rojo, SKN verde) sin romper Mateo ni los vídeos.

**Expected Outcomes:**
- `--color-partido-a` y `--color-partido-b` se definen en `tokens.css` con valor de fallback `var(--color-team-a/b)`.
- `.swatch--partido-a`, `.swatch--partido-b`, `.bar--partido-a`, `.bar--partido-b` en `match-hub.css`.
- `iniciar()` en `partido.js`: si `D.colores_uniforme` existe, hace `setProperty('--color-partido-a', ...)` para cada equipo.
- `EQUIPOS` usa el sufijo `partido-a/partido-b` si `colores_uniforme` está presente, `bra/ger` si no (Brasil sigue igual).
- Accesibilidad: texto de equipo siempre visible junto a cada swatch; tooltip en barras.
- Leyenda en Comparativa: frase corta «Colores del uniforme real (distintos a los del análisis de video)».

**Todo:**
1. Añadir en `tokens.css`: `--color-partido-a: var(--color-team-a)` y `--color-partido-b: var(--color-team-b)`.
2. Añadir en `match-hub.css`: `.swatch--partido-a`, `.bar--partido-a`, `.swatch--partido-b`, `.bar--partido-b`.
3. Añadir en `fichero.css`: `.camiseta--partido-a`, `.camiseta--partido-b`.
4. Modificar `CLASES_EQ` en `partido.js`: usar `['partido-a', 'partido-b']` si `D.colores_uniforme` existe, `['bra', 'ger']` si no.
5. En `iniciar()`, si `D.colores_uniforme`, hacer `setProperty('--color-partido-a', ...)` y `setProperty('--color-partido-b', ...)`.
6. Mismo cambio en `fichero.js`: `CLASES_EQ` debe seguir la misma lógica; pasarlo como parámetro desde `renderFichero`.
7. Verificar contraste: rojo `#c8102e` sobre fondo oscuro `#111111` y verde `#009739` sobre `#111111`.

**Archivos:** `dashboard/styles/tokens.css`, `dashboard/styles/components/match-hub.css`, `dashboard/styles/components/fichero.css`, `dashboard/components/partido.js`, `dashboard/components/fichero.js`

---

### ST-3 — Goles: `jugada`, `zona_remate`, `pie_remate`, segundo oficial, mini-cancha
**Status:** [ ] pending

**Intent:** La columna «Jugada» hoy muestra «—» (lee `tipo_jugada`, null). El detalle muestra `narracion`. Hay que mostrar el relato de Fer.

**Expected Outcomes:**
- Columna «Jugada» en la tabla muestra las primeras ~60 chars de `g.jugada` (o `g.narracion` si falta).
- El detalle del gol seleccionado muestra: `jugada` completo, `zona_remate`, `pie_remate`, y el tiempo oficial (min:seg derivado de `segundo_oficial`).
- Mini-cancha SVG inline con un punto en la posición `coordenadas_fifa` (x, y en 0–100, sin dirección, con etiqueta de zona).
- Si `g.jugada` y `g.coordenadas_fifa` faltan (Brasil), el comportamiento es idéntico al actual.

**Todo:**
1. En `renderGoles`, cambiar la celda de Jugada: usar `g.jugada || g.tipo_jugada || '—'` (truncar a ~60 chars en la tabla).
2. En `marcarGol`, añadir: `jugada` completo, `zona_remate`, `pie_remate`, tiempo oficial (segundos → `mm:ss`).
3. Dibujar mini-cancha SVG: rectángulo 105×68 (proporciones reales), punto en `x%` / `y%` del rectángulo, sin portería ni dirección. Mostrarla solo si `g.coordenadas_fifa` existe.
4. Eliminar la cabecera «xG est.» y «Dist. (m)» de la tabla si todos los valores son nulos (para no mostrar columnas vacías).

**Archivos:** `dashboard/components/partido.js`

---

### ST-4 — Nueva pestaña «Eventos»
**Status:** [ ] pending

**Intent:** Los 30 eventos de `eventos_partido.json` necesitan una vista cronológica.

**Expected Outcomes:**
- Pestaña «Eventos» aparece solo cuando `D.eventos` existe y tiene al menos un elemento.
- Cada evento muestra: minuto, icono/etiqueta de tipo, nombre del jugador (si lo hay), descripción.
- Color del equipo (`.swatch--partido-a/b`) junto a cada evento según `evento.equipo`.
- El SVG `timeline_partido.svg` aparece antes de la lista de eventos con crédito «Diagrama: equipo de análisis (Fer)».
- Si no hay datos (Brasil), la pestaña no aparece.

**Todo:**
1. Añadir `'eventos'` a `TODOS_TABS` y crear `$('tab-eventos')` / `$('panel-eventos')` en `partido.html`.
2. Escribir `renderEventos()` en `partido.js`: itera `D.eventos`, construye fila por tipo con icono emoji/label y color de equipo.
3. Mapa de tipo → icono: `gol`⚽ `tarjeta_amarilla`🟨 `tarjeta_roja`🟥 `cambio`🔄 `poste`⬜ `atajada`🧤 `ocasion_clara`💥 `atencion_medica`➕ `inicio/descanso/final`⏱.
4. Mostrar `timeline_partido.svg` como `<img>` con crédito antes de la lista.
5. Añadir `'eventos'` a `RENDER` y la lógica de visibilidad en `iniciar()`.

**Archivos:** `dashboard/components/partido.js`, `dashboard/pages/partido.html`

---

### ST-5 — Fichero: `rol_tactico` + rendimiento individual
**Status:** [ ] pending

**Intent:** Cada jugador en la pestaña Fichero debe mostrar su rol táctico y sus stats FotMob.

**Expected Outcomes:**
- El panel de detalle del jugador muestra `rol_tactico` si está en su entrada de `plantilla`.
- Si el jugador tiene fila en `rendimiento_individual_destacado`, se muestran: calificación FotMob, toques, pases (completados/intentados), tiros, duelos, recuperaciones. Para porteros: atajadas y goles recibidos en lugar de tiros y duelos.
- Si no hay `rendimiento_individual_destacado` (Brasil), el bloque no aparece.
- El encabezado de equipo muestra `esquema_nota` si existe.

**Todo:**
1. En `fichero.js`, construir un mapa `{equipo+dorsal → stats}` desde `datos.estadisticas.rendimiento_individual_destacado` si existe.
2. En `jugadoresDe()`, añadir `rol_tactico` al objeto del jugador desde `j.rol_tactico` (plantilla).
3. En `pintarDetalle()`, añadir: `rol_tactico` como texto, bloque de stats FotMob si tiene datos, distinguiendo porteros.
4. En el `team-head` de cada equipo, mostrar `eq.esquema_nota` si existe.
5. `datos.estadisticas` llega a `fichero.js` desde `datos` que ya incluye el campo; no hace falta cambio en el exporter.

**Archivos:** `dashboard/components/fichero.js`

---

### ST-6 — Comparativa: `metricas_adicionales`
**Status:** [ ] pending

**Intent:** Las 22 métricas adicionales (postes, grandes ocasiones, duelos, etc.) no aparecen en la tabla de Comparativa.

**Expected Outcomes:**
- Después de «Todas las métricas» (métricas principales) aparece una segunda sección «Métricas adicionales» con la misma estructura de tabla (1T / 2T / Total donde aplique).
- Si `metricas_adicionales` no existe (Brasil), la segunda tabla no se renderiza.
- Las claves se muestran con etiquetas en español (definidas en un mapa en JS).

**Todo:**
1. Crear mapa `ETIQUETAS_ADICIONALES` con ~22 claves → nombre en español.
2. Escribir `tablaAdicional()` en `partido.js`: lee `D.estadisticas.metricas_adicionales`, construye tabla con la misma lógica que `tablaCompleta()` pero usando los periodos disponibles en `metricas_adicionales`.
3. En `renderComparativa()`, añadir la segunda sección después de `tablaCompleta()` si hay datos.
4. Añadir la leyenda de colores de uniforme como `<p class="caption">`.

**Archivos:** `dashboard/components/partido.js`

---

### ST-7 — Ficha: contexto competitivo, datos no disponibles, discrepancias + SVGs de Fer
**Status:** [ ] pending

**Intent:** La pestaña Ficha tiene espacio para los datos de contexto, transparencia y los diagramas tácticos.

**Expected Outcomes:**
- Párrafo de `partido.contexto_competitivo` debajo de los stats del partido si el campo existe.
- `<details>` «Datos no disponibles» listando `partido.datos_no_disponibles` si existe.
- `<details>` «Discrepancias entre fuentes resueltas» listando `partido.discrepancias_resueltas` si existe.
- Diagrama `esquemas_tacticos.svg` mostrado en Ficha con `<img>` y crédito «Diagrama: equipo de análisis (Fer)».
- Diagrama `uniformes_y_zonas.svg` mostrado en Ficha antes de la sección de fuentes.
- Si los campos no existen (Brasil), nada se muestra.

**Todo:**
1. En `renderFicha()`, añadir párrafo de `info.contexto_competitivo` si existe.
2. Añadir `<details>` para `info.datos_no_disponibles` (array de strings) si existe.
3. Añadir `<details>` para `info.discrepancias_resueltas` (array de strings) si existe.
4. Mostrar `esquemas_tacticos.svg` y `uniformes_y_zonas.svg` con `<img src="../data/partido/esquemas_tacticos.svg">` y crédito, solo si los archivos se copiaron (comprobar existencia en JS con `onerror`).
5. Verificar que `partido.json` contenga `contexto_competitivo`, `datos_no_disponibles`, `discrepancias_resueltas` (vienen de `contexto_partido.json → partido_info`; ya están en el exporter vía `data["partido"] = contexto["partido_info"]`).

**Archivos:** `dashboard/components/partido.js`

---

## Verificación final (blueprint §4)

Después de completar todos los sub-tasks:
1. `.\.venv\Scripts\python.exe scripts\export_dashboard_data.py --solo-partido`
2. `.\.venv\Scripts\python.exe dashboard\serve.py --port 8600`
3. Abrir `http://localhost:8600/pages/partido.html`, Ctrl+F5, revisar cada pestaña.
4. Comprobar manualmente:
   - Jugada del 2-0 (49', Galo, pie izquierdo, zurdazo rastrero)
   - 4 tarjetas amarillas (26', 45'+4', 58', 63') en Eventos
   - Calificación de Galo (9.17) en Fichero
   - Tiros al poste de Costa Rica (2) en Comparativa / métricas adicionales
5. `git status` solo debe mostrar los archivos tocados.

## Al terminar

Escribir `bob_sessions/sesion_26_pagina_partido_fer.md` y actualizar `bob_sessions/README.md`.
