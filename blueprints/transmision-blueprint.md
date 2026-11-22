# Omnimorph — Página «Transmisión» — Blueprint

> Generado por The Architect (modo brownfield) el 2026-11-21
> Forma: cambio sobre una página web estática existente (dashboard de Omnimorph)
> Pista de ejecución: la del repo — Python 3.12 (`.venv`) + HTML/CSS/JS sin compilación + Node solo para pruebas
> Modo de emisión: archivo único (7 pasos)
> Versión del blueprint: 3 (2026-11-21: sin km/h — la velocidad queda «en pruebas»; protagonista = el más cercano al balón; panel «Alineaciones»)
> Versiones verificadas: 2026-11-21. Ver §11 para el origen de cada una
> Diseñó: Claude (solo diseño). Construye: Bob

---

## 1. Visión general y lo que queda fuera

### Visión
Una página nueva, **Transmisión**, que muestra el clip de Costa Rica vs. San Cristóbal y Nieves a pantalla
completa, con gráficos sobrepuestos como en la tele: marcador y reloj, sello de Omnimorph, el
protagonista de cada jugada (el jugador más cerca del balón) marcado con un triángulo y su estela,
un mini radar, el panel «Alineaciones» y la franja con la **voz de MATEO**. Es la pieza que se le mostraría a una televisora o a un
servicio de streaming: el análisis de Omnimorph convertido en experiencia para el aficionado, sin
términos técnicos.

Subtítulo de la página: **«El partido como en la tele, con la voz de MATEO»**.

### Usuarios
- **El equipo de Omnimorph y sus invitados (IBM, Gallos Blancos)** en la prueba con enlace público:
  abren la página, le dan a reproducir y miran 36 segundos de partido con los gráficos.
- **Un posible cliente de TV o streaming** en una demo en vivo: necesita entenderlo sin explicación.

### Objetivos — alcance de la v1
1. Un script `scripts/export_transmision.py` que genera `dashboard/data/transmision.json` a partir de
   los datos limpios que ya existen.
2. La página `dashboard/pages/transmision.html` con video a pantalla completa y los 7 gráficos.
3. «Transmisión» en el menú principal.
4. Pruebas automáticas: `scripts/probar_transmision.py` (datos, servidor, regresión) y
   `scripts/probar_transmision_logica.js` (lógica de los gráficos con Node).

### Lo que queda fuera — explícitamente, para la v1
| Fuera | Por qué |
|---|---|
| Transmisión en vivo | El pipeline procesa después del partido. Lo en vivo es otro proyecto |
| Otros partidos o clips | Solo el clip activo (`costa_rica_skn_eliminatorias_2026`, 1080 cuadros) |
| Videos amateur | Es la idea 1 del usuario. Va en otro blueprint |
| Llamadas nuevas a Granite o a cualquier LLM | Se reutilizan las 8 narraciones de `mateo_data.json` |
| Cambios en `dashboard/serve.py` | La página es estática; el servidor ya la sirve |
| Cambios en MATEO, Partido, Método, Operaciones, Opinión e Inicio | Solo se toca `site-nav.js` para el menú |
| Cambios en el pipeline o en `data/clean/` | El cambio solo lee esos archivos |
| Copiar la marca de otro canal (Magenta TV, Fussball.TV) | Se usa el formato como inspiración, con el diseño propio de `DESIGN.md` |
| Marcador del balón en pantalla | La detección del balón falla en 220 de 1080 cuadros. No se dibuja; solo se usa para elegir al protagonista |
| Velocidad en km/h | No es confiable: la calibración de la cámara salta en cada cuadro y la infla (un jugador trotando sale a ~11 km/h y hasta 34). La página dice que está **en pruebas**. Decisión del usuario, 2026-11-21 |
| Interfaces congeladas (ver §5) | `mateo_data.json`, `serve.py`, rutas de páginas existentes |

### Métricas de éxito
- `.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 7` sale con código 0.
- La página carga y reproduce los 36 s sin errores en la consola (lista de lanzamiento, §20.1).
- En la siguiente ronda de prueba con el equipo, la página aparece en el registro del servidor.

### Estado actual
| Aspecto | Hoy |
|---|---|
| Servidor | `dashboard/serve.py`: Python 3.12, solo biblioteca estándar. Sirve `dashboard/` como estático, con soporte de rangos para video. En modo prueba responde 410 a las páginas cuando vence el tiempo |
| Páginas | `dashboard/pages/*.html`. Cada una carga `../styles/tokens.css`, `../styles/base.css`, sus componentes CSS, y al final `../components/site-nav.js` y su propio JS |
| Estilo | `dashboard/DESIGN.md` es la única fuente visual y se traslada a `dashboard/styles/tokens.css`. Fondo oscuro, sin sombras ni degradados, números en `--font-mono` |
| Menú | `dashboard/components/site-nav.js`, arreglo `LINKS` |
| Datos del tablero | `scripts/export_dashboard_data.py` genera `dashboard/data/mateo_data.json` desde `data/clean/` |
| `mateo_data.json` | `meta` (fps 29.97, n_frames 1080, team_a SKN, team_b CRC, colores), `media` (videos, audio, vtt), `windows` (8 jugadas con `narration`), `players` (46, con `dorsal`, `jugador`, `certeza` y `rastros` en 10 de ellos), `frames` (1080, `{"p": [[id, team, x_dm, y_dm], …], "b": [x_dm, y_dm] o null}`) |
| `data/clean/objects_cleaned.parquet` | Una fila por detección. Columnas: `frame, t, source, track_id, class_id, class_name, team, x1, y1, x2, y2, conf, pitch_x, pitch_y, track_id_stitched, pitch_x_smooth, pitch_y_smooth, vx_mps, vy_mps, v_mps, v_clipped`. Las cajas están en píxeles del video de 1280×720 |
| Medios | `dashboard/media/ORIGINAL_HP3zxNuoWXE-720-15.mp4` (1280×720, con audio del estadio), `NARRACION_COMPLETA_60S.wav` (36.04 s, alineado con el clip), `narrations_es.vtt` (8 subtítulos, uno por jugada, con prefijo `[W0]` … `[W7]`). `dashboard/media/` no se sube a git |
| Pruebas | Sin pytest. Scripts de prueba en `scripts/probar_*.py` que levantan `serve.py` en un puerto libre |
| Lint / CI | Ninguno configurado |

### Estado objetivo
Tras el cambio existen 8 archivos nuevos (uno de ellos generado, `transmision.json`) y 1 archivo
modificado, todos en las convenciones del repo:
la página nueva sigue el patrón de `metodo.html` (cabecera, menú, pie), el JS va en IIFE con
`'use strict'` como `site-nav.js`, los estilos usan solo variables de `tokens.css`, y el script de
exportación sigue el patrón de `export_dashboard_data.py` (rutas desde `ROOT`, salida JSON compacta).

---

## 2. Stack tecnológico

| Capa | Elección | Por qué |
|---|---|---|
| Datos | Python 3.12 de `.venv` + pandas + pyarrow (ya instalados) | El export lee parquet, igual que `export_dashboard_data.py` |
| Página | HTML + CSS + JS sin compilación | Es la convención del dashboard. Nada que instalar |
| Gráficos sobre el video | DOM posicionado + un `<svg>` para la estela y el radar | Sin librerías; escalan con una sola variable CSS |
| Pruebas de lógica | Node (`node:assert`, sin paquetes) | La lógica de los gráficos se prueba sin navegador |
| Pruebas de datos y servidor | Python, mismo patrón que `scripts/probar_modo_prueba.py` | Ya es la forma de probar del repo |
| Servidor | `dashboard/serve.py` sin cambios | Ya sirve archivos estáticos y rangos de video |

### Comprobación de compatibilidad
No se agrega ninguna dependencia. Node solo corre pruebas con módulos integrados (`node:assert`) y
`node --check`; sirve cualquier Node ≥ 18. Probado en esta máquina con v21.6.2.

---

## 3. Estructura de directorios

