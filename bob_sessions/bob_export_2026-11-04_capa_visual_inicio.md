# # ROL
Eres un ingeniero front-end y diseñador de producto senior. Vas a construir la
capa visual de OMNIMORPH y de su tablero MATEO (Motor de Análisis Táctico y
Estadístico) con calidad de producto profesional, escalable y mantenible.

# FUENTE DE VERDAD
1. Mockup aprobado: https://claude.ai/artifact/AhGQ9UKLbcdsbFmoxTc6S7
   Pantallas válidas:
   - "Inicio · estilo galería" (portada)
   - "Tablero MATEO"
   - "Carga / respaldo"
   IGNORA la pantalla "Inicio OMNIMORPH" (portada anterior con botones
   morados): está descartada.
   Reprodúcelas fielmente: layout, jerarquía, espaciados y componentes.
2. `DESIGN.md`: único sistema de estilo. Lo creas tú en el paso 2.
3. Herramientas de diseño disponibles: [HERRAMIENTA 1] y [HERRAMIENTA 2].
   Úsalas para layout, componentes y accesibilidad, NUNCA para elegir
   paletas, tipografías o estilos de su propio catálogo. Si algo falta,
   derívalo de DESIGN.md y dime qué derivaste.
4. Inspiración de estilo: sistema "galería monocromática" (interfaz casi
   invisible, el color lo ponen el video, el logo y los datos). Adopta la
   manera de organizar la pantalla, no ningún activo de otra marca.

# PASO 0: RECONOCIMIENTO (antes de escribir código)
- Inspecciona el repositorio [RUTA/REPO]. Identifica el framework actual y
  cómo se alimenta de datos (video, JSON de métricas, audio .wav, transcripción).
- NO cambies el framework ni la lógica del pipeline: tu alcance es la capa visual.
- Resume en 10 líneas lo que encontraste y tu plan, y espera mi OK.

# PASO 1: ESTRUCTURA DE CARPETAS (escalable)
```
dashboard/
├── DESIGN.md
├── styles/
│   ├── tokens.css              # variables: colores, tipografía, espaciado, radios
│   ├── base.css                # reset, tipografía global, fondo
│   ├── layout.css              # rejilla con líneas finas, barra lateral, breakpoints
│   ├── components/
│   │   ├── nav.css · pill-button.css · status-chips.css · master-clock.css
│   │   ├── video-panel.css · radar.css · kpi-card.css · chronicle.css
│   │   ├── transcript.css · player-sidebar.css · hero.css · tiles.css
│   │   ├── loader.css · powered-by.css · footer-legend.css
│   └── themes/                 # variantes futuras (claro, alto contraste)
├── components/                 # un componente por panel, sin lógica de negocio
├── pages/                      # inicio (portada), tablero, carga/error
├── assets/
│   ├── fonts/                  # Jost, Inter y JetBrains Mono, locales
│   ├── icons/                  # SVG de línea, trazo 1.5 px
│   ├── hero/                   # video de fondo (mp4/webm), audio opcional, poster
│   │   ├── hero.mp4 · hero.webm
│   │   ├── hero-ambient.mp3    # pista de audio aparte, opcional
│   │   └── hero-poster.png     # imagen del estadio (la del mockup)
│   └── logos/                  # CARPETA PARA TODOS LOS LOGOS
│       ├── omnimorph/          # logo principal y variantes (SVG o PNG transparente)
│       ├── ibm/                # logos de IBM y de sus herramientas
│       ├── programa/           # logo del programa o institución
│       ├── README.md           # fuente, licencia y reglas de uso de cada logo
│       └── logos.manifest.json # id, archivo, alt, ancho máx., variante clara/oscura
├── visuals/                    # figuras del tablero
│   ├── radar/ · heatmap/ · charts/
│   └── theme.*                 # aplica los tokens a las figuras
├── config/
│   └── ui.config               # equipos, colores por equipo, métrica activa,
│                               # textos de la leyenda (creadores/programa/licencia)
└── docs/
    └── STYLE_GUIDE.md          # cómo agregar un componente, métrica o logo
```
Reglas de arquitectura:
- Cero colores o tamaños escritos a mano en componentes: todo sale de tokens.
- Colores de equipos y textos de la leyenda vienen de `config/ui.config`.
- Cada panel recibe datos ya procesados; no consulta el pipeline directamente.
- Agregar una métrica o un logo debe requerir tocar solo config/manifest y
  quedar documentado en STYLE_GUIDE.md.

