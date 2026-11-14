# Plan de mejoras de Omnimorph — tras las evaluaciones del 2026-11-14

**Para qué es este documento:** reunir en un solo lugar todo lo que encontraron las tres evaluaciones (Claude Code, Gemini e IBM Bob), lo que comprobamos, y una propuesta de cómo implementarlo, para **leerlo y decidir** antes de tocar código.

- Rama: `feat-costa-rica` · Commit evaluado: `8d60ee5`
- Fuentes: `evaluaciones/2026-11-14_{claude,gemini,bob}.md`, `evaluaciones/2026-11-14_comparativa.md`, `bob_sessions/sesion_29_comparativa_evaluaciones.md`
- Estado: **propuesta, sin implementar.** Nada de esto tiene commit.

---

## 1. Resumen en 30 segundos

- Los tres evaluadores dicen lo mismo: **«la enseñaría al club, pero con avisos»** (H = 3/5). Media real, corrigiendo los errores de cada evaluador: **~3.3/5**.
- **El contenido ya está al nivel de un club** (Partido, Método y la honestidad sobre lo que no sabemos). **La presentación todavía parece de laboratorio** (jerga, Operaciones en el menú y un botón que promete algo que no hace).
- **El riesgo más grande es el chat con Granite.** Falla siempre en las mismas preguntas (3 y 4), inventa recomendaciones (9) y todo sale con el sello verde **PASS**. Las respuestas por regla acertaron 6 de 6 en las tres pruebas.
- **Propuesta:** 4 fases, cada una con su commit y tu aprobación. Las fases 1 y 2 van **antes de la demo con el club**.

---

## 2. Qué dijeron los evaluadores

### 2.1 Puntuaciones

| Dimensión | Claude | Gemini | Bob | Lectura |
|---|---|---|---|---|
| A. Propuesta de valor | 4 | 3 | 4 | El botón «Analizar mi partido» engaña |
| B. Claridad no técnicos | 2 | 3 | 4 | Bob no vio la jerga en pantalla |
| C. Utilidad táctica | 3 | 4 | 3 | Partido es lo más fuerte |
| D. Confianza en los datos | 3 | 4 | 5 | El 5 de Bob no es coherente con sus propios PASS falsos |
| E. Chat | 2 | 4 | 3 | Mismo fondo: Granite falla en 3 y 4 |
| F. Rendimiento | 4 | 3 | 5 | Bob no pudo medirlo |
| G. Móvil | 4 | 2 | 4 (est.) | El 2 de Gemini no se reproduce |
| H. Listo para la demo | 3 | 3 | 3 | **Unánime** |
| **Media** | 3.1 | 3.25 | 3.9 | Corregida: ~3.3 |

### 2.2 Chat: las 11 preguntas fijas

| # | Pregunta | Claude | Gemini | Bob | Origen |
|---|---|---|---|---|---|
| 1 | Goles y minutos | ✔ | ◐ | ✔ | Granite |
| 2 | Mejor según FotMob | ✔ | ✔ | ✔ | Granite |
| 3 | Más duelos de SKN | **✘ PASS** | **✘ PASS** | **✘ PASS** | Granite |
| 4 | Presión de CRC tras pérdida | **✘ PASS** | **✘ PASS** | ◐ PASS | Granite |
| 5 | Tiros por tiempo | ✔ | ✔ | ✔ | regla |
| 6 | Tarjetas | ✔ | ✔ | ✔ | regla |
| 7 | «¿y de Costa Rica?» | ✔ | ✔ | ✔ | regla |
| 8 | Km de Galo | ✔ | ✔ | ✔ | regla |
| 9 | Qué debe corregir SKN | **✘ PASS** | ✔ BLOQUEADA | **✘ PASS** | Granite |
| 10 | Portero del Real Madrid | ✔ | ✔ | ◐ | Granite (~16 000 tokens) |
| 11 | Código Python | ✔ | ✔ | ✔ | regla |

### 2.3 Hallazgos que comprobamos (para no arreglar lo que no está roto)

