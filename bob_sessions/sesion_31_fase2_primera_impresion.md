# Sesión 31 — Fase 2: Primera impresión

**Fecha:** 2026-11-14  
**Agente:** Gemini (Antigravity, modo agente con navegador)  
**Rama:** `feat-costa-rica`  
**Blueprint:** `blueprints/fase2_primera_impresion.md` (incluye sección 6 de aclaraciones)  
**Plan general:** `evaluaciones/PLAN_MEJORAS_2026-11-14.md` (mejoras B1, B2, B3, B5, B6, A5, C2 y D-a…D-e)

---

## 1. Qué se hizo

Se implementó por completo la Fase 2 del plan de mejoras para cambiar textos de jerga técnica a lenguaje de fútbol para cuerpos técnicos, ajustar la navegación principal, distinguir visualmente el origen de las respuestas del chat, ordenar y filtrar la lista de jugadores en Mateo y alinear etiquetas y esquemas entre páginas, sin tocar `implementacion/` ni hacer commit.

### Tabla de IDs (hecho / no hecho / decisión)

| ID | Estado | Decisión tomada / Detalle |
|---|---|---|
| **B1** | **Hecho** | En `dashboard/pages/index.html`, se cambió el botón primario de «Analizar mi partido» a **«Ver partido de muestra»** y se añadió debajo la nota `.hero__demo-note`: «Demo con un partido real: Costa Rica 4-0 San Cristóbal y Nieves. ¿Quieres ver el tuyo? Escríbenos.» |
| **B2** | **Hecho** | En `dashboard/pages/index.html`, se mantuvo el `<h1>` «¡Que no te lo cuente tu cuñado!» y se reemplazó el subtítulo por: «Análisis táctico de video para cuerpos técnicos: posiciones, bloque y una crónica con IA, en un solo tablero.» |
| **B3** | **Hecho** | En `dashboard/pages/index.html`, se reescribieron los tres bloques numerados (`01 Visión`, `02 Métricas`, `03 Narrador`) con los textos exactos en lenguaje de fútbol propuestos en el blueprint (sin «frame a frame», «Block height», «Savitzky-Golay» ni detalles crudos del modelo). |
| **B5** | **Hecho** | Se quitó «Operaciones» de `LINKS` en `dashboard/components/site-nav.js` y del menú propio `.om-nav__links` de `dashboard/pages/index.html`. Se añadió el enlace discreto «Operaciones técnicas» hacia `operaciones.html` en el pie (`site-credit`) de las 5 páginas (`index.html`, `mateo.html`, `partido.html`, `metodo.html`, `operaciones.html`), y se actualizó el enlace en `dashboard/components/metodo.js` a «Ver las operaciones del sistema →». |
| **B6 / A5** | **Hecho** | En `dashboard/components/chat.js` y `dashboard/styles/components/chat.css`, se añadieron insignias visibles con contraste AA: **«✓ Dato verificado»** (verde `--color-ok`) cuando `r.origen === 'regla'`, **«Lectura del analista»** (neutro `--color-text-soft`) cuando la respuesta empieza por `Lectura táctica del analista`, y **«Lectura de IA · contrástala»** (ámbar `--color-warn`) cuando proviene de Granite. Toda la metadatos técnica (`modelo · ms · tokens · estado`) pasó dentro de un `<details class="msg__trace">` cerrado con `<summary>Ver trazabilidad</summary>`. |
| **C2 (6.1 y 6.2)** | **Hecho** | **6.1:** En `scripts/export_dashboard_data.py` (`cargar_dorsales`), se lee `sin_asignar` de `rastros_dorsales.json` y se marca con `"dudoso": true` y `"motivo_dudoso": <motivo>` a los rastros con cambio de identidad (`"cambio de identidad"` en `motivo`). Se regeneró `dashboard/data/mateo_data.json` con `--no-media`. En `dashboard/pages/mateo.html`, el Top 5 filtra `!p.dudoso`, ordena primero los jugadores identificados (`p.dorsal != null`) y luego por tiempo en pantalla, y etiqueta a los no identificados como «Jugador de <equipo> sin identificar» dejando `Rastro N` en el atributo `title`. **6.2:** Se cambiaron los 4 textos visibles («Top 5 jugadores», aviso explicativo sin la palabra «rastro», «Selecciona un jugador» y `#pc-foot` envuelto en un `<details>` cerrado «Ver detalle del seguimiento»). |
| **Mateo — Reloj (`#mc-frame`)** | **Hecho** | En `dashboard/pages/mateo.html` (HTML inicial y `renderAt()`), se muestra **«Segundo X,Y de 36»** calculado con los `fps` del partido (`(f / FPS).toFixed(1).replace('.', ',')` y `Math.round(DUR)`), conservando `Frame f / (NF - 1)` en el atributo `title`. |
| **Mateo — Ventanas (`W0`…`W7`)** | **Hecho** | En `dashboard/pages/mateo.html`, se reemplazaron las etiquetas visibles `W0`…`W7` por **«Tramo 1»…«Tramo 8»** (función `nombreTramo(w, i)`) en el chip superior, la barra de tramos del reloj maestro, los tooltips de los sparklines y las líneas de la crónica (`[Tramo 1]`), dejando `W0` en `title`. |
| **Mateo — Crónica (Latencia / Tokens)** | **Hecho** | En `dashboard/pages/mateo.html`, los metadatos «Latencia» y «Tokens in/out» de la crónica se movieron dentro de un `<details class="chronicle__details">` cerrado con `<summary>Ver detalle</summary>`. |
| **Mateo — Franja Estado del sistema** | **Hecho** | En `dashboard/pages/mateo.html`, la franja `#obs-strip` muestra en una sola línea visible el enlace **«✓ Análisis verificado (9 de 9 comprobaciones)»** hacia `metodo.html` (calculado dinámicamente según los monitores en PASS), y esconde los chips `Pipeline 9/9 OK`, `ibm/granite-4-h-small` y `M1…M4` dentro de un `<details class="obs-strip__details">` cerrado con `<summary>Ver detalle</summary>`. |
| **D-a** | **Hecho** | En `dashboard/pages/index.html` (bloque `02 Métricas`), se cambió «4 segundos» a **«4,5 segundos»**. Se verificó el resto de páginas y `metodo.json` (donde ya figuraba `4.5 s`). |
| **D-b (6.3)** | **Hecho** | Siguiendo la aclaración 6.3, se cambió únicamente `etiqueta_corta` en `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json` de `"CRC vs SKN · 2026"` a **`"CRC vs SKN · 2024"`** y se regeneró `mateo_data.json` con `--no-media`, de modo que tanto Mateo como Partido muestran `"CRC vs SKN · 2024"` sin tocar Brasil. |
| **D-c (6.4)** | **Hecho** | Siguiendo la aclaración 6.4, tanto Ficha previa (`dashboard/components/partido.js`) como Fichero (`dashboard/components/fichero.js`) muestran `esquema_inicial` (**«3-4-2-1»**), eliminando `esquema_nota.split(' ')[0]` en `fichero.js`, y muestran `esquema_nota` completa tanto en el atributo `title` como en una línea pequeña debajo (`.team-head__note` y `.fichero__esquema-nota`). |
| **D-d** | **Hecho** | En `dashboard/pages/index.html`, se eliminó el enlace roto `<a href="#">Equipo</a>` de `.om-nav__links`. |
| **D-e** | **Hecho** | En `dashboard/pages/mateo.html`, se cambió el subtítulo del panel de «Radar cenital · 120 × 70 m» a **«Radar · cancha de referencia»**. |