### Delta
```
scripts/
├── export_transmision.py            NUEVO  — genera dashboard/data/transmision.json
├── probar_transmision.py            NUEVO  — pruebas de datos, servidor y regresión (--hasta N)
└── probar_transmision_logica.js     NUEVO  — pruebas de la lógica con Node (--hasta N)
dashboard/
├── data/transmision.json            NUEVO (generado y versionado, como mateo_data.json)
├── pages/transmision.html           NUEVO
├── components/
│   ├── transmision-logica.js        NUEVO  — funciones puras, sin DOM
│   ├── transmision.js               NUEVO  — pinta la página
│   └── site-nav.js                  MODIFICADO — una entrada más en LINKS
└── styles/components/transmision.css NUEVO
```
Nada se borra.

---

## 4. Modelo de datos

### Entidades
No hay base de datos. El único dato nuevo es `dashboard/data/transmision.json`. Este es su contrato
completo:

```json
{
  "version": 1,
  "partido": {
    "titulo": "Costa Rica vs. San Cristóbal y Nieves",
    "competicion": "Eliminatorias Concacaf · Mundial 2026",
    "local":  {"team": 1, "codigo": "CRC", "nombre": "Costa Rica",            "color": "#00BFFF"},
    "visita": {"team": 0, "codigo": "SKN", "nombre": "San Cristóbal y Nieves", "color": "#FF1493"},
    "marcador": [0, 0],
    "reloj_inicio_s": 63
  },
  "video": {"src": "../media/ORIGINAL_HP3zxNuoWXE-720-15.mp4", "ancho": 1280, "alto": 720,
            "fps": 29.97, "n_frames": 1080},
  "narracion": {"audio": "../media/NARRACION_COMPLETA_60S.wav", "vtt": "../media/narrations_es.vtt"},
  "jugadores": {"6": {"team": 1, "etiqueta": "14 · Galo"}, "3": {"team": 0, "etiqueta": "Jugador SKN"}},
  "cuadros": [[[6, 412, 300, 440, 372]]],
  "balon":   [[590, 448]],
  "cancha":  [{"p": [[6, 1, 640, 310]], "b": [578, 397]}],
  "jugadas": [{"id": "W0", "t0": 0.0, "t1": 4.5, "f0": 0, "f1": 134,
               "texto": "San Cristóbal y Nieves presiona desde el primer minuto, …",
               "protagonista": 1, "frames_cerca": 45}],
  "ficha": {"estadio": "Estadio Nacional de Costa Rica", "asistencia": 15700,
            "local":  {"esquema": "3-4-2-1", "entrenador": "Gustavo Alfaro"},
            "visita": {"esquema": "5-4-1",   "entrenador": "Francisco Molina"}}
}
```
Los valores de `jugadores`, `cuadros`, `balon`, `cancha` y `jugadas` en el ejemplo son ilustrativos de
la forma; los de `ficha` son los reales. Las reglas exactas:

| Campo | Regla |
|---|---|
| `partido.local` / `visita` | `local` = el equipo con código `meta.team_b` de `mateo_data.json` (CRC, `team` 1); `visita` = `meta.team_a` (SKN, `team` 0). `nombre` y `color` salen de `meta.team_b_name` / `team_b_color` y `meta.team_a_name` / `team_a_color` |
| `partido.titulo` | `meta.titulo` de `mateo_data.json` |
| `partido.competicion` | El literal `"Eliminatorias Concacaf · Mundial 2026"` |
| `partido.reloj_inicio_s` | Constante `CLIP_INICIO_S = 63` en el script. Dato del usuario (2026-11-21): el clip va del minuto 1:03 al 1:39 |
| `partido.marcador` | `[goles local, goles visita]` contando en `dashboard/data/partido/partido.json` → `goles` los que tienen `segundo_oficial` no nulo y `< 63`. Un gol es del local si `equipo_anotador == partido.local.nombre`. Para este clip da `[0, 0]` (el primer gol es del minuto 40) |
| `video` | `src` = `media.original` de `mateo_data.json` (hoy `"../media/ORIGINAL_HP3zxNuoWXE-720-15.mp4"`). `ancho` 1280 y `alto` 720 fijos (resolución de las cajas). `fps` y `n_frames` de `meta` |
| `narracion` | `media.audio` y `media.vtt` de `mateo_data.json` |
| `jugadores` | Una entrada por cada id de `mateo_data.json` → `players`. Clave = id como texto. `team` = `players[i].team`. `etiqueta`: si `certeza` es `"alta"` o `"media"` y hay `jugador` → `f"{dorsal} · {jugador.title()}"`; si no, si hay `dorsal` → `f"#{dorsal} {codigo}"`; si no → `f"Jugador {codigo}"`, con `codigo` = código del equipo de ese jugador (`team` 0 → SKN, `team` 1 → CRC, `team` 2 → `"Árbitro"` como etiqueta completa) |
| `cuadros` | Lista de exactamente `n_frames` elementos. El elemento `f` es la lista de cajas del cuadro `f`, ordenada por id ascendente. Cada caja: `[id, x1, y1, x2, y2]` con coordenadas enteras en píxeles del video, recortadas a `0..1279` y `0..719`. Sin velocidad |
| `balon` | Lista de exactamente `n_frames` elementos: `[cx, cy]` enteros = centro de la caja del balón (`source == "ball"`, primera fila del cuadro) o `null` si no hay balón en ese cuadro |
| `cancha` | Copia literal de `mateo_data.json` → `frames` (mismo largo y forma). Lo usa el radar |
| `jugadas` | Una por cada elemento de `mateo_data.json` → `windows`, en el mismo orden. `id`, `t0`, `t1`, `f0`, `f1` copiados. `texto` = `narration`. Para cada cuadro de `f0..f1` (incluidos) con `balon` no nulo, el **más cercano** es el id cuya caja tiene el centro inferior (`(x1+x2)/2`, `y2`) a menor distancia euclidiana del balón, si esa distancia es `<= 120` px (empate → id menor). `protagonista` = el id que fue el más cercano en más cuadros de la jugada (empate → id menor), solo si lo fue en **al menos 15** cuadros; si no, `null`. `frames_cerca` = esos cuadros (o `0` si `protagonista` es `null`) |
| `ficha` | De `dashboard/data/partido/partido.json`: `estadio` y `asistencia` de `partido`; `local` y `visita` con `esquema` = `esquema_inicial` y `entrenador` del equipo de `equipos` cuyo `codigo` coincide con `partido.local.codigo` / `partido.visita.codigo` |

**Cómo se calculan las cajas** (en `export_transmision.py`):
1. Leer `data/clean/objects_cleaned.parquet` y quedarse con `source == "track"`, `class_name == "player"`
   y `track_id_stitched` no nulo.
2. Mapear cada `track_id_stitched` a su id canónico: para cada jugador de `players` con `rastros`, cada
   id de `rastros` apunta a `rastros[0]`. Los demás ids quedan igual.
3. Descartar filas cuyo id canónico no esté en `players`. Si un id canónico tiene dos filas en el
   mismo cuadro, quedarse con la primera (como hace `fusionar_rastros` en `export_dashboard_data.py`).
4. No se calcula ninguna velocidad: `v_mps`, `v_clipped` y las posiciones en cancha son demasiado
   ruidosas para dar km/h creíbles (ver §1, lo que queda fuera).

### Relaciones
Todo id de `cuadros` y de `jugadas[].protagonista` existe en `jugadores`.

### Índices
NOT APPLICABLE — no hay base de datos.

### Esquema
El bloque JSON y la tabla de arriba son el esquema.

### Migraciones
NOT APPLICABLE — no hay base de datos.

### Datos semilla
NOT APPLICABLE — los datos salen del export; no hay semilla.

---

## 5. Diseño de la API

### Convenciones
No hay endpoints nuevos. La página es estática y `serve.py` la sirve tal como sirve las demás.

### Rutas
| Ruta | Método | Respuesta |
|---|---|---|
| `/pages/transmision.html` | GET | 200, HTML (410 si el modo prueba venció, como el resto) |
| `/data/transmision.json` | GET | 200, JSON |
| `/components/transmision-logica.js`, `/components/transmision.js`, `/styles/components/transmision.css` | GET | 200 |

### Endpoints críticos — detalle
NOT APPLICABLE — no hay endpoints dinámicos nuevos.