| Hallazgo | Quién | Resultado |
|---|---|---|
| Partido se desborda a 845 px en el móvil | Gemini | **Falso.** A 375×812 el ancho de la página es 375 en las 5 pestañas; las tablas anchas se desplazan dentro de su caja |
| Pestaña Eventos oculta | Bob | **Falso.** `partido.js:263` la muestra cuando hay eventos |
| El servidor se cayó | Gemini | **No reproducido.** `serve.py` usa `ThreadingHTTPServer` y atrapa los cortes del video. Vigilar en el ensayo |
| 3-4-2-1 en Ficha y 3-4-3 en Fichero | Gemini | **Cierto.** Los datos tienen una nota de fuentes que Fichero no muestra |

---

## 3. Por qué el chat da PASS a respuestas falsas (diagnóstico)

El verificador (`implementacion/cloud_agent/chat_agent.py:882` y `chat_verificador.py:325`) hace dos comprobaciones:

1. **¿Cada cifra existe en los datos?** (`numeros_sin_respaldo`). Ignora los enteros menores que 11.
2. **¿Cada cifra está atribuida al equipo o jugador correcto?** (`verificar_atribucion`), para las métricas que reconoce.

Eso explica cada fallo:

| Pregunta | Qué dijo Granite | Por qué pasó el verificador |
|---|---|---|
| 3 | «Burley, 5 duelos» | Burley **sí** ganó 5. El error es el superlativo («el que más»), y el verificador no comprueba superlativos. Además, 5 < 11 |
| 4 | «Presión media», «14 intercepciones de CRC» | La opinión táctica no tiene cifra que comprobar. El 14 sí existe (es de SKN). Hay que confirmar si «intercepciones» está entre las métricas que el verificador atribuye |
| 9 | 4–5 recomendaciones genéricas | No tiene cifras: no hay nada que el verificador pueda medir |
| 10 | «No tengo información…» | Está bien, pero «Real Madrid» no cae en el filtro de fuera de tema y la pregunta va a Granite con el contexto completo |

**Conclusión:** la solución no es «un verificador más listo» para todo, sino **quitarle a Granite los tipos de pregunta en los que no se puede verificar lo que dice** (rankings, táctica, recomendaciones y otros equipos) y responderlos por regla, como ya hacemos con tarjetas y tiros.

---

## 4. Catálogo de mejoras

Esfuerzo: **S** = menos de 1 h · **M** = medio día · **L** = un día o más.
Visto por: número de evaluadores que lo señalaron (de 3).

### Bloque A — Chat (confianza)

| ID | Mejora | Visto por | Cómo se implementa | Archivos | Esfuerzo | Cómo comprobamos |
|---|---|---|---|---|---|---|
| **A1** | **Rankings por regla**: «¿quién ganó más duelos / pases / entradas / tiros / toques…?» | 3/3 | Nueva `respuesta_ranking()` en `respuesta_por_regla`: detecta «más/menos + métrica + (equipo)», ordena `estadisticas_jugadores` y da el top 3 con fuente | `chat_agent.py` (+ diccionario de métricas por jugador) | M | P3 → «Sawyers 7 (Lewis 6, Burley 5)», origen regla |
| **A2** | **Táctica por regla con la lectura de Fer**: «¿cómo presionó / defendió / atacó…?» | 3/3 | Nueva `respuesta_tactica()`: busca el fragmento de Fer del tema, lo cita marcado «Lectura táctica del analista (Fer)» y añade las cifras de apoyo (entradas 5 en 1T y 15 en 2T). Sin Granite | `chat_agent.py` | M | P4 → acoso tras pérdida, más intenso en el 2T, cifras de CRC correctas |
| **A3** | **Recomendaciones por regla**: «¿qué debería corregir / mejorar / hacer…?» | 2/3 (+1 por suerte) | Responder: «No doy recomendaciones; esto es lo que muestran los datos» + 2–3 hechos + la lectura de Fer si existe | `chat_agent.py` | S | P9 → no inventa; origen regla |
| **A4** | **Otros equipos y jugadores fuera de tema, por regla** | 3/3 | Ampliar `fuera_de_tema`: si menciona un club o selección que no es CRC/SKN (lista corta de clubes y selecciones frecuentes) → rechazo directo | `chat_agent.py` | S | P10 → rechazo, 0 tokens |
| **A5** | **Sello visual distinto** para un dato verificado y para una lectura de la IA | 3/3 (indirecto) | En el chat: «✓ Dato verificado» (regla) y «Lectura de IA · contrástala» (Granite), aunque salga PASS | `chat-widget.js`, `chat.js` | S | Se ve la diferencia en P2 y P5 |
| **A6** | Quitar «(ESPN/TM)» y «Transfermarkt registra…» de las tarjetas del chat | 1/3 | Usar el mismo texto limpio que la página Partido | `chat_agent.py` (`respuesta_eventos`) | S | P6 sin esas marcas |
| A7 | Contexto más corto cuando no se reconoce el tema | 1/3 | Mandar solo ficha y resumen en lugar de todas las secciones | `chat_agent.py` (`seleccionar_secciones`) | S | Pregunta abierta < 6 000 tokens |