---

## 2. Verificación en navegador

### 2.1 `scrollWidth` medido a 375 px (emulación móvil 375×812)

| Página / Vista | `window.innerWidth` | `document.documentElement.scrollWidth` | Desbordamiento horizontal |
|---|---|---|---|
| `pages/index.html` (Inicio) | 375 px | **375 px** (360 px útiles con barra vertical, `scrollWidth <= clientWidth`) | 0 px |
| `pages/mateo.html` (Mateo) | 375 px | **375 px** (`scrollWidth <= clientWidth`) | 0 px |
| `pages/mateo.html` (Chat abierto) | 375 px | **375 px** (`scrollWidth <= clientWidth`) | 0 px |
| `pages/partido.html` (5 pestañas: Ficha previa, Fichero, Comparativa 1T/2T, Los 4 goles, Eventos) | 375 px | **375 px** (`scrollWidth <= clientWidth` en las 5 pestañas) | 0 px |
| `pages/metodo.html` (Método) | 375 px | **375 px** | 0 px |
| `pages/operaciones.html` (Operaciones) | 375 px | **375 px** (`scrollWidth <= clientWidth`) | 0 px |

### 2.2 Prueba de las 3 preguntas del chat

| # | Pregunta | Etiqueta mostrada | Trazabilidad (`<details>`) |
|---|---|---|---|
| 1 | «¿Qué tarjetas hubo?» | `✓ Dato verificado` (verde) | Respuesta directa desde los datos del partido · PASS |
| 2 | «¿Cómo presionó Costa Rica después de perder el balón?» | `Lectura del analista` (neutro) | Respuesta directa desde los datos del partido · PASS |
| 3 | «¿Quién marcó cada gol y en qué minuto?» | `Lectura de IA · contrástala` (ámbar) | `ibm/granite-4-h-small · 3247 ms · tokens 7196/62 · PASS` |