### Interfaces que no se mueven
| Interfaz | Regla |
|---|---|
| `dashboard/data/mateo_data.json` | Solo se lee. Ni su forma ni su contenido cambian |
| `dashboard/serve.py` | Sin cambios |
| `data/clean/*` | Solo se lee |
| Rutas `/pages/{index,mateo,partido,metodo,operaciones,opinion}.html` | Siguen respondiendo 200 |
| Las 4 entradas actuales de `LINKS` en `site-nav.js` | Mismo orden y mismos textos; «Transmisión» se agrega al final |

---

## 6. Arquitectura del frontend

### Rutas
Una página: `dashboard/pages/transmision.html`.

### Estrategia de renderizado
Página estática. Al cargar, `transmision.js` pide `../data/transmision.json`, prepara el video y los
gráficos, y muestra un botón grande **«Ver transmisión»** (los navegadores bloquean el sonido sin un
clic). Al pulsarlo empiezan a la vez el video y la narración. Cada cuadro de animación
(`requestAnimationFrame`) calcula el cuadro actual con `indiceCuadro` y actualiza los gráficos.

### Jerarquía de componentes (HTML de la página)
```
body.page-transmision
├── header.site-header           (igual que metodo.html, subtítulo «MATEO · Transmisión», con nav#site-nav)
├── main.transmision
│   ├── div.tv#tv                (escenario 16:9; define --tv-escala)
│   │   ├── video#tv-video       (playsinline, preload="auto", sin controles nativos)
│   │   ├── audio#tv-voz         (preload="auto")
│   │   ├── div.tv__capa         (todos los gráficos; pointer-events: none)
│   │   │   ├── div.tv-marcador#tv-marcador      ① reloj · CRC 0-0 SKN
│   │   │   ├── div.tv-sello                     ② «Omnimorph · IBM Granite»
│   │   │   ├── div.tv-protagonista#tv-protagonista  ③ etiqueta del jugador
│   │   │   ├── svg.tv-trazos#tv-trazos          ⑥ estela + triángulo (viewBox 0 0 1280 720)
│   │   │   ├── div.tv-radar#tv-radar            ④ svg viewBox 0 0 1200 700
│   │   │   ├── div.tv-ficha#tv-ficha            ⑤ «Alineaciones» + 2 filas + estadio
│   │   │   └── div.tv-mateo#tv-mateo            ⑦ franja de MATEO (aria-live="polite")
│   │   └── button.tv-inicio#tv-inicio           «Ver transmisión»
│   └── div.tv-controles         botones: Pausa/Reanudar (#tv-pausa), Voz de MATEO sí/no (#tv-voz-toggle), Repetir (#tv-repetir)
├── p.tv-subtitulo               «El partido como en la tele, con la voz de MATEO»
├── p.tv-nota#tv-nota           «La velocidad de los jugadores está en pruebas: la calibración de la cámara todavía no da cifras confiables, por eso no la mostramos.»
└── footer.site-credit           (igual que metodo.html)
```

### Manejo de estado
Un objeto `estado` dentro del IIFE de `transmision.js`: `{datos, reproduciendo, vozActiva}`. Nada en
`localStorage`.

### Estados de carga, vacío y error
| Estado | Qué se ve |
|---|---|
| Cargando | El botón «Ver transmisión» deshabilitado con el texto «Preparando…» |
| Listo | El botón habilitado |
| Sin `transmision.json` | Aviso `div.notice.notice--alert#data-error` como en `metodo.html`: «No se pudo cargar data/transmision.json. Ejecuta .venv/Scripts/python.exe scripts/export_transmision.py» |
| Sin video | Mismo aviso con el texto «No se encontró el video del partido en dashboard/media/» |

---

## 7. Sistema de diseño

Manda `dashboard/DESIGN.md`. Esta página solo usa variables que ya existen en `tokens.css`.

### Colores
| Uso | Variable |
|---|---|
| Fondo de la página y del escenario | `--color-bg-deep` |
| Fondo de los paneles sobre el video | `color-mix(in srgb, var(--color-bg) 88%, transparent)` |
| Borde de paneles | `--border` |
| Texto | `--color-text`; secundario `--color-text-soft` |
| Color de cada equipo | `partido.local.color` / `partido.visita.color` del JSON, aplicado inline |
| Árbitro en el radar | `--color-text-soft` |
| Acento (triángulo, título «Alineaciones», palabra «MATEO») | `--color-ball` |
| Estela | `--color-ok` |
| Cancha del radar | fondo `--color-pitch`, líneas `--color-pitch-lines` |

### Tipografía
| Elemento | Variable |
|---|---|
| Códigos de equipo y «MATEO» | `--font-headline` |
| Reloj, marcador, esquemas, cifras | `--font-mono` |
| Etiquetas y texto de la franja | `--font-ui` |

Tamaños en `em` sobre `font-size: calc(var(--tv-escala) * 16px)` en `.tv__capa`, para que todo escale
con el video. `--tv-escala` = ancho del escenario / 1280, lo fija `transmision.js` al cargar y en cada
`resize`.

### Espaciado, radio, elevación
- Escenario: `aspect-ratio: 16 / 9; width: 100%; max-width: calc((100vh - 140px) * 16 / 9); margin: 0 auto`.
- Marcador, sello y etiqueta del protagonista: forma de píldora (`--radius-pill`).
- Radar, «Alineaciones» y franja de MATEO: radio `--radius-card` (0).
- `p.tv-nota`: debajo del escenario, `--text-small`, color `--color-text-soft`, centrada.
- Sin sombras ni degradados.

### Posiciones sobre el video (en % del escenario)
| Gráfico | Posición |
|---|---|
| ① Marcador | arriba 3 %, izquierda 2 % |
| ② Sello | arriba 3 %, derecha 2 % |
| ③ Protagonista | abajo 22 %, izquierda 2 % |
| ④ Radar | abajo 20 %, centrado, ancho 26 % |
| ⑤ Alineaciones | abajo 20 %, derecha 2 %, ancho mínimo 22 % |
| ⑥ Triángulo | 10 px de video arriba del borde superior de la caja del protagonista, centrado en x |
| ⑦ Franja MATEO | abajo 3 %, izquierda 2 %, derecha 2 % |

### Movimiento
Los gráficos ③④⑤⑥ entran y salen con `opacity` en `var(--transition)`. Con
`prefers-reduced-motion: reduce`, sin transición.

### Estilo de componentes
Igual que el boceto aprobado el 2026-11-21: paneles planos oscuros, texto claro, el color de equipo
como borde izquierdo de 3 px en la etiqueta del protagonista.

---

## 8. Autenticación y autorización

NOT APPLICABLE — la página es pública dentro del dashboard, igual que las demás. El modo prueba de
`serve.py` ya la cubre sin cambios.

---

## 9. ORDEN DE CONSTRUCCIÓN

Reglas para Bob:
- Todos los comandos se ejecutan desde la raíz del repo (`C:\Users\Dell G3\Documents\omnimorph-pruebas`)
  en **Git Bash**.
- Un paso no está listo hasta que su `Verify` sale con código 0 **y** los de los pasos anteriores
  también (cada `probar_transmision.py --hasta N` vuelve a correr los pasos 1…N).
- No adelantar pasos. Si uno se bloquea, parar y avisar.
- **Antes de cada commit, mostrar al usuario lo que se va a subir y esperar su aprobación** (regla del
  usuario). Nunca `git add -A`: rutas explícitas, como en los `Checkpoint`.
- Para volver atrás: `git revert --no-edit <commit del paso>` (deshace solo ese paso). **Nunca
  `git reset --hard`, `stash` ni cambio de rama**: la carpeta y la rama `feat-costa-rica` son
  compartidas con Claude y Gemini, y hay trabajo sin commit de otros. Los tags `step-NN-*` sirven para
  ubicar cada paso (`git diff step-03-pagina-base step-04-protagonista`).

### Mapa de pasos
| # | Slug | Entrega |
|---|---|---|
| 1 | exportar-datos | `export_transmision.py`, `transmision.json`, pruebas paso 1 |
| 2 | logica-base | `transmision-logica.js` (cuadro, reloj, escala) + pruebas con Node |
| 3 | pagina-base | Página con video, botón de inicio, marcador ①, sello ② |
| 4 | protagonista | ③ protagonista, ⑥ triángulo con estela, y la función de horario de gráficos |
| 5 | radar-alineaciones | ④ mini radar y ⑤ alineaciones |
| 6 | voz-mateo | ⑦ franja de MATEO con audio sincronizado y controles |
| 7 | menu-regresion | «Transmisión» en el menú y regresión del resto del dashboard |