### Bloque B — Mensaje y lenguaje (primera impresión)

| ID | Mejora | Visto por | Cómo se implementa | Archivos | Esfuerzo |
|---|---|---|---|---|---|
| **B1** | Botón «Analizar mi partido» → «Ver partido de muestra» + una línea: «Para analizar el tuyo, contáctanos» | 2/3 | Texto | `pages/index.html:161` | S |
| **B2** | Titular «¡Que no te lo cuente tu cuñado!» | divide | **Decisión D1** (sección 6) | `pages/index.html:150` | S |
| **B3** | Jerga en Inicio: «Block height», «Savitzky-Golay», «Ventanas de 4 segundos» → «altura del bloque», «movimiento suavizado», «tramos de 4,5 s» | 2/3 | Texto | `pages/index.html:203-204` | S |
| **B4** | Jerga en Mateo: «W0–W7», «Frame N / 1079», «Pipeline 9/9 OK», «M1–M4», «Tokens in/out», «Latencia» → «Tramo 1–8», «segundo 12,3», y lo técnico detrás de un icono «i» | 2/3 | Texto + un `<details>` | `pages/mateo.html` | M |
| **B5** | Sacar **Operaciones** del menú principal → enlace al pie y desde Método | 2/3 | Menú | `components/site-nav.js` | S |
| **B6** | En el chat, «modelo · ms · tokens» detrás de «Ver trazabilidad» | 1/3 | Componente | `chat-widget.js` | S |

> El texto quemado en el video (`Frame 771/1080 [POST-MATH]`, `Moda M2.0`) solo se quita volviendo a renderizar el video. Propuesta: **no tocarlo antes de la demo**; la vista «Original» no lo tiene.

### Bloque C — Mateo (contenido)

| ID | Mejora | Visto por | Cómo se implementa | Archivos | Esfuerzo |
|---|---|---|---|---|---|
| **C1** | La crónica no puede decir «posesión» ni «domina» (el motor mide la posición del bloque, no la posesión) y debe acotar «en estos 36 s del minuto 1» | 1/3 | **Decisión D3**: (a) corregir el texto de las 8 ventanas a mano en los datos, sin Granite; o (b) prohibirlo en el prompt del narrador + regla en el M3 y regenerar (gasta RU) | `narrations.json` / `agent_narrator.py`, `governance_monitor_m3.py` | S (a) / M (b) |
| **C2** | Lista de jugadores: primero los identificados; el resto «Jugador de SKN sin identificar»; ocultar rastros con cambio de identidad | 2/3 | Orden y etiqueta | `pages/mateo.html:871,895` | S |
| C3 | Mensaje si la crónica no carga en 5 s (hoy se queda «Cargando narración…») | 1/3 | Temporizador → `#data-notice` | `pages/mateo.html:399` | S |

### Bloque D — Coherencia (lo que un analista nota)

