# Comparativa de evaluaciones — 2026-11-14

Commit evaluado por los tres: `8d60ee5`. Guía: `GUIA_EVALUACION.md`.
Informes: `2026-11-14_claude.md` (navegador), `2026-11-14_gemini.md` (navegador), `2026-11-14_bob.md` (sin navegador: leyó HTML/CSS/JSON y llamó a `/api/chat`).

## 1. Puntuaciones

| Dimensión | Claude | Gemini | Bob | Comentario |
|---|---|---|---|---|
| A. Propuesta de valor | 4 | 3 | 4 | Coinciden: «Analizar mi partido» promete subir tu video |
| B. Claridad no técnicos | 2 | 3 | 4 | Bob no vio la jerga en pantalla (video quemado, pie de Mateo, chat) |
| C. Utilidad táctica | 3 | 4 | 3 | Partido es lo más fuerte para los tres |
| D. Confianza en los datos | 3 | 4 | **5** | El 5 de Bob no es coherente: él mismo encontró 2 PASS falsos |
| E. Chat | 2 | 4 | 3 | Mismo resultado de fondo; Gemini tuvo suerte en la 9 |
| F. Rendimiento | 4 | 3 | **5** | Bob no pudo medirlo sin navegador |
| G. Móvil | 4 | **2** | 4 (est.) | El 2 de Gemini sale de un desbordamiento que no se reproduce (ver 3) |
| H. Listo para demo | 3 | 3 | 3 | **Unánime:** «la enseñaría con avisos» |
| **Media** | **3.1** | **3.25** | **3.9** | Corrigiendo D/F de Bob y G de Gemini, los tres quedan en ~3.2–3.4 |

## 2. Chat: las 11 preguntas

| # | Claude | Gemini | Bob | Conclusión |
|---|---|---|---|---|
| 1 Goles | ✔ | ◐ | ✔ | Bien (Gemini fue estricto con «de cabeza») |
| 2 Mejor FotMob | ✔ | ✔ | ✔ | Bien |
| 3 Duelos SKN | ✘ PASS | ✘ PASS | ✘ PASS | **Falla siempre:** «Burley 5» en vez de Sawyers 7 |
| 4 Presión CRC | ✘ PASS | ✘ PASS | ◐ PASS | **Falla siempre:** «presión media» y cifras de SKN atribuidas a CRC |
| 5 Tiros por tiempo | ✔ regla | ✔ regla | ✔ regla | Bien |
| 6 Tarjetas | ✔ regla | ✔ regla | ✔ regla | Bien (todavía dice «ESPN/TM») |
| 7 «¿y de Costa Rica?» | ✔ regla | ✔ regla | ✔ regla | Bien |
| 8 Km de Galo | ✔ regla | ✔ regla | ✔ regla | Bien |
| 9 Qué corregir SKN | ✘ PASS | ✔ BLOQUEADA | ✘ PASS | **Inventa recomendaciones**; el bloqueo en Gemini fue suerte, no regla |
| 10 Portero Real Madrid | ✔ | ✔ | ◐ | Dice que no, pero gasta Granite (~16 000 tokens) |
| 11 Código Python | ✔ regla | ✔ regla | ✔ regla | Bien |

**Las reglas acertaron 6 de 6 en las tres pruebas. Todos los fallos son de Granite y todos salieron como PASS.**

## 3. Hallazgos revisados contra el código y el navegador

| Hallazgo | Quién | Verificación | Veredicto |
|---|---|---|---|
| Partido se desborda a 845 px en móvil | Gemini | En el navegador de Claude Code a 375×812: `scrollWidth = 375` en todas las pestañas; las 5 pestañas se envuelven en dos líneas; las tablas anchas de Comparativa y Goles se desplazan dentro de su propia caja | **Descartado** (lo más probable es que su navegador estrechó la ventana sin emular el móvil) |
| Pestaña Eventos oculta con `hidden` | Bob | `partido.js:263` la añade a las pestañas cuando hay eventos; se ve «Eventos (30)» | **Descartado** (Bob leyó el HTML sin ejecutar el JS) |
| El servidor se cayó con ERR_CONNECTION_REFUSED | Gemini | `serve.py` usa `ThreadingHTTPServer` y atrapa los cortes de conexión del video (`serve.py:459`); no se reprodujo | **No reproducido**: vigilar en el ensayo |
| 3-4-2-1 en Ficha y 3-4-3 en Fichero | Gemini | `partido.json` tiene los dos y una `esquema_nota` (FIFA/ESPN vs. FotMob) que la pestaña Fichero no muestra | **Válido** (menor) |
| Crónica del clip dice «domina la posesión» | Claude | — | Válido; solo lo vio Claude |

## 4. Lista única de mejoras

Prioridad por gravedad y por cuántos agentes lo vieron.

### Antes de la demo con un club

1. **CRÍTICO (3/3): rankings de jugadores por regla.** «¿Quién ganó más duelos/pases/entradas?» se responde ordenando los datos, sin Granite. El verificador también debe revisar que cada cifra sea del **equipo** y del **jugador** correctos, no solo que el número exista. (Preguntas 3 y 4)
2. **CRÍTICO (3/3): táctica y recomendaciones por regla.** «¿Cómo presionó…?» → cita la lectura de Fer marcada como tal, con las entradas 5 (1T) y 15 (2T). «¿Qué debería corregir…?» → «No doy recomendaciones; esto muestran los datos» + Fer. (Preguntas 4 y 9)
3. **IMPORTANTE (3/3): rechazar por regla a los equipos y jugadores que no son de este partido**, sin mandar ~16 000 tokens a Granite. (Pregunta 10)
4. **IMPORTANTE (2/3): botón «Analizar mi partido» → «Ver partido de muestra»** o una línea que explique que es una demo.
5. **IMPORTANTE (2/3): quitar la jerga de la vista del club.** En Inicio y Mateo: «Savitzky-Golay», «Block height», «W0–W7», «Frame», «M2.x», «POST-MATH». En el chat: esconder ms/tokens detrás de «Ver trazabilidad». Mover Operaciones al pie o a Método.
6. **IMPORTANTE (1/3): crónica de Mateo sin «posesión» ni «domina»** y con «en estos 36 s del minuto 1».
7. **MENOR: incoherencias que un analista nota.** 4 s vs. 4,5 s; «2026» vs. «2024»; 3-4-3 vs. 3-4-2-1 (mostrar la nota de fuentes); enlace «Equipo» a `#`; «ESPN/TM» en las tarjetas del chat.
8. **Operativo:** limpiar `chat_audit.jsonl` antes de la demo y ensayar 10 min de uso continuo para descartar la caída del servidor.

### Después de la demo

9. Top de jugadores de Mateo con los identificados primero, sin «Rastro N» (Claude).
10. Filtros por tipo en Eventos (Gemini).
11. Cuadro del chat de una línea sin barra de desplazamiento (Gemini).
12. Mensaje de espera de la crónica si `mateo_data.json` tarda (Bob).

### Decisión del equipo

- **Titular «¡Que no te lo cuente tu cuñado!»:** a Claude y a Bob les funciona; a Gemini le parece de aficionado frente a un club profesional. Una opción es mantenerlo en la versión pública y usar un subtítulo serio en la demo con el club.

## 5. Sobre los evaluadores

- **Claude y Gemini** recorrieron la app en el navegador; sus notas de B, F y G son de lo que vieron.
- **Bob** no tenía navegador: su chat es válido, pero B, F y G salen de leer el código, y por eso tienen dos errores (Eventos «oculta» y F = 5 sin medir). Para la próxima ronda, Bob debería usar un navegador o no puntuar F y G.