### 2.3 Búsqueda final de jerga en `document.body.innerText`

Con los `<details>` en su estado cerrado por defecto, se evaluó `document.body.innerText` en `pages/index.html` y `pages/mateo.html` buscando (insensible a mayúsculas/minúsculas): `Savitzky`, `Block height`, `Frame`, `W0`, `Pipeline`, `M2.`, `tokens`, `Latencia`, `Rastro`.
- **`pages/index.html`:** 0 coincidencias.
- **`pages/mateo.html`:** 0 coincidencias.
- **Consola JS en las 5 páginas:** 0 errores.

---

## 3. Capturas de pantalla (`evaluaciones/fase2_capturas/`)

### Estado Antes
- `evaluaciones/fase2_capturas/antes_escritorio_inicio.png`
- `evaluaciones/fase2_capturas/antes_escritorio_inicio_bloques.png`
- `evaluaciones/fase2_capturas/antes_escritorio_mateo.png`
- `evaluaciones/fase2_capturas/antes_escritorio_mateo_inferior.png`
- `evaluaciones/fase2_capturas/antes_escritorio_chat.png`
- `evaluaciones/fase2_capturas/antes_movil_inicio.png`
- `evaluaciones/fase2_capturas/antes_movil_partido.png`

### Estado Después
- `evaluaciones/fase2_capturas/despues_escritorio_inicio.png`
- `evaluaciones/fase2_capturas/despues_escritorio_inicio_bloques.png`
- `evaluaciones/fase2_capturas/despues_escritorio_mateo.png`
- `evaluaciones/fase2_capturas/despues_escritorio_mateo_inferior.png`
- `evaluaciones/fase2_capturas/despues_escritorio_partido_ficha.png`
- `evaluaciones/fase2_capturas/despues_escritorio_partido_fichero.png`
- `evaluaciones/fase2_capturas/despues_escritorio_metodo.png`
- `evaluaciones/fase2_capturas/despues_escritorio_operaciones.png`
- `evaluaciones/fase2_capturas/despues_escritorio_chat.png`
- `evaluaciones/fase2_capturas/despues_movil_inicio.png`
- `evaluaciones/fase2_capturas/despues_movil_mateo.png`
- `evaluaciones/fase2_capturas/despues_movil_chat.png`
- `evaluaciones/fase2_capturas/despues_movil_partido.png`

---

## 4. Archivos modificados (sin commit)

- `dashboard/pages/index.html`
- `dashboard/pages/mateo.html`
- `dashboard/pages/partido.html`
- `dashboard/pages/metodo.html`
- `dashboard/pages/operaciones.html`
- `dashboard/components/site-nav.js`
- `dashboard/components/chat.js`
- `dashboard/components/partido.js`
- `dashboard/components/fichero.js`
- `dashboard/components/metodo.js`
- `dashboard/styles/components/chat.css`
- `dashboard/styles/components/fichero.css`
- `dashboard/styles/components/match-hub.css`
- `dashboard/styles/components/site-credit.css`
- `scripts/export_dashboard_data.py` (6.1: lectura de `sin_asignar` para marcar `"dudoso": true`)
- `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json` (6.3: `etiqueta_corta` a `"CRC vs SKN · 2024"`)
- `dashboard/data/mateo_data.json` (regenerado con `export_dashboard_data.py --no-media`)