| ID | Mejora | Archivos | Esfuerzo |
|---|---|---|---|
| D-a | «4 segundos» → «4,5 s» en Inicio (y revisar M2.4) | `index.html`, monitor M2.4 | S |
| D-b | «CRC vs SKN · 2026» en Mateo y «· 2024» en Partido → «2024 · Eliminatorias 2026» en los dos | `mateo.html`, `partido.js` | S |
| D-c | Esquema: mostrar «3-4-2-1 (FotMob) / 3-4-3 (FIFA, ESPN)» con la nota de fuentes en Ficha y Fichero | `fichero.js`, `partido.js` | S |
| D-d | Enlace «Equipo» del menú lleva a `#` → quitarlo o apuntar a una sección real | `site-nav.js` | S |
| D-e | «Radar cenital · 120 × 70 m» → «cancha de referencia» (el Estadio Nacional no mide eso) | `mateo.html` | S |

### Bloque E — Pulido (después de la demo)

| ID | Mejora | Visto por | Esfuerzo |
|---|---|---|---|
| E1 | Pantalla de carga (cubo) solo si la página tarda más de 300 ms | Gemini | S |
| E2 | Filtros en Eventos: Goles · Tarjetas · Cambios · Remates | Gemini | M |
| E3 | Cuadro del chat sin barra de desplazamiento y con un placeholder corto | Gemini | S |
| E4 | «Toca para ampliar» en los diagramas de Fer en el móvil | Claude | S |
| E5 | Volver a renderizar el video «Con marcas» sin texto técnico quemado | Gemini | L |

### Bloque F — Operación de la demo (sin código)

| ID | Acción |
|---|---|
| F1 | Vaciar o archivar `chat_audit.jsonl` antes de la demo (hoy se ven preguntas de prueba en Operaciones) |
| F2 | Ensayo de 10 min de uso continuo (video, cambio de páginas y chat) para descartar la caída del servidor |
| F3 | Recorrido de la demo: Inicio (10 s) → Partido (Ficha → Goles → Comparativa) → Mateo (video y radar) → Método («lo que no afirmamos») → chat solo con preguntas de datos |

---

## 5. Orden propuesto de implementación

Cada fase es **un commit**, que se enseña antes de hacerlo (regla del proyecto).

| Fase | Contenido | Antes de la demo | Esfuerzo total | Criterio para darla por buena |
|---|---|---|---|---|
| **1 · Chat confiable** | A1, A2, A3, A4, A6 | **Sí** | ~1 día | Las 11 preguntas: 11/11 correctas, ninguna respuesta falsa con PASS. P3, P4, P9 y P10 salen por regla. Pruebas del chat en verde |
| **2 · Primera impresión** | B1, B3, B5, B6, A5, D-a…D-e, C2 (+ B2 según D1) | **Sí** | ~medio día | Inicio y Mateo sin jerga visible; Operaciones fuera del menú; mismas cifras en todas las páginas; móvil a 375 px sin desbordes |
| **3 · Crónica y Mateo** | C1, C3, B4, A7 | Recomendado | medio día | La crónica no dice «posesión»; las etiquetas de Mateo en lenguaje de fútbol; M3 en PASS |
| **3.5 · Prueba con el equipo** | Levantar el servicio (decisión D7), guía corta de 20 min y formulario de retroalimentación | **Sí** | medio día | Al menos 3 personas del equipo la prueban; sus comentarios entran a este plan |
| **4 · Pulido** | E1–E5 + lo que salga de la prueba con el equipo | Según lo que salga | 1–2 días | Al gusto del equipo |
| — | F1–F3 | **Sí, el día anterior** | 30 min | Ensayo sin caídas |

**Opinión del equipo, en dos momentos:**
1. **Hoy:** el equipo lee este plan y opina sobre las decisiones D1–D7 (unos 15 min). No prueba la app todavía, para no gastar su tiempo en problemas que ya conocemos.
2. **Fase 3.5:** prueba la app ya corregida. Esa ronda funciona también como ensayo general antes del club.

### 5.1 Quién hace cada cosa

**Claude Code es el cerebro: no implementa.** Escribe cada encargo con criterios de aceptación, revisa el resultado contra esos criterios, corre las comprobaciones y propone el commit. Los demás agentes implementan.