---

#### Paso 1 — Exportar los datos de la transmisión

**Do**
1. Crear `scripts/export_transmision.py` que escribe `dashboard/data/transmision.json` con el contrato
   exacto de §4 (todas las reglas de la tabla y el cálculo de cajas). Detalles:
   - `ROOT = pathlib.Path(__file__).resolve().parent.parent`; leer
     `ROOT/"data/clean/objects_cleaned.parquet"`, `ROOT/"dashboard/data/mateo_data.json"`,
     `ROOT/"dashboard/data/partido/partido.json"`.
   - Constante `CLIP_INICIO_S = 63` con el comentario
     `# Dato del usuario (2026-11-21): el clip va del 1:03 al 1:39 del partido`.
   - Escribir con `json.dump(datos, f, ensure_ascii=False, separators=(",", ":"))` en UTF-8. Mismas
     entradas → mismos bytes (sin fechas ni azar).
   - Si falta un archivo de entrada: imprimir `[FALLA] falta <ruta>` y salir con código 1.
   - Al terminar imprimir `[OK] dashboard/data/transmision.json  cuadros=<n> jugadores=<n> jugadas=<n> bytes=<n>`.
   - Reconfigurar `sys.stdout` a UTF-8 como hace `probar_modo_prueba.py` (consola de Windows).
2. Crear `scripts/probar_transmision.py` con el mismo estilo que `scripts/probar_modo_prueba.py`
   (`_OK`/`_FALLA`, `sys.stdout` en UTF-8), argumento `--hasta N` (entero 1–7, por defecto 7) que
   corre las funciones `paso_1()` … `paso_N()` en orden, imprime cada caso y sale con código 0 solo si
   todos pasan (1 si alguno falla). En este paso solo existe `paso_1()`, con estos casos:
   1. Correr `export_transmision.py` dos veces con `sys.executable`; ambas salen 0 y el SHA-256 del
      archivo es idéntico.
   2. `version == 1`; `len(cuadros) == len(cancha) == video.n_frames == mateo_data.meta.n_frames`.
   3. Toda caja de `cuadros` tiene exactamente 5 elementos; `len(balon) == n_frames` y cada elemento
      de `balon` es `null` o 2 enteros dentro de `0..1279` × `0..719`.
   4. Todo id de `cuadros` y de `protagonista` está en `jugadores`; toda jugada con `protagonista` no
      nulo tiene `frames_cerca >= 15`, y `jugadas[0].protagonista == 1` (dato real: en la primera
      jugada el id 1 es el más cercano al balón en 45 cuadros).
   5. `len(jugadas) == len(mateo_data.windows)` y cada `texto` es igual a su `narration`.
   6. `partido.reloj_inicio_s == 63` y `partido.marcador == [0, 0]`.
   7. Etiquetas: `jugadores["6"].etiqueta == "14 · Galo"` y `jugadores["1"].etiqueta == "11 · Rogers"`
      (datos reales de `mateo_data.json`: id 6 = GALO, dorsal 14, certeza alta; id 1 = ROGERS,
      dorsal 11, certeza media). Además, todo jugador sin `jugador` en `mateo_data.json` tiene una
      etiqueta que empieza con `"Jugador "`, `"#"` o es `"Árbitro"`.
   8. Tamaño del archivo `< 3_000_000` bytes.
   9. `ficha == {"estadio": "Estadio Nacional de Costa Rica", "asistencia": 15700, "local":
      {"esquema": "3-4-2-1", "entrenador": "Gustavo Alfaro"}, "visita": {"esquema": "5-4-1",
      "entrenador": "Francisco Molina"}}` (datos validados de `partido.json`), y la cadena `"kmh"` no
      aparece en el archivo.

**Done when**
- [ ] WHEN se ejecuta `export_transmision.py` dos veces THE SYSTEM SHALL escribir `dashboard/data/transmision.json` con bytes idénticos y salir con 0.
- [ ] WHEN se valida el JSON THE SYSTEM SHALL tener tantos `cuadros` y `balon` como `meta.n_frames` de `mateo_data.json`, cajas de 5 elementos y ninguna velocidad.
- [ ] WHEN se elige al protagonista de la primera jugada THE SYSTEM SHALL dar el id 1 con al menos 15 cuadros cerca del balón.
- [ ] WHEN se leen las etiquetas THE SYSTEM SHALL dar `"14 · Galo"` para el id 6 y `"11 · Rogers"` para el id 1.
- [ ] WHEN falta `data/clean/objects_cleaned.parquet` THE SYSTEM SHALL imprimir `[FALLA] falta …` y salir con código 1.

**Verify**
```bash
.venv/Scripts/python.exe scripts/export_transmision.py          # expect: línea [OK] dashboard/data/transmision.json …, exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 1 # expect: todos los casos OK, exit 0
mv data/clean/objects_cleaned.parquet data/clean/objects_cleaned.parquet.bak
status=0; .venv/Scripts/python.exe scripts/export_transmision.py || status=$?
mv data/clean/objects_cleaned.parquet.bak data/clean/objects_cleaned.parquet
test "$status" -eq 1                                             # expect: el export falla con 1 sin el parquet → la línea sale 0
test -f data/clean/objects_cleaned.parquet                       # expect: el parquet volvió a su lugar
```

**Checkpoint**
```bash
git add scripts/export_transmision.py scripts/probar_transmision.py dashboard/data/transmision.json
git commit -m "feat(transmision): datos de la transmisión desde data/clean"
git tag step-01-exportar-datos
```

---

#### Paso 2 — Lógica base de los gráficos

**Do**
1. Crear `dashboard/components/transmision-logica.js`: funciones puras, sin DOM, en este envoltorio
   para que funcione en el navegador (`window.TransmisionLogica`) y en Node (`module.exports`):
   ```js
   (function (raiz) {
     'use strict';
     var L = {};
     // … funciones …
     if (typeof module !== 'undefined' && module.exports) module.exports = L;
     else raiz.TransmisionLogica = L;
   })(this);
   ```
   Funciones de este paso (contrato exacto):
   | Función | Devuelve |
   |---|---|
   | `indiceCuadro(t, fps, n)` | `Math.floor(t * fps)` acotado a `0..n-1`; `t` negativo o `NaN` → 0 |
   | `reloj(t, inicioS)` | `"MM:SS"` de `inicioS + Math.floor(max(t, 0))`, con ceros a la izquierda |
   | `escala(anchoEscenario, anchoVideo)` | `anchoEscenario / anchoVideo`; si alguno es 0 o no numérico → 1 |
2. Crear `scripts/probar_transmision_logica.js`: carga el módulo con
   `require('../dashboard/components/transmision-logica.js')`, usa `node:assert/strict`, acepta
   `--hasta N` (por defecto 7) y corre los grupos de casos de los pasos 2…N. Imprime
   `OK <n> casos` y sale 0, o el primer error y sale 1. Casos del paso 2 (literales):
   - `indiceCuadro(0, 29.97, 1080) === 0`; `indiceCuadro(1, 29.97, 1080) === 29`;
     `indiceCuadro(100, 29.97, 1080) === 1079`; `indiceCuadro(-1, 29.97, 1080) === 0`.
   - `reloj(0, 63) === "01:03"`; `reloj(36.04, 63) === "01:39"`; `reloj(-2, 63) === "01:03"`.
   - `escala(640, 1280) === 0.5`; `escala(0, 1280) === 1`.
3. Agregar `paso_2()` a `scripts/probar_transmision.py`: corre
   `node --check dashboard/components/transmision-logica.js` y
   `node scripts/probar_transmision_logica.js --hasta 2`, ambos deben salir 0.

**Done when**
- [ ] WHEN Node carga `transmision-logica.js` THE SYSTEM SHALL exponer `indiceCuadro`, `reloj` y `escala`.
- [ ] WHEN `t = 36.04` y el inicio es 63 s THE SYSTEM SHALL devolver `"01:39"`.
- [ ] WHEN `t` es negativo THE SYSTEM SHALL devolver el cuadro 0 y el reloj `"01:03"`.
- [ ] WHEN el ancho del escenario es 0 THE SYSTEM SHALL devolver una escala de 1.

