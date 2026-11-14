# Encargo — Fase 2: primera impresión

- **Implementa:** Gemini (Antigravity, modo agente **con navegador**)
- **Diseña y revisa:** Claude Code
- **Rama:** `feat-costa-rica` (base: `e122eea`)
- **Plan general:** `evaluaciones/PLAN_MEJORAS_2026-11-14.md` (mejoras B1, B2, B3, B5, B6, A5, C2 y D-a…D-e)
- **Estado:** listo para empezar

---

## 1. Por qué

Las tres evaluaciones coinciden: **el contenido está al nivel de un club, pero la presentación todavía parece de laboratorio.** Un jefe de análisis que ve la app por primera vez se encuentra con tres cosas:
- un botón que promete algo que no hace;
- jerga de ingeniería («Savitzky-Golay», «Frame», «W0», «M2.x», «tokens»);
- una página técnica (Operaciones) en el menú principal.

Esta fase **solo cambia textos, menú y presentación** del tablero web. No cambia datos ni lógica del chat.

**Regla general para todos los textos:** escribe como le hablarías a un entrenador. Usa lenguaje de fútbol y no uses palabras de programación, estadística ni nombres de monitores. Lo técnico no se borra: se mueve a Método u Operaciones, o se esconde detrás de un «Ver detalle».

---

## 2. Qué hay que hacer

Todo dentro de `dashboard/`.

### B1 — El botón principal no puede prometer lo que no hace
- **Dónde:** `pages/index.html`, el botón «Analizar mi partido» (línea ~161).
- **Qué hacer:**
  - Cambia el texto a **«Ver partido de muestra»**.
  - Debajo de los botones, añade una línea pequeña: «Demo con un partido real: Costa Rica 4-0 San Cristóbal y Nieves. ¿Quieres ver el tuyo? Escríbenos.» No hace falta un enlace real; basta el texto.

### B2 — Titular
- **Dónde:** `pages/index.html`, `<h1>` (línea ~150).
- **Qué hacer:** se **mantiene** «¡Que no te lo cuente tu cuñado!». Cambia el subtítulo para que dé seriedad:
  > «Análisis táctico de video para cuerpos técnicos: posiciones, bloque y una crónica con IA, en un solo tablero.»
- Si el usuario decide otra cosa (decisión D1 del plan), se cambia después. No inventes otro titular.

### B3 — Inicio sin jerga
- **Dónde:** `pages/index.html`, los tres bloques numerados (líneas ~185–215).
- **Qué hacer:** reescribe las tres descripciones en lenguaje de fútbol, conservando lo que dicen:

| Bloque | Ahora | Propuesta |
|---|---|---|
| 01 Visión | «Detección de jugadores y balón frame a frame. Tracking con costura de identidad y mapeo a coordenadas reales de cancha (120 × 70 m).» | «Reconoce a cada jugador y al balón en la transmisión de TV, los sigue durante la jugada y los coloca en un mapa de la cancha.» |
| 02 Métricas | «Block height, velocidad de transición, compacidad y centroides. Suavizado Savitzky-Golay. Ventanas tácticas de 4 segundos.» | «Altura del bloque, compacidad, velocidad de transición y posición media de cada equipo, en tramos de 4,5 segundos.» |
| 03 Narrador | «Crónica táctica generada por ibm/granite-4-h-small vía watsonx.ai. Texto sintetizado a voz…» | «Una crónica táctica escrita por IA (IBM Granite en watsonx.ai) y narrada en voz, sincronizada con el video.» |

### B5 — Operaciones fuera del menú principal
- **Dónde:** `components/site-nav.js`, la lista `LINKS`.
- **Qué hacer:**
  - Quita «Operaciones» del menú principal.
  - Ponle un enlace discreto al pie de **todas** las páginas («Operaciones técnicas»), junto al crédito `site-credit`, y otro dentro de `pages/metodo.html` («Ver las operaciones del sistema»).
  - La página `operaciones.html` sigue existiendo y funcionando.
- Revisa también el menú propio de `pages/index.html` (`om-nav`, línea ~118): el enlace **«Equipo» va a `#`**. Quítalo (D-d).

### B6 y A5 — El chat distingue un dato verificado de una lectura de IA
- **Dónde:** `components/chat.js`, línea ~139, donde se arma `msg__meta`.
- **Hoy:** las respuestas por regla dicen «Respuesta directa desde los datos, sin LLM», y las de Granite muestran «modelo · ms · tokens N/M · PASS».
- **Qué hacer:**
  - **Si `r.origen === 'regla'`:** pon una etiqueta visible **«✓ Dato verificado»**, en verde (usa los tokens de color que ya existen).
  - **Si viene de Granite:** pon la etiqueta **«Lectura de IA · contrástala»**, en ámbar, sea cual sea el estado.
  - **Si la respuesta empieza por «Lectura táctica del analista»:** aunque sea por regla, usa **«Lectura del analista»**, en un color neutro.
  - **Lo técnico** (modelo, ms, tokens, estado PASS/REVISAR/BLOQUEADA) va a un `<details>` cerrado con el texto «Ver trazabilidad». No se borra.
  - Las etiquetas deben leerse bien en el móvil y tener suficiente contraste (AA).

