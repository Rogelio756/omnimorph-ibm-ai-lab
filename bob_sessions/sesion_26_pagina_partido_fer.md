# Sesión 26 — Página Partido: datos de Fer en el frontend

**Fecha:** 2026-11-14 · **Agente:** IBM Bob IDE · **Rama:** `feat-costa-rica`

---

## 1. Qué se pidió

Encargo en `blueprints/encargo_bob_pagina_partido_fer.md` (preparado por Claude Code):
mostrar en `dashboard/pages/partido.html` toda la información que Fer entregó: jugadas
reales de los 4 goles, colores del uniforme, línea de tiempo de eventos, rendimiento
individual FotMob/Opta, métricas adicionales y los diagramas SVG del equipo de análisis.

Reglas: rama `feat-costa-rica`, sin commit ni push, sin `git add -A`.
No tocar `chat_agent.py`, `chat_verificador.py` ni `importar_datos_fer.py`.

---

## 2. Plan ejecutado

Plan completo en `blueprints/plan_pagina_partido_fer.md` (7 sub-tasks).
Aprobado por el usuario antes de escribir código (sesión en modo Plan → modo Agent).

---

## 3. Qué se hizo — sub-task por sub-task

### ST-1 · Exportar `eventos` y `colores_uniforme`

**`scripts/export_dashboard_data.py`**
- `export_partido()` lee `eventos_partido.json` si existe y añade clave `eventos` al JSON.
- `export_partido()` lee `color_uniforme` de `partido.config.json` y construye `colores_uniforme`
  (mapeando `team_id` → clave de equipo). Solo aparece si al menos un equipo lo tiene.
- Lista `opcionales` ampliada con los 3 SVG de Fer desde `fer_validacion/assets/`.

**`data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json`**
- Añadido `color_uniforme: { principal, accento }` por equipo:
  - SKN: `#009739` / `#166534` (verde)
  - CRC: `#c8102e` / `#102a56` (rojo / azul marino)

### ST-2 · Tokens de color de uniforme

**`dashboard/styles/tokens.css`** — añadidas variables `--color-partido-a/b`
(fallback `var(--color-team-a/b)` para partidos sin `color_uniforme`).

**`dashboard/styles/components/match-hub.css`** — añadidas reglas CSS:
`.swatch--partido-a/b`, `.bar--partido-a/b`, `.tbl .group--partido-a/b`.

**`dashboard/styles/components/fichero.css`** — añadidas reglas:
`.camiseta--partido-a/b`, `.fichero__detalle--partido-a/b`, `.carta--partido-a/b`.

**`dashboard/components/partido.js`** — `iniciar()`:
- Si `D.colores_uniforme` existe, hace `setProperty('--color-partido-a', ...)` para cada equipo.
- `EQUIPOS` usa clase `partido-a/b` cuando hay `colores_uniforme`, `bra/ger` si no (Brasil intacto).

**`dashboard/components/fichero.js`** — misma lógica de clase dinámica.

### ST-3 · Goles: `jugada`, `zona_remate`, `pie_remate`, segundo oficial, mini-cancha

**`dashboard/components/partido.js`**
- Columna «Jugada» en tabla usa `g.jugada` truncado a 60 chars (antes leía `tipo_jugada`, null).
- Columnas xG y Dist. solo se renderizan si al menos un gol tiene el dato (evita columnas vacías).
- `marcarGol()` muestra: encabezado con minuto y reloj oficial (`segundo_oficial` → `mm'ss"`),
  bloque Remate con `pie_remate` y `zona_remate`, mini-cancha SVG inline, jugada completa y
  análisis táctico.
- Función `miniCancha(coordenadas)`: rectángulo 210×136, punto en `coordenadas_fifa` (0–100),
  línea central, sin dirección ni porterías. CSS `.mini-cancha__*` en `match-hub.css`.

### ST-4 · Nueva pestaña «Eventos»

**`dashboard/pages/partido.html`** — añadidos `tab-eventos` y `panel-eventos`.

**`dashboard/components/partido.js`**
- `'eventos'` añadido a `TODOS_TABS`.
- `iniciar()` activa la pestaña solo si `D.eventos && D.eventos.length`.
- `renderEventos()`: muestra `timeline_partido.svg` con crédito, luego 30 filas con icono por
  tipo, minuto, tipo, swatch del equipo, jugador y descripción.
- CSS `.eventos-lista`, `.evento-fila__*` en `match-hub.css` (responsive a 600 px).

### ST-5 · Fichero: `rol_tactico` + rendimiento individual

**`dashboard/components/fichero.js`**
- `indiceRendimiento(datos)`: construye mapa `equipo|dorsal → stats` desde
  `estadisticas.rendimiento_individual_destacado` (si existe).
- `jugadoresDe()`: extrae `rol_tactico` de cada entrada de plantilla; añade `rendimiento` al objeto.
- `pintarDetalle()`: muestra `rol_tactico` en la línea de puesto; si hay `rendimiento`, renderiza
  bloque FotMob/Opta (6 cifras; porteros con atajadas/goles_recibidos en lugar de tiros/duelos).
- Botones de equipo en filtros muestran esquema táctico abreviado (`eq.esquema_nota.split(' ')[0]`).
- CSS `.fichero__rend-titulo`, `.fichero__cifras--rend` en `fichero.css`.

### ST-6 · Comparativa: `metricas_adicionales`

**`dashboard/components/partido.js`**
- `ETIQUETAS_ADICIONALES`: mapa de 22 claves reales del JSON → etiquetas en español.
- `tablaAdicional()`: construye tabla con los periodos presentes en `metricas_adicionales`
  (1T / 2T / Total); no renderiza si no hay datos (Brasil seguro).