**Verify**
```bash
node --check dashboard/components/transmision-logica.js              # expect: sin salida, exit 0
node scripts/probar_transmision_logica.js --hasta 2                  # expect: OK <n> casos, exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 2     # expect: pasos 1 y 2 OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/components/transmision-logica.js scripts/probar_transmision_logica.js scripts/probar_transmision.py
git commit -m "feat(transmision): lógica base de cuadro, reloj y escala"
git tag step-02-logica-base
```

---

#### Paso 3 — Página base: video, inicio, marcador y sello

**Do**
1. Crear `dashboard/pages/transmision.html` con la jerarquía de §6, copiando de `metodo.html` el
   `<head>` (sin los CSS de chat, consola, tabs, match-hub) y la cabecera y el pie. CSS que carga:
   `tokens.css`, `base.css`, `components/pill-button.css`, `components/status-chips.css`,
   `components/site-header.css`, `components/site-credit.css`, `components/site-nav.css`,
   `components/transicion.css`, `components/transmision.css`. Scripts al final del `body`, en este
   orden: `../components/site-nav.js`, `../components/transmision-logica.js`,
   `../components/transmision.js`. `<title>MATEO — Transmisión</title>`. Incluye todos los elementos
   de §6 con sus ids (los de pasos posteriores pueden quedar vacíos y ocultos con `hidden`).
2. Crear `dashboard/styles/components/transmision.css` con el escenario, la capa, el marcador, el
   sello, el botón de inicio y los controles según §7. Solo variables de `tokens.css`.
3. Crear `dashboard/components/transmision.js` (IIFE con `'use strict'`):
   - `fetch('../data/transmision.json')`; si falla, mostrar `#data-error` (§6).
   - Asignar `video.src`, fijar `--tv-escala` con `TransmisionLogica.escala(tv.clientWidth, datos.video.ancho)` al cargar y en `resize`.
   - Botón `#tv-inicio`: deshabilitado con «Preparando…» hasta `loadeddata`; luego «Ver transmisión».
     Al pulsarlo: `video.play()`, ocultar el botón.
   - `#tv-pausa` alterna pausa y reproducción; `#tv-repetir` vuelve a `currentTime = 0` y reproduce.
     Barra espaciadora = pausa.
   - Bucle con `requestAnimationFrame`: `t = video.currentTime`; `#tv-marcador` muestra
     `reloj(t, partido.reloj_inicio_s)`, `local.codigo`, `marcador[0] - marcador[1]`, `visita.codigo`,
     cada código con su color. `.tv-sello` muestra el texto fijo «Omnimorph · IBM Granite».
   - `p.tv-nota#tv-nota` con el texto literal de §6 (velocidad en pruebas), siempre visible.
4. Agregar `paso_3()` a `probar_transmision.py`: levanta `serve.py --port <libre>` (igual que
   `probar_modo_prueba.py`, sin modo prueba), espera a que responda y comprueba:
   - `GET /pages/transmision.html` → 200 y el HTML contiene los ids `tv`, `tv-video`, `tv-marcador`,
     `tv-inicio`, `tv-protagonista`, `tv-trazos`, `tv-radar`, `tv-ficha`, `tv-mateo`, `tv-voz`,
     `tv-nota`, `data-error`, y la frase `está en pruebas`. No contiene `km/h`.
   - `GET` 200 a `/data/transmision.json`, `/components/transmision.js`,
     `/components/transmision-logica.js`, `/styles/components/transmision.css`.
   - `node --check dashboard/components/transmision.js` sale 0.
   - `transmision.css` no contiene `box-shadow` ni `gradient`.
   - Apaga el servidor al terminar, también si algo falla (`try/finally`).

**Done when**
- [ ] WHEN el servidor recibe `GET /pages/transmision.html` THE SYSTEM SHALL responder 200 con todos los ids de §6.
- [ ] WHEN se piden el JSON, los dos JS y el CSS de la página THE SYSTEM SHALL responder 200 a cada uno.
- [ ] WHEN se revisa `transmision.js` con `node --check` THE SYSTEM SHALL salir con 0.
- [ ] WHEN se revisa `transmision.css` THE SYSTEM SHALL no contener `box-shadow` ni `gradient`.

**Verify**
```bash
node --check dashboard/components/transmision.js                     # expect: exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 3     # expect: pasos 1–3 OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/pages/transmision.html dashboard/styles/components/transmision.css dashboard/components/transmision.js scripts/probar_transmision.py
git commit -m "feat(transmision): página base con video, marcador y sello"
git tag step-03-pagina-base
```

---

#### Paso 4 — Protagonista, triángulo y estela

**Do**
1. Agregar a `transmision-logica.js`:
   | Función | Contrato |
   |---|---|
   | `jugadaEn(t, jugadas)` | Índice de la jugada con `t0 <= t < t1`; si `t >= t1` de la última → índice de la última; si no hay ninguna → `-1` |
   | `graficosVisibles(t, jugadas)` | `{indice, protagonista, radar, ficha}`. Con `i = jugadaEn(t, jugadas)`; si `i === -1` todo `false`. Con `dt = t - j.t0` y `dur = j.t1 - j.t0`: `protagonista = 0.5 <= dt && dt < 3.5`; `radar = (i % 2 === 0) && 0.5 <= dt && dt < dur - 0.3`; `ficha = (i % 2 === 1) && 0.5 <= dt && dt < dur - 0.3` |
   | `cajaDe(cuadro, id)` | La caja `[id, x1, y1, x2, y2]` con ese id en la lista `cuadro`, o `null` |
   | `estela(cuadros, id, f, largo)` | Lista de puntos `[x, y]` = centro inferior de la caja (`(x1+x2)/2`, `y2`) del id en los cuadros `max(0, f-largo+1) .. f`, en orden, saltando cuadros donde no está |
2. Casos nuevos en `probar_transmision_logica.js` (grupo del paso 4), con
   `J = [{t0: 0, t1: 4.5}, {t0: 4.5, t1: 9.01}]`:
   - `jugadaEn(1, J) === 0`; `jugadaEn(5, J) === 1`; `jugadaEn(20, J) === 1`; `jugadaEn(-1, J) === -1`.
   - `graficosVisibles(0.2, J)` → `protagonista`, `radar`, `ficha` todos `false`.
   - `graficosVisibles(1.0, J)` → `{indice: 0, protagonista: true, radar: true, ficha: false}`.
   - `graficosVisibles(4.4, J)` → `protagonista: false`, `radar: false`.
   - `graficosVisibles(5.0, J)` → `{indice: 1, protagonista: true, radar: false, ficha: true}`.
   - Con `C = [[[6,10,10,20,40]], [], [[6,12,10,22,42]]]`: `cajaDe(C[2], 6)[4] === 42`;
     `cajaDe(C[1], 6) === null`; `estela(C, 6, 2, 15)` es `[[15,40],[17,42]]`.
3. En `transmision.js`, en cada cuadro: con `graficosVisibles` y la jugada actual `j`:
   - ③ `#tv-protagonista` visible si `protagonista` y `j.protagonista !== null`; texto =
     `jugadores[j.protagonista].etiqueta`; borde izquierdo con el color de su equipo.
   - ⑥ Si además `cajaDe(cuadro actual, j.protagonista)` existe: en `#tv-trazos` (viewBox
     `0 0 1280 720`) una `polyline` con `estela(cuadros, id, f, 15)` en `--color-ok` de 3 de grosor, y
     un triángulo relleno `--color-ball` 10 px arriba de `y1`, centrado en x (§7). Si no hay caja:
     ocultar estela y triángulo. No se muestra ninguna cifra de velocidad.
   - Agregar en `transmision.css` los estilos de ③ y ⑥ (§7).
4. `paso_4()` en `probar_transmision.py`: corre `node scripts/probar_transmision_logica.js --hasta 4`
   y `node --check` de los dos JS; y verifica en `transmision.json` que cada jugada con
   `protagonista` no nulo tiene ese id en al menos una caja entre `f0` y `f1`.