# PASO 2: DESIGN.md (valores concretos)
Principios: galería oscura, interfaz casi invisible, datos y video como
protagonistas, sin color de marca en la interfaz, números en monoespaciada.

Colores:
- fondo #111111 · fondo profundo #0A0A0A · borde #2A2A2A (1 px) · borde
  suave #3A3A3A
- texto #FFFFFF · texto-suave #A1A1AE (nunca más oscuro sobre negro)
- equipo A (BRA) #F5A623 · equipo B (GER) #F5F3EE · balón #A3E635
- cancha #0E1A16 con líneas #2A4A3E
- estado OK #1FC8B0 (solo el punto del chip) · alerta #F24E6B
- tarjeta del logo: crema #F5F3EE
- NO hay color de acento de marca en la interfaz. El color viene del logo,
  del video/estadio y de los datos de equipos.
Tema claro (solo pantalla de carga/error): fondo #FFFFFF, texto #111111,
texto-suave #4B5563, borde #E5E7EB.

Tipografía:
- Titulares: Jost 500 (hero 76 px en mayúsculas, interlineado 1.0; títulos
  de tarjeta 24 px; cifras KPI 44 px).
- Interfaz: Inter 400/500 (cuerpo 14–16 px, etiquetas 12 px).
- Números y tiempos: JetBrains Mono 500.
- Pesos únicamente 400 y 500; nunca negritas.

Forma y espaciado:
- Escala de 4 px (4·8·12·16·20·24·36·48); padding de celda 20×24; sección 48.
- Botones, chips y etiquetas: píldora (radio 30 px). Tarjetas, celdas, video
  y logos: radio 0.