- `renderComparativa()`: añade la tabla adicional después de «Todas las métricas» y una nota
  de colores de uniforme si `D.colores_uniforme` existe.

### ST-7 · Ficha: contexto, datos no disponibles, discrepancias + SVGs de Fer

**`dashboard/components/partido.js`** `renderFicha()`:
- Párrafo de `info.contexto_competitivo` (formato de ronda y resultado del grupo).
- `<details>` «Datos no disponibles» con 10 campos y motivo.
- `<details>` «Discrepancias entre fuentes resueltas» con 6 entradas.
- `esquemas_tacticos.svg` y `uniformes_y_zonas.svg` con `<img onerror>` y crédito
  «Diagrama: equipo de análisis (Fer)».

---

## 4. Verificación

```
.\.venv\Scripts\python.exe scripts\export_dashboard_data.py --solo-partido
→ [OK] partido.json (51 KB) + esquemas_tacticos.svg, uniformes_y_zonas.svg, timeline_partido.svg
```

Servidor arrancado en `localhost:8600`. Checks del encargo §4:

| Check | Resultado |
|---|---|
| Jugada del 2-0 (49', Galo, pie izquierdo) | ✅ `pie_remate: Pie izquierdo`, jugada completa visible |
| 4 tarjetas amarillas (26', 45'+4', 58', 63') | ✅ Exactas en pestaña Eventos |
| Calificación de Galo (9.17) | ✅ En Fichero, bloque FotMob/Opta |
| Tiros al poste CRC (2) | ✅ En Comparativa, tabla métricas adicionales |

Sintaxis JS verificada con `node --check`. Sin errores en consola.
`git status` solo muestra los archivos tocados intencionalmente.

---

## 5. Archivos modificados por esta sesión

| Archivo | Cambio |
|---|---|
| `scripts/export_dashboard_data.py` | Exporta `eventos`, `colores_uniforme` y SVGs de Fer |
| `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json` | Campo `color_uniforme` por equipo |
| `dashboard/data/partido/partido.json` | Regenerado (incluye `eventos` y `colores_uniforme`) |
| `dashboard/data/partido/esquemas_tacticos.svg` | Copiado de `fer_validacion/assets/` |
| `dashboard/data/partido/uniformes_y_zonas.svg` | Copiado de `fer_validacion/assets/` |
| `dashboard/data/partido/timeline_partido.svg` | Copiado de `fer_validacion/assets/` |
| `dashboard/pages/partido.html` | Tab + panel `eventos` añadidos |
| `dashboard/components/partido.js` | Colores uniforme, Goles, Eventos, Comparativa, Ficha |
| `dashboard/components/fichero.js` | Colores uniforme, `rol_tactico`, rendimiento individual |
| `dashboard/styles/tokens.css` | `--color-partido-a/b` |
| `dashboard/styles/components/match-hub.css` | Reglas `partido-a/b`, mini-cancha, eventos |
| `dashboard/styles/components/fichero.css` | Reglas `partido-a/b`, rendimiento |
| `blueprints/plan_pagina_partido_fer.md` | Plan técnico aprobado (nuevo) |

---

## 6. Lo que NO se hizo (límites del encargo)

- No se hizo commit ni push (instrucción explícita).
- No se tocaron `chat_agent.py`, `chat_verificador.py` ni `importar_datos_fer.py`.
- No se re-exportaron datos de Brasil (el código es compatible, verificado por razonamiento).
- El validador de Fer (`validate_data.py`) no se corrió (era código descargado, fuera del scope).
- El tramo T18 de Lassiter sigue sin confirmar (pendiente de sesiones anteriores).

---

## 7. Coins usados

Estimado: ~35–38 Bob coins (dentro del tope de ~40).

---

## Revisión y pulido de Claude Code (2026-11-14)

Revisado en el navegador: las 5 pestañas sin errores de consola, sin scroll horizontal a 375 px, y los 4 datos de control coinciden con Fer. Cambios hechos sobre el trabajo de Bob:

- **Brasil:** las leyendas «Diagrama: equipo de análisis (Fer)» quedaban sueltas cuando el SVG no existe. Ahora van dentro de la figura y se quitan juntas.
- **Mini cancha corregida:** el eje y estaba invertido. Según la convención IFES/Opta de `ANALISIS_PARTIDO.md`, y = 0 es la banda derecha mirando a la portería rival. Ahora dibuja áreas, porterías y círculo central, y lleva la leyenda «ataca hacia la derecha». Su etiqueta accesible dice la distancia a la línea de gol.
- **Sin jerga de fuentes:** se quitan «(FIFA Timeline pos: …)», «(ESPN/TM)» y similares de eventos y jugadas. Los tipos de evento tienen nombre en español («Poste o travesaño», «Cambio»), y los cambios ya tienen icono.
- **Columna Jugada:** ya no repite el marcador al inicio.
- **Datos no disponibles:** nombres legibles en lugar de claves técnicas y un motivo en lenguaje llano.
- **Uniforme en texto:** desplegable «Uniforme del partido» en cada equipo de la Ficha (camiseta, pantaloneta, medias, y portero o «sin foto verificada»).
- **Diagramas:** se abren en grande en otra pestaña al tocarlos, y se presentan como tarjeta clara sobre el fondo oscuro.
- **Etiqueta superior:** el punto de «CRC vs SKN» usa mitad rojo y mitad verde (uniformes), en el orden del marcador.

Archivos: `dashboard/components/partido.js`, `dashboard/styles/components/match-hub.css`.