### C2 — Lista de jugadores de Mateo sin números internos
- **Dónde:** `pages/mateo.html`, alrededor de las líneas 860–900 (la función que arma la etiqueta `'Rastro ' + p.id`).
- **Qué hacer:**
  - Ordena primero a los jugadores **identificados** (con dorsal).
  - A los no identificados, muéstralos como «Jugador de <equipo> sin identificar». Así el usuario no ve «Rastro 25».
  - Los rastros con cambio de identidad (los que el propio archivo marca como dudosos) no salen en el top.
  - El número de rastro solo aparece en el detalle o en un `title` para quien lo busque.

### Mateo — etiquetas en lenguaje de fútbol
- **Dónde:** `pages/mateo.html`.

| Dónde (línea aprox.) | Ahora | Propuesta |
|---|---|---|
| 239 y 710 | «Frame 386 / 1799» | «Segundo 15,4 de 72» (calcúlalo con los fps del partido). El número de frame queda en un `title` |
| 343 y JS | «W0», «W3» | «Tramo 1», «Tramo 4» |
| 295 | «Radar cenital · 120 × 70 m» | «Radar · cancha de referencia» (D-e) |
| 406–407 | «Latencia», «Tokens in/out» de la crónica | Dentro de un «Ver detalle» cerrado |
| 455–581 | Franja «Estado del sistema · Pipeline 9/9 OK · M1 … M4» | Una sola línea «✓ Análisis verificado (9 de 9 comprobaciones)» que enlaza a Método. Los chips M1…M4 quedan dentro de un «Ver detalle» |

> **No toques el video «Con marcas»:** el texto quemado (`Frame … [POST-MATH]`, `Moda M2.0`) solo se quita volviendo a renderizar el video, y eso es de la fase 4.

### D — Coherencia entre páginas
| ID | Qué | Dónde buscar |
|---|---|---|
| D-a | «4 segundos» → **«4,5 segundos»** en cualquier texto visible del tablero | `pages/*.html` (incluye `metodo.html` y lo que salga de `data/metodo.json` si se muestra) |
| D-b | Mateo dice «CRC vs SKN · 2026» y Partido «· 2024». Debe decir **«2024 · Eliminatorias 2026»** en los dos | Busca de dónde sale la etiqueta (`etiqueta_corta` del partido, `mateo.html` o `partido.js`). Si sale de `data/partidos/*/partido.config.json`, cambia solo esa clave y dilo en tu informe |
| D-c | Ficha previa dice 3-4-2-1 y Fichero dice «Costa Rica · 3-4-3». Muestra **lo mismo en las dos**: «3-4-3 / 3-4-2-1», con la nota de fuentes (`esquema_nota`) en un `title` o en una línea pequeña | `components/fichero.js:205`, `components/partido.js:375` |
| D-d | Enlace «Equipo» → `#` | Ver B5 |
| D-e | «120 × 70 m» | Ver la tabla de Mateo |

---

## 3. Lo que no hay que tocar

- `implementacion/`: el chat y el pipeline son de Bob. Si Bob está corrigiendo R8–R11, trabaja en paralelo en esos archivos.
- Los datos de Fer, `data/partidos/*/partido/*.json` y `*.md`. La única excepción es la clave de la etiqueta de D-b, y solo si la etiqueta sale de ahí.
- Los videos (`assets/`) y el diseño general: colores, tipografía y rejilla. Esta fase cambia palabras y la ubicación de lo técnico, no el estilo.
- La página de Brasil: si cambias un texto que también se ve con Brasil, debe seguir siendo correcto para Brasil. No escribas «Costa Rica» a mano donde hoy sale de los datos.
- **No hagas commit.** Claude revisa y el usuario aprueba.

---

## 4. Cómo comprobarlo (obligatorio, en el navegador)

1. Levanta el servidor: `.\.venv\Scripts\python.exe dashboard\serve.py --port 8600` (o el que esté libre) y abre `http://localhost:8600/pages/index.html`.
2. **Escritorio (1280 px):** recorre Inicio, Mateo, Partido (las 5 pestañas), Método y Operaciones (desde el pie de página). Haz una captura de cada página.
3. **Móvil:** usa la **emulación de dispositivo** de las herramientas de desarrollo a 375×812, no solo estrechando la ventana. Repite Inicio, Mateo, Partido y el chat.
   - En cada página, `document.documentElement.scrollWidth` debe ser **375**: que no haya desplazamiento horizontal de la página.
   - En la evaluación anterior, a Gemini le salió 845 px por estrechar la ventana sin emular el dispositivo. Usa la emulación.