| Fase | Implementa | Por qué |
|---|---|---|
| **1 · Chat confiable** | **IBM Bob** (modo 💻 Code) | Es lógica en Python con una comprobación automática que no necesita navegador (lo que Bob no tiene). Además suma al relato de IBM: el componente de IA lo corrige la herramienta de IBM |
| **2 · Primera impresión** | **Gemini** (Antigravity, modo agente con navegador) | Son textos, menú y CSS que hay que mirar en pantalla y en el móvil, y Gemini tiene navegador |
| **3 · Crónica y Mateo** | Bob: C1 (datos y regla del M3) y A7 · Gemini: B4 y C3 (pantalla) | Cada uno, lo de su terreno |
| **3.5 · Servicio para el equipo** | Bob (si es IBM Cloud Code Engine) o Gemini (si es un túnel) | Según D7 |
| **4 · Pulido** | Gemini | Casi todo es de pantalla |

**Flujo de cada fase:**
1. Claude escribe el encargo en `blueprints/fase<N>_<nombre>.md`.
2. El agente implementa **sin hacer commit** y registra su sesión en `bob_sessions/`.
3. Claude revisa los cambios, corre las comprobaciones y reporta.
4. Tú apruebas y se hace el commit.

**Regla:** dos agentes nunca trabajan a la vez sobre los mismos archivos. Las fases 1 y 2 sí pueden ir en paralelo, porque la 1 toca `implementacion/cloud_agent/` y la 2 toca `dashboard/`. La única excepción es A5, que toca el widget del chat y queda dentro de la fase 2.

**Cómo medimos la mejora:** al terminar las fases 1–3, repetir la evaluación con `GUIA_EVALUACION.md` (los tres agentes y las mismas 11 preguntas).
- **Meta:** chat 11/11 sin falsos PASS · B ≥ 4 · H ≥ 4 · media ≥ 4.
- **Cambio en la guía:** Bob debe usar navegador o no puntuar F y G.

---

## 6. Decisiones que necesitamos de ti / del equipo

| # | Decisión | Opciones | Recomendación |
|---|---|---|---|
| **D1** | Titular «¡Que no te lo cuente tu cuñado!» | (a) Mantenerlo · (b) Cambiarlo por uno profesional · (c) Mantenerlo y añadir un subtítulo serio («Análisis táctico de video para cuerpos técnicos») | **(c)**: conserva la personalidad y tranquiliza al club |
| **D2** | Qué hace Granite después de la fase 1 | (a) Solo redacta lo que no cubren las reglas, con el sello «Lectura de IA» · (b) Apagarlo en la demo y dejar solo las reglas | **(a)**: es el componente IBM que queremos enseñar, pero sin poder dar rankings, táctica ni recomendaciones |
| **D3** | Cómo corregir la crónica (C1) | (a) Editar a mano los 8 textos en los datos · (b) Prompt + regla en el M3 y regenerar | **(a) antes de la demo y (b) después**: (a) es inmediato y sin gasto; (b) es la solución de fondo |
| **D4** | Operaciones | (a) Pie de página · (b) Solo dentro de Método · (c) Quitarla en el modo demo | **(a)** |
| **D5** | Alcance antes de la demo | Fases 1+2 · Fases 1+2+3 | **1+2+3** si hay más de 2 días; si no, **1+2** |
| **D6** | ¿Quién implementa cada fase? | Claude Code, Bob o Gemini | **Decidido (2026-11-14):** Claude Code solo diseña y revisa; Bob la fase 1 y Gemini la 2 (ver 5.1) |
| **D7** | Dónde levantar el servicio para el equipo | (a) Túnel · (b) IBM Cloud Code Engine | **Decidido (2026-11-14):** túnel desde la PC del usuario (Cloudflare quick tunnel), prueba de **48 h** y **15 preguntas por persona** al chat. Encargo: `blueprints/fase3_5_modo_prueba.md` |

---

## 7. Fuera de alcance (por ahora)

- Subir el video propio del club («Analizar mi partido» de verdad): es otro producto.
- Distancias, velocidades y sprints por jugador: el motor no los valida todavía y Método ya lo explica.
- Rehacer el verificador para que entienda superlativos y opiniones: se resuelve sacando esas preguntas de Granite (fase 1).
- Rediseño visual: los tres evaluadores dicen que el diseño está cuidado.