**Done when**
- [ ] WHEN `t = 1.0` en la primera jugada THE SYSTEM SHALL marcar visibles al protagonista y al radar, y no a las alineaciones.
- [ ] WHEN `t = 4.4` THE SYSTEM SHALL ocultar al protagonista y al radar.
- [ ] WHEN el protagonista no aparece en el cuadro THE SYSTEM SHALL devolver `null` en `cajaDe` y la estela solo con los cuadros donde aparece.
- [ ] WHEN se revisa `transmision.json` THE SYSTEM SHALL tener a cada protagonista presente en su jugada.

**Verify**
```bash
node scripts/probar_transmision_logica.js --hasta 4                  # expect: OK <n> casos, exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 4     # expect: pasos 1–4 OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/components/transmision-logica.js dashboard/components/transmision.js dashboard/styles/components/transmision.css scripts/probar_transmision_logica.js scripts/probar_transmision.py
git commit -m "feat(transmision): protagonista, triángulo y estela"
git tag step-04-protagonista
```

---

#### Paso 5 — Mini radar y «Alineaciones»

**Do**
1. Agregar a `transmision-logica.js`:
   | Función | Contrato |
   |---|---|
   | `puntosRadar(entradaCancha)` | Para `{"p": [[id, team, x, y], …], "b": [x, y] o null}` devuelve `{jugadores: [{id, team, x, y}], balon: {x, y} o null}`, mismo orden |
   | `filasFicha(ficha, partido)` | `[{codigo, color, texto}]`: primero el local y luego la visita, con `codigo` y `color` de `partido.local` / `partido.visita` y `texto = esquema + " · " + entrenador` de `ficha.local` / `ficha.visita` |
2. Casos nuevos (grupo del paso 5):
   - `puntosRadar({p: [[6, 1, 640, 310]], b: null})` deep-equal
     `{jugadores: [{id: 6, team: 1, x: 640, y: 310}], balon: null}`.
   - `puntosRadar({p: [], b: [578, 397]}).balon` deep-equal `{x: 578, y: 397}`.
   - Con `F = {local: {esquema: "3-4-2-1", entrenador: "Gustavo Alfaro"}, visita: {esquema: "5-4-1",
     entrenador: "Francisco Molina"}}` y `P = {local: {codigo: "CRC", color: "#00BFFF"}, visita:
     {codigo: "SKN", color: "#FF1493"}}`: `filasFicha(F, P)` deep-equal
     `[{codigo: "CRC", color: "#00BFFF", texto: "3-4-2-1 · Gustavo Alfaro"}, {codigo: "SKN", color: "#FF1493", texto: "5-4-1 · Francisco Molina"}]`.
3. En `transmision.js`:
   - ④ `#tv-radar`: un `<svg viewBox="0 0 1200 700">` con fondo `--color-pitch`, líneas de cancha
     `--color-pitch-lines` (borde, línea media, círculo central de radio 91.5, áreas de 165 × 403
     centradas en cada portería), un círculo de radio 12 por jugador del cuadro actual
     (`cancha[f]`) con el color de su equipo (`team` 2 → `--color-text-soft`) y el balón de radio 8 en
     `--color-ball`. Visible solo cuando `radar` es `true`.
   - ⑤ `#tv-ficha`: título «Alineaciones», una fila por elemento de `filasFicha(datos.ficha,
     datos.partido)` (código en su color y en `--font-headline`, esquema en `--font-mono`) y al pie
     `ficha.estadio + " · " + asistencia.toLocaleString("es") + " aficionados"` en
     `--color-text-soft`. Visible solo cuando `ficha` (de `graficosVisibles`) es `true`.
   - Estilos de ④ y ⑤ en `transmision.css` (§7).
4. `paso_5()` en `probar_transmision.py`: corre `node scripts/probar_transmision_logica.js --hasta 5`
   y `node --check` de los dos JS.

**Done when**
- [ ] WHEN `puntosRadar` recibe una entrada de `cancha` THE SYSTEM SHALL devolver los jugadores con `id`, `team`, `x`, `y` en el mismo orden.
- [ ] WHEN no hay balón en el cuadro THE SYSTEM SHALL devolver `balon: null`.
- [ ] WHEN `filasFicha` recibe la ficha y el partido THE SYSTEM SHALL devolver CRC «3-4-2-1 · Gustavo Alfaro» y luego SKN «5-4-1 · Francisco Molina».

**Verify**
```bash
node scripts/probar_transmision_logica.js --hasta 5                  # expect: OK <n> casos, exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 5     # expect: pasos 1–5 OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/components/transmision-logica.js dashboard/components/transmision.js dashboard/styles/components/transmision.css scripts/probar_transmision_logica.js scripts/probar_transmision.py
git commit -m "feat(transmision): mini radar y alineaciones"
git tag step-05-radar-alineaciones
```

---

#### Paso 6 — Voz de MATEO

**Do**
1. Agregar a `transmision-logica.js`:
   | Función | Contrato |
   |---|---|
   | `textoMateo(texto)` | Quita un prefijo `^\[W\d+\]\s*` y recorta espacios; sin prefijo, solo recorta |
   | `ajusteVoz(tVideo, tVoz)` | Si `Math.abs(tVideo - tVoz) > 0.3` devuelve `tVideo`; si no, `null` |
   | `fraseEn(t, jugadas)` | `textoMateo(jugadas[i].texto)` con `i = jugadaEn(t, jugadas)`; `""` si `i === -1` |
2. Casos nuevos (grupo del paso 6):
   - `textoMateo("[W0] San Cristóbal y Nieves presiona") === "San Cristóbal y Nieves presiona"`;
     `textoMateo("  Sin prefijo ") === "Sin prefijo"`.
   - `ajusteVoz(10, 10.2) === null`; `ajusteVoz(10, 10.5) === 10`.
   - `fraseEn(1, [{t0: 0, t1: 4.5, texto: "[W0] Hola"}]) === "Hola"`; `fraseEn(-1, []) === ""`.
3. En `transmision.js`:
   - `#tv-voz.src = narracion.audio`. El video suena al 25 % (`volume = 0.25`) como ambiente cuando
     la voz está activa, y al 100 % cuando no.
   - Al reproducir, pausar o repetir el video, hacer lo mismo con `#tv-voz`. En cada cuadro, si
     `ajusteVoz(video.currentTime, voz.currentTime)` no es `null`, asignar ese valor a `voz.currentTime`.
   - ⑦ `#tv-mateo` (con `aria-live="polite"`): la palabra «MATEO» en `--color-ball` y
     `fraseEn(t, jugadas)`. Solo se reescribe el texto cuando cambia la frase. Visible mientras haya
     frase y la voz esté activa.
   - `#tv-voz-toggle` (`aria-pressed`): «Voz de MATEO: sí/no». Al apagarla: `voz.muted = true`, oculta
     ⑦ y sube el video al 100 %.
   - Estilos de ⑦ en `transmision.css` (§7).
4. `paso_6()` en `probar_transmision.py`: corre `node scripts/probar_transmision_logica.js --hasta 6`,
   `node --check` de los dos JS, y verifica que el HTML de `transmision.html` contiene
   `aria-live="polite"` dentro del elemento `tv-mateo` (el atributo ya lo puso el paso 3, según §6;
   este paso no modifica el HTML).

**Done when**
- [ ] WHEN el subtítulo trae el prefijo `[W0]` THE SYSTEM SHALL mostrar la frase sin el prefijo.
- [ ] WHEN el desfase entre video y voz supera 0.3 s THE SYSTEM SHALL devolver la posición del video para reajustar la voz.
- [ ] WHEN el desfase es de 0.2 s THE SYSTEM SHALL no reajustar (`null`).
- [ ] WHEN se revisa la página THE SYSTEM SHALL tener `aria-live="polite"` en `#tv-mateo`.

**Verify**
```bash
node scripts/probar_transmision_logica.js --hasta 6                  # expect: OK <n> casos, exit 0
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 6     # expect: pasos 1–6 OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/components/transmision-logica.js dashboard/components/transmision.js dashboard/styles/components/transmision.css scripts/probar_transmision_logica.js scripts/probar_transmision.py
git commit -m "feat(transmision): franja y voz de MATEO sincronizada"
git tag step-06-voz-mateo
```