4. **Chat:** haz solo estas 3 preguntas, para gastar poco:
   - «¿Qué tarjetas hubo?» → «✓ Dato verificado».
   - «¿Cómo presionó Costa Rica después de perder el balón?» → «Lectura del analista».
   - «¿Quién marcó cada gol y en qué minuto?» → «Lectura de IA · contrástala», y «Ver trazabilidad» muestra el modelo y los tokens.
5. **Consola:** que no haya errores nuevos de JavaScript en ninguna página.
6. **Búsqueda final de jerga:** en lo que se ve en Inicio y Mateo (no en Método ni en Operaciones), no debe quedar «Savitzky», «Block height», «Frame», «W0», «Pipeline», «M2.», «tokens», «Latencia» ni «Rastro». Haz la búsqueda con `document.body.innerText` en el navegador, para mirar solo el texto visible y no el código.

---

## 5. Qué entregar

1. Los cambios en `dashboard/`, **sin commit**.
2. Capturas de pantalla, antes y después, de Inicio, Mateo y el chat en escritorio, y de Inicio y Partido en el móvil. Guárdalas en `evaluaciones/fase2_capturas/`.
3. Una tabla con cada ID (B1, B2, B3, B5, B6/A5, C2, la tabla de Mateo y D-a…D-e): **hecho / no hecho / decisión que tomé**.
4. El `scrollWidth` medido a 375 px en cada página.
5. `bob_sessions/sesion_31_fase2_primera_impresion.md` y su fila en `bob_sessions/README.md`.

Si algo del encargo no cuadra con el código, **para y pregunta**; no improvises.

---

## 6. Aclaraciones (respuestas de Claude a las preguntas de Gemini)

### 6.1 C2: cómo marcar los rastros dudosos → opción (a), desde el exportador
- En `scripts/export_dashboard_data.py`, donde se arma la lista de jugadores de Mateo (líneas ~162 y ~331), lee también `sin_asignar` de `rastros_dorsales.json`. A cada jugador cuyo `id` aparezca allí, añádele `"dudoso": true` y `"motivo_dudoso": <motivo>`. No escribas a mano el número 29.
- En `mateo.html`, los jugadores con `dudoso` no entran en el top. Sí pueden verse en la lista completa, si existe, con su motivo.
- **No edites `mateo_data.json` a mano.** Regenéralo con `.\.venv\Scripts\python.exe scripts\export_dashboard_data.py --no-media`.
- Luego revisa `git diff --stat dashboard/data`. Solo deben cambiar `mateo_data.json` (el campo nuevo y la etiqueta de 6.3) y, si acaso, `partido.json`. Si cambia algo más, para y dime qué.
- Esta es la única excepción a «solo `dashboard/`». `scripts/export_dashboard_data.py` no lo está tocando Bob.

### 6.2 «Rastro» fuera del texto visible → sí, cambia esos 4 textos
| Dónde | Ahora | Nuevo |
|---|---|---|
| l. 421 | «Top 5 rastros» | «Top 5 jugadores» |
| l. 427 | «Un rastro es un seguimiento automático…» | «Cada jugador se sigue automáticamente en el video. A veces una misma persona aparece dos veces o el seguimiento cambia de jugador; por eso algunos salen sin identificar.» |
| l. 435 | «Selecciona un rastro» | «Selecciona un jugador» |
| l. 895 `#pc-foot` | «Rastro 6 · dorsal leído a mano…» / «Rastros 2 y 74 unidos…» | Dentro de un `<details>` cerrado «Ver detalle del seguimiento». El texto de dentro puede seguir diciendo «Rastro N»: los `<details>` cerrados no cuentan en la comprobación 4.6 |

### 6.3 D-b: la etiqueta → la más simple, «CRC vs SKN · 2024» en las dos páginas
- Cambia **solo** `etiqueta_corta` en `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json` de `"CRC vs SKN · 2026"` a **`"CRC vs SKN · 2024"`**.
- Así coincide con lo que Partido ya calcula a partir de la fecha. No hace falta cambiar `partido.js` ni añadir campos.
- «Eliminatorias 2026» ya aparece en el encabezado de Partido. Esto **sustituye** lo que pedía D-b en la sección 2.
- No toques la configuración de Brasil.

### 6.4 D-c: el esquema → no analices `esquema_nota`
- En Ficha y en Fichero, muestra **`esquema_inicial`** («3-4-2-1») y pon `esquema_nota` completa en un `title` y en una línea pequeña debajo («3-4-3 según FIFA y ESPN; 3-4-2-1 según FotMob…»).
- En `fichero.js:205`, deja de usar `esquema_nota.split(' ')[0]`.
- No toques `contexto_partido.json`. Esto **sustituye** lo que pedía D-c en la sección 2.