- Rejilla con líneas de 1 px (#2A2A2A) en lugar de tarjetas con relleno.
- Sin sombras ni degradados decorativos (única excepción: la capa oscura
  sobre el video de la portada).

Botones: UN solo estilo principal: píldora blanca (#FFFFFF) con texto
#111111, altura mínima 44 px. Secundarios solo como píldora con contorno
(p. ej. "Activar sonido"). El texto de un botón nunca usa un color de marca.

Movimiento: 150 ms ease-out; solo se animan el fondo de la portada, el
indicador de carga y "en vivo". Respeta `prefers-reduced-motion` (todo se
detiene; el video se sustituye por el poster).

Accesibilidad: contraste 4.5:1; objetivos táctiles ≥ 44 px; botones reales
con aria-label si solo llevan icono; alt descriptivo en cada logo; equipos
distinguibles también por luminosidad, no solo por tono.

NO USAR: emojis como iconos, color de marca en la interfaz, sombras de más
de 8 px, azul contra rojo para equipos, negritas, esquinas redondeadas en
tarjetas, verde brillante en la cancha, parpadeos o rebotes.

# PASO 3: PANTALLAS Y COMPONENTES

A) PORTADA (fondo #111111, a pantalla completa)
- Navegación transparente: wordmark OMNIMORPH (Jost 500, tracking .2em),
  enlaces (Inicio, MATEO, Arquitectura, Equipo) y "Abrir tablero" como
  enlace más.
- Titular: "¡QUE NO TE LO CUENTE TU CUÑADO!" (Jost 500, 76 px, mayúsculas,
  blanco, abajo a la izquierda). Subtítulo: "Ve lo que el ojo no ve:
  posiciones, métricas tácticas y una crónica narrada por IA, todo en un solo
  tablero." Botón principal: píldora blanca "Analizar mi partido".
- Debajo del botón: indicador "Preparando el análisis…" (tres puntos blancos
  pulsando) y el botón con contorno "Activar sonido".
- A la derecha, el logo OMNIMORPH (cubo de Rubik) en tarjeta crema de bordes
  rectos. Si hay versión SVG o PNG transparente, úsala directo sobre negro.
- FONDO (de abajo hacia arriba):
  1. Cancha animada con puntos flotando (BRA naranja, GER crema, balón
     lima): respaldo final.
  2. Poster: imagen aérea del estadio (`hero-poster.png`).
  3. Video en bucle, `muted`, `playsinline`, `loop`, sin controles.
  4. Capa oscura (más fuerte a la izquierda) para que el texto se lea.
- Comportamiento del video y el audio:
  - Arranca SIN sonido (los navegadores bloquean el autoplay con audio).
  - "Activar sonido" enciende el audio con fundido de entrada (~500 ms) y su
    texto cambia a "Silenciar"; recuerda la elección durante la sesión.
  - El audio: ambiente de estadio, sin voz, volumen inicial ≤ 30 %.
  - Si el video falla o tarda, se queda el poster; el indicador "Preparando…"
    desaparece cuando el video empieza a reproducirse.
  - Con `prefers-reduced-motion` o conexión lenta: solo el poster.
  - Si el audio es pesado, va como archivo aparte y se carga solo al activar
    el sonido.
  - Requisitos del video: 10–20 s, ≤ 10 MB, 1080p o menos, MP4 y WebM.
- Tres bloques numerados a sangre con líneas finas (01 Visión, 02 Métricas,
  03 Narrador): título 24 px y texto de 14 px en #A1A1AE.
- Franja "Impulsado por herramientas de IBM": logos tomados de
  `assets/logos/ibm/` mediante el manifest, versión oficial sin modificar y
  con espacio libre alrededor; respeta las reglas de uso de marca de IBM y
  documéntalo en logos/README.md. Mientras falten, recuadros punteados
  [Logo IBM] / [Logo herramienta].
- Leyenda al pie: Creadores, Programa, Licencia (textos desde config), más
  "OMNIMORPH" y "MATEO · Motor de análisis táctico y estadístico".

B) TABLERO MATEO (fondo #111111, rejilla con líneas de 1 px)
1. Cabecera: logo + MATEO + subtítulo; chip "BRA vs GER · 2014"; chip
   "Pipeline 9/9 OK" que pasa a ámbar/rojo si falla un módulo.
2. Tira de observabilidad: chips M1, M2.0–M2.5, M3, M4 con estado real
   (punto turquesa si está OK).
3. Reloj maestro: línea de tiempo blanca con ventanas W0…Wn, tiempo y frame
   (p. ej. 00:00.0 / duración · Frame 0 / 1799); sincroniza todos los paneles.
4. Panel de video doble: POST-MATEO (con las marcas de los modelos) como
   principal con chip "en vivo"; debajo, la transmisión original en miniatura
   sincronizada y la píldora blanca "Intercambiar".
5. Radar cenital 120 × 70 m, mismo alto que el video, cancha centrada.
6. KPIs (Block height, velocidad de transición): cifra en Jost 44 px, barra
   BRA/GER de 4 px, badge "BRA domina" en píldora naranja. Valores de GER
   vacíos ([—]) hasta tener datos.
7. Crónica IA: texto en serif, reproductor con forma de onda, pie con
   latencia y tokens.
8. Transcripción al español: líneas con marca de tiempo; ventana actual en
   blanco, siguiente atenuada con cursor; se completa conforme suena el audio.
9. Barra lateral de jugadores (derecha, 320 px): selector BRA/GER (píldoras),
   lista de 5 jugadores con UNA métrica activa y selector de métrica; ficha del
   jugador con mapa de calor y 3 cifras. Una idea por bloque.
   Crea un adaptador (un solo archivo) que mapee el formato que entregue mi
   equipo de análisis (CSV/JSON) a lo que consumen los componentes.
10. Leyenda al pie (Creadores, Programa, Licencia).

C) PANTALLA DE CARGA / RESPALDO (fondo blanco)
- Cubo de Rubik pequeño en SVG (naranja arriba, turquesa izquierda, morado
  derecha, con el cuadro rosa y el lima; la capa superior se levanta en
  bucle), "OMNIMORPH" en Jost 500, "Preparando el análisis…" con tres puntos
  pulsando.
- Bloque de respaldo: "¿Está tardando demasiado?…" y píldora negra "Reintentar".
- IMPORTANTE: debe ser autosuficiente (SVG y CSS incrustados en el HTML, sin
  archivos externos) para aparecer incluso si todo lo demás falla. Sirve como
  pantalla de carga inicial y como pantalla de error.

# PASO 4: LOGOS
- Todos los logos que yo suba van en `assets/logos/`, en su subcarpeta. Prefiere
  SVG; si es PNG, con fondo transparente.
- Los componentes NUNCA escriben rutas de logos a mano: leen
  `logos.manifest.json` (id, archivo, alt, ancho máximo, variante).
- Mientras falte un logo, muestra un recuadro punteado con su nombre entre
  corchetes y avísame cuáles faltan.
- Crea `assets/logos/README.md` con la fuente de cada logo, su licencia y las
  reglas de uso (espacio libre, colores permitidos, tamaño mínimo).

# PASO 5: RESPONSIVO Y CALIDAD
- Sin anchos fijos en px: rejilla fluida; la barra lateral baja debajo del
  contenido en pantallas angostas; franjas y leyenda se apilan.
- Fuentes locales; todo debe funcionar sin internet en la laptop.
- Sin CSS duplicado; sin `!important` salvo justificación; clases con
  convención consistente (BEM).

# PASO 6: VERIFICACIÓN (al terminar)
- Compara cada pantalla con el mockup y con DESIGN.md; dime en qué te saliste
  y corrígelo.
- Lista los valores derivados que no estaban en DESIGN.md.
- Verifica contraste, que no haya colores escritos a mano fuera de tokens y
  que ningún botón use color de marca.
- Prueba: portada con el video ausente, con el audio bloqueado y con
  movimiento reducido; pantalla de carga con la red cortada.
- Entrega: resumen de archivos creados/modificados, cómo correr el proyecto,
  lista de logos y archivos de video/audio pendientes, y una captura de cada
  pantalla.

# RESTRICCIONES
- No inventes datos ni textos legales: donde falte algo (creadores, programa,
  licencia, valores de GER) deja el marcador visible entre corchetes.
- No cambies el pipeline de visión, el LLM ni la síntesis de voz.
- Si hay una decisión de arquitectura que no está aquí, pregúntame antes de
  avanzar. nota parte del dashboard que tenemos y deja las capteas para agregar los logos y el video

---

**Status:** active  **Date:** 2026-11-04

---

### 👤 User

# ROL
Eres un ingeniero front-end y diseñador de producto senior. Vas a construir la
capa visual de OMNIMORPH y de su tablero MATEO (Motor de Análisis Táctico y
Estadístico) con calidad de producto profesional, escalable y mantenible.

# FUENTE DE VERDAD
1. Mockup aprobado: https://claude.ai/artifact/AhGQ9UKLbcdsbFmoxTc6S7
   Pantallas válidas:
   - "Inicio · estilo galería" (portada)
   - "Tablero MATEO"
   - "Carga / respaldo"
   IGNORA la pantalla "Inicio OMNIMORPH" (portada anterior con botones
   morados): está descartada.
   Reprodúcelas fielmente: layout, jerarquía, espaciados y componentes.
2. `DESIGN.md`: único sistema de estilo. Lo creas tú en el paso 2.
3. Herramientas de diseño disponibles: [HERRAMIENTA 1] y [HERRAMIENTA 2].
   Úsalas para layout, componentes y accesibilidad, NUNCA para elegir
   paletas, tipografías o estilos de su propio catálogo. Si algo falta,
   derívalo de DESIGN.md y dime qué derivaste.
4. Inspiración de estilo: sistema "galería monocromática" (interfaz casi
   invisible, el color lo ponen el video, el logo y los datos). Adopta la
   manera de organizar la pantalla, no ningún activo de otra marca.

# PASO 0: RECONOCIMIENTO (antes de escribir código)
- Inspecciona el repositorio [RUTA/REPO]. Identifica el framework actual y
  cómo se alimenta de datos (video, JSON de métricas, audio .wav, transcripción).
- NO cambies el framework ni la lógica del pipeline: tu alcance es la capa visual.
- Resume en 10 líneas lo que encontraste y tu plan, y espera mi OK.

# PASO 1: ESTRUCTURA DE CARPETAS (escalable)
```
dashboard/
├── DESIGN.md
├── styles/
│   ├── tokens.css              # variables: colores, tipografía, espaciado, radios
│   ├── base.css                # reset, tipografía global, fondo
│   ├── layout.css              # rejilla con líneas finas, barra lateral, breakpoints
│   ├── components/
│   │   ├── nav.css · pill-button.css · status-chips.css · master-clock.css
│   │   ├── video-panel.css · radar.css · kpi-card.css · chronicle.css
│   │   ├── transcript.css · player-sidebar.css · hero.css · tiles.css
│   │   ├── loader.css · powered-by.css · footer-legend.css
│   └── themes/                 # variantes futuras (claro, alto contraste)
├── components/                 # un componente por panel, sin lógica de negocio
├── pages/                      # inicio (portada), tablero, carga/error
├── assets/
│   ├── fonts/                  # Jost, Inter y JetBrains Mono, locales
│   ├── icons/                  # SVG de línea, trazo 1.5 px
│   ├── hero/                   # video de fondo (mp4/webm), audio opcional, poster
│   │   ├── hero.mp4 · hero.webm
│   │   ├── hero-ambient.mp3    # pista de audio aparte, opcional
│   │   └── hero-poster.png     # imagen del estadio (la del mockup)
│   └── logos/                  # CARPETA PARA TODOS LOS LOGOS
│       ├── omnimorph/          # logo principal y variantes (SVG o PNG transparente)
│       ├── ibm/                # logos de IBM y de sus herramientas
│       ├── programa/           # logo del programa o institución
│       ├── README.md           # fuente, licencia y reglas de uso de cada logo
│       └── logos.manifest.json # id, archivo, alt, ancho máx., variante clara/oscura
├── visuals/                    # figuras del tablero
│   ├── radar/ · heatmap/ · charts/
│   └── theme.*                 # aplica los tokens a las figuras
├── config/
│   └── ui.config               # equipos, colores por equipo, métrica activa,
│                               # textos de la leyenda (creadores/programa/licencia)
└── docs/
    └── STYLE_GUIDE.md          # cómo agregar un componente, métrica o logo
```
Reglas de arquitectura:
- Cero colores o tamaños escritos a mano en componentes: todo sale de tokens.
- Colores de equipos y textos de la leyenda vienen de `config/ui.config`.
- Cada panel recibe datos ya procesados; no consulta el pipeline directamente.
- Agregar una métrica o un logo debe requerir tocar solo config/manifest y
  quedar documentado en STYLE_GUIDE.md.

# PASO 2: DESIGN.md (valores concretos)
Principios: galería oscura, interfaz casi invisible, datos y video como
protagonistas, sin color de marca en la interfaz, números en monoespaciada.

Colores:
- fondo #111111 · fondo profundo #0A0A0A · borde #2A2A2A (1 px) · borde
  suave #3A3A3A
- texto #FFFFFF · texto-suave #A1A1AE (nunca más oscuro sobre negro)
- equipo A (BRA) #F5A623 · equipo B (GER) #F5F3EE · balón #A3E635
- cancha #0E1A16 con líneas #2A4A3E
- estado OK #1FC8B0 (solo el punto del chip) · alerta #F24E6B
- tarjeta del logo: crema #F5F3EE
- NO hay color de acento de marca en la interfaz. El color viene del logo,
  del video/estadio y de los datos de equipos.
Tema claro (solo pantalla de carga/error): fondo #FFFFFF, texto #111111,
texto-suave #4B5563, borde #E5E7EB.

Tipografía:
- Titulares: Jost 500 (hero 76 px en mayúsculas, interlineado 1.0; títulos
  de tarjeta 24 px; cifras KPI 44 px).
- Interfaz: Inter 400/500 (cuerpo 14–16 px, etiquetas 12 px).
- Números y tiempos: JetBrains Mono 500.
- Pesos únicamente 400 y 500; nunca negritas.

Forma y espaciado:
- Escala de 4 px (4·8·12·16·20·24·36·48); padding de celda 20×24; sección 48.
- Botones, chips y etiquetas: píldora (radio 30 px). Tarjetas, celdas, video
  y logos: radio 0.
- Rejilla con líneas de 1 px (#2A2A2A) en lugar de tarjetas con relleno.
- Sin sombras ni degradados decorativos (única excepción: la capa oscura
  sobre el video de la portada).

Botones: UN solo estilo principal: píldora blanca (#FFFFFF) con texto
#111111, altura mínima 44 px. Secundarios solo como píldora con contorno
(p. ej. "Activar sonido"). El texto de un botón nunca usa un color de marca.

Movimiento: 150 ms ease-out; solo se animan el fondo de la portada, el
indicador de carga y "en vivo". Respeta `prefers-reduced-motion` (todo se
detiene; el video se sustituye por el poster).

Accesibilidad: contraste 4.5:1; objetivos táctiles ≥ 44 px; botones reales
con aria-label si solo llevan icono; alt descriptivo en cada logo; equipos
distinguibles también por luminosidad, no solo por tono.

NO USAR: emojis como iconos, color de marca en la interfaz, sombras de más
de 8 px, azul contra rojo para equipos, negritas, esquinas redondeadas en
tarjetas, verde brillante en la cancha, parpadeos o rebotes.

# PASO 3: PANTALLAS Y COMPONENTES

A) PORTADA (fondo #111111, a pantalla completa)
- Navegación transparente: wordmark OMNIMORPH (Jost 500, tracking .2em),
  enlaces (Inicio, MATEO, Arquitectura, Equipo) y "Abrir tablero" como
  enlace más.
- Titular: "¡QUE NO TE LO CUENTE TU CUÑADO!" (Jost 500, 76 px, mayúsculas,
  blanco, abajo a la izquierda). Subtítulo: "Ve lo que el ojo no ve:
  posiciones, métricas tácticas y una crónica narrada por IA, todo en un solo
  tablero." Botón principal: píldora blanca "Analizar mi partido".
- Debajo del botón: indicador "Preparando el análisis…" (tres puntos blancos
  pulsando) y el botón con contorno "Activar sonido".
- A la derecha, el logo OMNIMORPH (cubo de Rubik) en tarjeta crema de bordes
  rectos. Si hay versión SVG o PNG transparente, úsala directo sobre negro.
- FONDO (de abajo hacia arriba):
  1. Cancha animada con puntos flotando (BRA naranja, GER crema, balón
     lima): respaldo final.
  2. Poster: imagen aérea del estadio (`hero-poster.png`).
  3. Video en bucle, `muted`, `playsinline`, `loop`, sin controles.
  4. Capa oscura (más fuerte a la izquierda) para que el texto se lea.
- Comportamiento del video y el audio:
  - Arranca SIN sonido (los navegadores bloquean el autoplay con audio).
  - "Activar sonido" enciende el audio con fundido de entrada (~500 ms) y su
    texto cambia a "Silenciar"; recuerda la elección durante la sesión.
  - El audio: ambiente de estadio, sin voz, volumen inicial ≤ 30 %.
  - Si el video falla o tarda, se queda el poster; el indicador "Preparando…"
    desaparece cuando el video empieza a reproducirse.
  - Con `prefers-reduced-motion` o conexión lenta: solo el poster.
  - Si el audio es pesado, va como archivo aparte y se carga solo al activar
    el sonido.
  - Requisitos del video: 10–20 s, ≤ 10 MB, 1080p o menos, MP4 y WebM.
- Tres bloques numerados a sangre con líneas finas (01 Visión, 02 Métricas,
  03 Narrador): título 24 px y texto de 14 px en #A1A1AE.
- Franja "Impulsado por herramientas de IBM": logos tomados de
  `assets/logos/ibm/` mediante el manifest, versión oficial sin modificar y
  con espacio libre alrededor; respeta las reglas de uso de marca de IBM y
  documéntalo en logos/README.md. Mientras falten, recuadros punteados
  [Logo IBM] / [Logo herramienta].
- Leyenda al pie: Creadores, Programa, Licencia (textos desde config), más
  "OMNIMORPH" y "MATEO · Motor de análisis táctico y estadístico".

B) TABLERO MATEO (fondo #111111, rejilla con líneas de 1 px)
1. Cabecera: logo + MATEO + subtítulo; chip "BRA vs GER · 2014"; chip
   "Pipeline 9/9 OK" que pasa a ámbar/rojo si falla un módulo.
2. Tira de observabilidad: chips M1, M2.0–M2.5, M3, M4 con estado real
   (punto turquesa si está OK).
3. Reloj maestro: línea de tiempo blanca con ventanas W0…Wn, tiempo y frame
   (p. ej. 00:00.0 / duración · Frame 0 / 1799); sincroniza todos los paneles.
4. Panel de video doble: POST-MATEO (con las marcas de los modelos) como
   principal con chip "en vivo"; debajo, la transmisión original en miniatura
   sincronizada y la píldora blanca "Intercambiar".
5. Radar cenital 120 × 70 m, mismo alto que el video, cancha centrada.
6. KPIs (Block height, velocidad de transición): cifra en Jost 44 px, barra
   BRA/GER de 4 px, badge "BRA domina" en píldora naranja. Valores de GER
   vacíos ([—]) hasta tener datos.
7. Crónica IA: texto en serif, reproductor con forma de onda, pie con
   latencia y tokens.
8. Transcripción al español: líneas con marca de tiempo; ventana actual en
   blanco, siguiente atenuada con cursor; se completa conforme suena el audio.
9. Barra lateral de jugadores (derecha, 320 px): selector BRA/GER (píldoras),
   lista de 5 jugadores con UNA métrica activa y selector de métrica; ficha del
   jugador con mapa de calor y 3 cifras. Una idea por bloque.
   Crea un adaptador (un solo archivo) que mapee el formato que entregue mi
   equipo de análisis (CSV/JSON) a lo que consumen los componentes.
10. Leyenda al pie (Creadores, Programa, Licencia).

C) PANTALLA DE CARGA / RESPALDO (fondo blanco)
- Cubo de Rubik pequeño en SVG (naranja arriba, turquesa izquierda, morado
  derecha, con el cuadro rosa y el lima; la capa superior se levanta en
  bucle), "OMNIMORPH" en Jost 500, "Preparando el análisis…" con tres puntos
  pulsando.
- Bloque de respaldo: "¿Está tardando demasiado?…" y píldora negra "Reintentar".
- IMPORTANTE: debe ser autosuficiente (SVG y CSS incrustados en el HTML, sin
  archivos externos) para aparecer incluso si todo lo demás falla. Sirve como
  pantalla de carga inicial y como pantalla de error.

# PASO 4: LOGOS
- Todos los logos que yo suba van en `assets/logos/`, en su subcarpeta. Prefiere
  SVG; si es PNG, con fondo transparente.
- Los componentes NUNCA escriben rutas de logos a mano: leen
  `logos.manifest.json` (id, archivo, alt, ancho máximo, variante).
- Mientras falte un logo, muestra un recuadro punteado con su nombre entre
  corchetes y avísame cuáles faltan.
- Crea `assets/logos/README.md` con la fuente de cada logo, su licencia y las
  reglas de uso (espacio libre, colores permitidos, tamaño mínimo).

# PASO 5: RESPONSIVO Y CALIDAD
- Sin anchos fijos en px: rejilla fluida; la barra lateral baja debajo del
  contenido en pantallas angostas; franjas y leyenda se apilan.
- Fuentes locales; todo debe funcionar sin internet en la laptop.
- Sin CSS duplicado; sin `!important` salvo justificación; clases con
  convención consistente (BEM).

# PASO 6: VERIFICACIÓN (al terminar)
- Compara cada pantalla con el mockup y con DESIGN.md; dime en qué te saliste
  y corrígelo.
- Lista los valores derivados que no estaban en DESIGN.md.
- Verifica contraste, que no haya colores escritos a mano fuera de tokens y
  que ningún botón use color de marca.
- Prueba: portada con el video ausente, con el audio bloqueado y con
  movimiento reducido; pantalla de carga con la red cortada.
- Entrega: resumen de archivos creados/modificados, cómo correr el proyecto,
  lista de logos y archivos de video/audio pendientes, y una captura de cada
  pantalla.

# RESTRICCIONES
- No inventes datos ni textos legales: donde falte algo (creadores, programa,
  licencia, valores de GER) deja el marcador visible entre corchetes.
- No cambies el pipeline de visión, el LLM ni la síntesis de voz.
- Si hay una decisión de arquitectura que no está aquí, pregúntame antes de
  avanzar. nota parte del dashboard que tenemos y deja las capteas para agregar los logos y el video

---

### 🤖 Assistant

> 🔧 called: list_files



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas

### 🤖 Assistant

> 🔧 called: list_files, list_files



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\worldcupvoice

> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas

### 🤖 Assistant

> 🔧 called: list_files, glob



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\sports

> 🔧 **glob** — **/*.py

### 🤖 Assistant

> 🔧 called: read_file, list_files



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\implementacion\dashboard

> 🔧 **read_file** — c:\Users\Dell G3\Documents\omnimorph-pruebas\implementacion\dashboard\app.py

### 🤖 Assistant

> 🔧 called: read_file, list_files



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\01_diagramas_y_assets

> 🔧 **read_file** — data sources consumed, file paths, and structure of the pipeline outputs

### 🤖 Assistant

> 🔧 called: read_file, read_file



> 🔧 **read_file** — project description, pipeline stages, data sources

> 🔧 **read_file** — SVG content of the OMNIMORPH logo

### 🤖 Assistant

> 🔧 called: list_files, list_files

I now have a thorough picture of the codebase. Let me check what data files exist and check the data/clean/outputs structure quickly.

> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\outputs

> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\data

### 🤖 Assistant

> 🔧 called: list_files, list_files



> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\data\clean

> 🔧 **list_files** — c:\Users\Dell G3\Documents\omnimorph-pruebas\data\audio

### 🤖 Assistant

> 🔧 called: ask_followup_question

I now have a complete picture of the project. Here is my **PASO 0 — Reconocimiento** summary before doing anything else:

---

## PASO 0 — Reconocimiento: lo que encontré y mi plan

### El repositorio (10 líneas)

1. **Framework**: **Streamlit** (`implementacion/dashboard/app.py`), Python 3.12, no hay framework JavaScript. No hay Next.js/React/Vue. La capa visual es 100 % HTML/CSS inyectado con `st.markdown(..., unsafe_allow_html=True)`.
2. **Páginas existentes**: `app.py` (tablero principal MATEO, 4 paneles) + `pages/1_Observabilidad.py` (monitores en tabs). Son las dos pantallas del sistema, más cualquier portada que agreguemos.
3. **Datos del pipeline** (todos en `data/clean/`): `frames_clean.parquet`, `objects_cleaned.parquet`, `tactical_summaries.json`, `narrations.json`, `narrations_es.vtt`, más 8 reportes JSON de monitores (`monitor_m1–m4.json`, `pipeline_summary.json`, `governance_audit.jsonl`).
4. **Audio**: `data/audio/` — `NARRACION_COMPLETA_60S.wav` + `W0.wav`…`W7.wav` (8 clips TTS, cada ventana táctica de 4 s).
5. **Vídeo**: el pipeline busca MP4 en `outputs/mvp_pruebas/…/clip_13/VIDEO_OMNIMORPH_POST_MATEMATICA.mp4` y en `data/videos/mundial_2014_720p_hd/…`; **ningún vídeo hero/portada existe aún**.
6. **Logo actual**: un SVG sencillo en `01_diagramas_y_assets/logos/omnimorph_logo_nombre_light.svg` (fondo #0f172a, ⚽ en círculo azul, texto OMNIMORPH). **No hay logo cubo de Rubik, ni logos IBM, ni carpeta `assets/logos/`**.
7. **CSS actual**: inline directo en `st.markdown()`, colores y tamaños escritos a mano (#0f172a, #22c55e, etc.), sin sistema de tokens, sin DESIGN.md, sin estructura de carpetas de diseño.
8. **Pipeline**: no se toca. Mi alcance es estrictamente la **capa visual** — agregar una carpeta `dashboard/` con el sistema de diseño, las 3 pantallas HTML estáticas (portada, tablero de arranque, cargador) y guías para que luego el equipo conecte Streamlit al sistema.
9. **Restricción de modo**: estoy en **modo Ask (lectura)** — no puedo escribir ni modificar archivos. Puedo leer, analizar y entregar el plan y los contenidos; el equipo los crea en Agent mode.
10. **Plan**: entregar en este mensaje la estructura de carpetas, DESIGN.md, el HTML/CSS completo de las 3 pantallas y el plan de integración con Streamlit, listos para que un agente los escriba en Agent mode.

---

### Observación importante sobre la solicitud

Tu prompt pide que yo **construya** (cree archivos) una capa visual nueva. Eso requiere **escribir archivos**. Estoy en **modo Ask**, que es de sólo lectura. Puedo preparar **todo el contenido** aquí mismo en el chat (código completo, estructura, DESIGN.md, HTMLs), pero para que esos archivos existan en disco necesitas cambiar a **Agent mode**.

¿Qué quieres hacer?

### 🤖 Assistant

Estás en modo Ask (solo lectura), así que no puedo crear ni modificar archivos. Tu prompt pide construir toda la capa visual. ¿Cómo quieres proceder?

> 🔧 **ask_followup_question** — Estás en modo Ask (solo lectura), así que no puedo crear ni modificar archivos. Tu prompt pide construir toda la capa visual. ¿Cómo quieres proceder?