---

#### Paso 7 — Menú y regresión

**Do**
1. En `dashboard/components/site-nav.js`, agregar `['Transmisión', 'transmision.html']` al final de
   `LINKS`. Nada más cambia en ese archivo.
2. `paso_7()` en `probar_transmision.py`:
   - `site-nav.js` contiene `['Transmisión', 'transmision.html']` y las 4 entradas originales en el
     mismo orden (`Inicio`, `MATEO`, `Partido`, `Método`).
   - Con el servidor levantado: `GET` 200 a `/pages/index.html`, `/pages/mateo.html`,
     `/pages/partido.html`, `/pages/metodo.html`, `/pages/operaciones.html`, `/pages/opinion.html` y
     `/pages/transmision.html`.
   - `git diff --quiet step-01-exportar-datos -- dashboard/serve.py dashboard/data/mateo_data.json`
     sale 0 (no se tocaron).
   - Correr `scripts/probar_modo_prueba.py` con `sys.executable`; sale 0.

**Done when**
- [ ] WHEN se carga cualquier página THE SYSTEM SHALL mostrar «Transmisión» como quinta entrada del menú.
- [ ] WHEN se piden las 6 páginas existentes y la nueva THE SYSTEM SHALL responder 200 a cada una.
- [ ] WHEN se compara con el paso 1 THE SYSTEM SHALL no tener cambios en `serve.py` ni en `mateo_data.json`.
- [ ] WHEN se corre `probar_modo_prueba.py` THE SYSTEM SHALL pasar sus 15 casos.

**Verify**
```bash
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 7     # expect: pasos 1–7 OK, exit 0
.venv/Scripts/python.exe scripts/probar_modo_prueba.py              # expect: 15 casos OK, exit 0
```

**Checkpoint**
```bash
git add dashboard/components/site-nav.js scripts/probar_transmision.py
git commit -m "feat(transmision): Transmisión en el menú"
git tag step-07-menu-regresion
```

---

### 9.1 Paridad y transición
NOT APPLICABLE — no es una migración: la página es nueva y no reemplaza nada.

---

## 10. Preparación del entorno

### Requisitos previos
- Esta misma PC, con el repo en `C:\Users\Dell G3\Documents\omnimorph-pruebas`.
- `.venv` con pandas y pyarrow (ya instalados).
- Node ≥ 18 en el PATH (hoy v21.6.2).
- Git Bash.

### Cuentas a crear primero
NOT APPLICABLE — no hace falta ninguna cuenta.

### Variables de entorno
NOT APPLICABLE — el cambio no lee variables de entorno. El `.env` de watsonx no se toca.

### Archivos que deben estar presentes (no se suben a git)
| Archivo | Lo usa |
|---|---|
| `data/clean/objects_cleaned.parquet` | paso 1 |
| `dashboard/media/ORIGINAL_HP3zxNuoWXE-720-15.mp4` | paso 3 |
| `dashboard/media/NARRACION_COMPLETA_60S.wav` | paso 6 |

### Bootstrap
Se puede correr dos veces seguidas; la segunda también sale 0.
```bash
set -e
cd "/c/Users/Dell G3/Documents/omnimorph-pruebas"
test "$(git branch --show-current)" = feat-costa-rica   # misma carpeta y rama que Claude y Gemini; no cambiar de rama
test -f data/clean/objects_cleaned.parquet
test -f dashboard/data/mateo_data.json
test -f dashboard/data/partido/partido.json
test -f dashboard/media/ORIGINAL_HP3zxNuoWXE-720-15.mp4
test -f dashboard/media/NARRACION_COMPLETA_60S.wav
.venv/Scripts/python.exe -c "import pandas, pyarrow; print('pandas', pandas.__version__)"
node --version
```

---

## 11. Dependencias

No se instala nada. Origen de cada versión:

| Paquete | Versión | Fuente | Fecha |
|---|---|---|---|
| Python | 3.12.2 | `.venv/Scripts/python.exe --version` en esta PC | 2026-11-21 |
| pandas | 2.3.3 | `requirements-dashboard.txt` del repo (sin cambio) | 2026-11-21 |
| pyarrow | la instalada en `.venv` (sin cambio) | entorno local, no verificada contra PyPI porque no se fija ni se actualiza | 2026-11-21 |
| Node | v21.6.2 (sirve cualquiera ≥ 18) | `node --version` en esta PC | 2026-11-21 |

### Tiempo de ejecución
Ninguna dependencia nueva en el navegador.

### Desarrollo
Ninguna. Las pruebas usan `node:assert/strict` y la biblioteca estándar de Python.

### Deliberadamente no usados
| No se usa | Por qué |
|---|---|
| Frameworks de UI (React, etc.) | El dashboard es HTML/JS sin compilación |
| Librerías de gráficos | Un SVG simple basta para la estela y el radar |
| Playwright / pruebas de navegador | No están instaladas; la revisión visual va en la lista de lanzamiento (§20.1) |

---

## 12. Estrategia de despliegue

### Hosting
El mismo de hoy: `dashboard/serve.py` en esta PC, con túnel de Cloudflare cuando hay ronda de prueba.

### Ambientes
Local (`python dashboard/serve.py --port 8600`) y prueba con túnel.

### CI/CD
NOT APPLICABLE — el repo no tiene CI.

### Lanzamiento y vuelta atrás
- Lanzamiento: los commits van a `feat-costa-rica` (la rama compartida del repo, sin cambiar de rama
  ni hacer `stash`), y el push lo aprueba el usuario.
- Vuelta atrás rápida: quitar la entrada de `LINKS` en `site-nav.js` oculta la página del menú.
- Vuelta atrás completa: `git revert --no-edit` de los 7 commits, del más nuevo al más viejo.

### Dominio, DNS, TLS
NOT APPLICABLE — el túnel de Cloudflare da la URL y el TLS.

---

## 13. Estrategia de pruebas

| Capa | Herramienta | Qué cubre |
|---|---|---|
| Datos | `scripts/probar_transmision.py` paso 1 | contrato de §4, determinismo, protagonista, ficha, etiquetas y ausencia de velocidades |
| Lógica | `scripts/probar_transmision_logica.js` | todas las funciones de `transmision-logica.js` con casos literales |
| Servidor y archivos | `probar_transmision.py` pasos 3 y 7 | que la página y sus archivos se sirvan, y que las demás páginas sigan en 200 |
| Regresión del modo prueba | `scripts/probar_modo_prueba.py` | los 15 casos existentes |

### Flujos críticos E2E
La reproducción con video, voz y gráficos se revisa a mano (§20.1), porque no hay navegador
automatizado instalado.

### Datos de prueba
Los datos reales del clip activo. Los casos de lógica usan fixtures literales dentro del archivo de
prueba.

### Lo que no se prueba a propósito
El aspecto visual exacto y la sincronía percibida; van a la lista de lanzamiento.

---

## 14. Seguridad y secretos

- No se lee ni escribe ningún secreto. No se toca `.env`.
- `transmision.json` solo contiene datos ya publicados en `mateo_data.json` y cajas de video. Ningún
  dato personal más allá de apellidos y dorsales públicos de una transmisión oficial.
- Los textos se insertan con `textContent`, nunca con `innerHTML`.

---

## 15. Accesibilidad

### Requisitos base
- Los controles son `<button>` con texto visible; `#tv-voz-toggle` usa `aria-pressed`.
- `#tv-mateo` con `aria-live="polite"`: un lector de pantalla oye la narración como texto.
- `video` con `aria-label="Transmisión del partido Costa Rica vs. San Cristóbal y Nieves"`.
- El radar lleva `role="img"` y `aria-label="Mini radar con la posición de los jugadores"`.
- Contraste: texto `--color-text` sobre fondo `--color-bg` al 88 %.

### Adiciones de WCAG 2.2
- Foco visible en los botones (el estilo de `pill-button.css`).
- `prefers-reduced-motion`: sin transiciones.
- La barra espaciadora pausa (2.1.1 teclado).

### Verificación
Se revisa a mano en la lista de lanzamiento (§20.1).

---

## 16. Observabilidad y costo

### Instrumentación
Ninguna nueva. El registro de `serve.py` ya muestra quién pide `transmision.html`.

### Métricas que importan
Visitas a `/pages/transmision.html` en el registro durante una ronda de prueba.

### Health check
NOT APPLICABLE — no hay servicio nuevo.

### Modelo de costo
Costo cero: sin llamadas a watsonx ni a ningún servicio.

---

## 17. Enrutamiento de modelos

NOT APPLICABLE — la página no llama a ningún modelo. Reutiliza las narraciones de Granite
(`ibm/granite-4-h-small`) ya guardadas en `mateo_data.json`.

---

## 18. Skills para usar durante la construcción

NOT APPLICABLE — el cambio no necesita ninguna skill. El blueprint es autosuficiente y el estilo
sale de `dashboard/DESIGN.md`.

---

## 19. Espacio de trabajo del agente

El repo ya tiene `AGENTS.md`. **Bob agrega el bloque de §19.2 al final de `AGENTS.md`**, sin borrar
nada. El `CLAUDE.md` de §19.1 es nuevo en la raíz. No se crea `.claude/commands/`.

### 19.1 `CLAUDE.md`
```markdown
# CLAUDE.md — Omnimorph

Las reglas del proyecto están en `AGENTS.md`. Léelas primero; mandan sobre este archivo.

## Trabajo en curso: página Transmisión
- Blueprint: `blueprints/transmision-blueprint.md`. Sigue su §9 paso por paso.
- Comandos desde la raíz del repo, en Git Bash.
- Pruebas: `.venv/Scripts/python.exe scripts/probar_transmision.py --hasta N` y
  `node scripts/probar_transmision_logica.js --hasta N`.
- Antes de cada commit, muestra al usuario lo que vas a subir y espera su aprobación.
  Usa rutas explícitas en `git add`, nunca `git add -A`.
- No toques `dashboard/serve.py`, `dashboard/data/mateo_data.json` ni las otras páginas.
- Estilo: solo variables de `dashboard/styles/tokens.css`; sin sombras ni degradados (`dashboard/DESIGN.md`).
- Escribe en español.
```

### 19.2 Bloque para agregar a `AGENTS.md`
```markdown
---

## 9. Página Transmisión (2026-11-21)

- Blueprint: `blueprints/transmision-blueprint.md` (lo diseñó Claude; lo construye Bob).
- Datos: `scripts/export_transmision.py` → `dashboard/data/transmision.json`. No llama a ningún LLM.
- Pruebas: `scripts/probar_transmision.py --hasta 7` y `scripts/probar_transmision_logica.js`.
- Al terminar, registrar la sesión en `bob_sessions/` (regla 8.B).
```

### 19.3 `.claude/settings.json`
El repo no tiene `.claude/settings.json` versionado. Si Bob corre en Claude Code, usar este:
```json
{
  "permissions": {
    "allow": [
      "Bash(.venv/Scripts/python.exe scripts/export_transmision.py*)",
      "Bash(.venv/Scripts/python.exe scripts/probar_transmision.py*)",
      "Bash(.venv/Scripts/python.exe scripts/probar_modo_prueba.py*)",
      "Bash(node scripts/probar_transmision_logica.js*)",
      "Bash(node --check *)",
      "Bash(node --version)",
      "Bash(git status*)",
      "Bash(git diff*)",
      "Bash(git rev-parse*)",
      "Bash(git branch --show-current)",
      "Bash(test *)",
      "Bash(status=0*)",
      "Bash(for t in step-*)",
      "Bash(mv data/clean/objects_cleaned.parquet*)"
    ]
  }
}
```
`git add`, `git commit` y `git tag` quedan fuera a propósito: el usuario aprueba cada commit.

### 19.4 Skills del proyecto
NOT APPLICABLE — no hace falta un flujo repetible nuevo; las pruebas son dos comandos.

### 19.5 `.claude/rules/*.md`
NOT APPLICABLE — las reglas caben en §19.1.

### 19.6 Configuración crítica para las verificaciones
NOT APPLICABLE — las verificaciones no necesitan archivos de configuración: Python y Node corren
scripts directos, y no hay runner de pruebas, linter ni formateador en el repo.

---

## 20. Puerta de aceptación, riesgos y decisiones

### 20.1 Puerta de aceptación global
```bash
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 7     # expect: pasos 1–7 OK, exit 0
node scripts/probar_transmision_logica.js --hasta 7                  # expect: OK <n> casos, exit 0
.venv/Scripts/python.exe scripts/probar_modo_prueba.py              # expect: 15 casos OK, exit 0
for t in step-01-exportar-datos step-02-logica-base step-03-pagina-base step-04-protagonista step-05-radar-alineaciones step-06-voz-mateo step-07-menu-regresion; do git rev-parse --verify --quiet "refs/tags/$t" >/dev/null; done   # expect: los 7 tags existen, exit 0
```

**Lista de lanzamiento (a mano, después de la construcción):**
- [ ] Abrir `http://localhost:8600/pages/transmision.html`, pulsar «Ver transmisión» y ver los 36 s
      completos sin errores en la consola del navegador.
- [ ] El reloj va de 01:03 a 01:39 y el marcador dice CRC 0-0 SKN.
- [ ] En cada jugada aparecen y se van el protagonista con su triángulo y estela, y alternan el radar y «Alineaciones». Debajo del video se lee que la velocidad está en pruebas.
- [ ] La voz de MATEO coincide con la franja y el botón la apaga.
- [ ] Captura en escritorio y en celular (ancho 375 px) para el equipo.
- [ ] Claude revisa las capturas contra el boceto y `DESIGN.md`.

### 20.2 Registro de riesgos
| Riesgo | Señal | Mitigación |
|---|---|---|
| La velocidad del tracker no es confiable (la calibración salta en cada cuadro) | Cifras infladas o topadas | No se muestra; la página dice que está en pruebas. Volver a medir cuando mejore la homografía |
| Solo 10 de 46 jugadores tienen nombre | Muchas etiquetas «Jugador CRC» | Es honesto; el protagonista suele ser un jugador identificado. Mejorar la identificación es otro trabajo |
| El protagonista es el más cercano al balón, no necesariamente quien lo tiene | En 6 de 8 jugadas sale el mismo jugador (id 1, Rogers) | Es la regla v1, explicable. Con la posesión fiable se puede cambiar |
| La voz se desfasa del video | Frase y jugada no coinciden | Reajuste si el desfase pasa de 0.3 s (paso 6) |
| El navegador bloquea el audio | Silencio al cargar | Botón «Ver transmisión» obligatorio antes de reproducir |
| Derechos del video de la transmisión | Uso público del material | Solo para demos privadas con el equipo, IBM o clientes; para material público, video propio |

### 20.3 Registro de decisiones
| Decisión | Por qué | Se revertiría si |
|---|---|---|
| Script de export aparte en vez de ampliar `export_dashboard_data.py` | No arriesgar el export que alimenta MATEO | Se unifica el pipeline de exportación |
| Lógica pura en `transmision-logica.js` probada con Node | Gates reales sin navegador | Se instala un runner de navegador (Playwright) |
| Protagonista = el más cercano al balón en más cuadros de la jugada | Usa solo cajas en pantalla y la detección del balón (860 de 1080 cuadros), que son fiables | Hay detección fiable de posesión |
| Sin km/h en la v1, con la nota «está en pruebas» | Decisión del usuario (2026-11-21), tras ver que incluso filtradas las cifras salen infladas (~11 km/h trotando) | La homografía mejora y una prueba muestra ritmos de fútbol creíbles (~7 km/h trotando) |
| Radar y «Alineaciones» alternan por jugada | Pantalla limpia, inmersiva | El equipo pide verlos juntos |
| Reloj desde 1:03 y marcador calculado de `partido.json` | Dato del usuario y datos validados por Fer | Cambia el clip |
| Nombre solo con certeza alta o media | No mostrar nombres dudosos | Se valida la identificación de todos |
| Nombre de la página «Transmisión» con subtítulo inmersivo | Cabe en el menú y dice lo que es | El equipo prefiere otro nombre |

### 20.4 Lo que sigue
1. Probarla con el equipo en la siguiente ronda.
2. Versión con otro clip (la final del Mundial) para la venta a TV.
3. Idea 1: videos amateur, en su propio blueprint.
