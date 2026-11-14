# Revisión de la fase 1 (chat confiable) — Claude Code

- **Revisado:** cambios sin commit de IBM Bob en `implementacion/cloud_agent/chat_agent.py` y `scripts/probar_chat_reglas.py` (sesión 30)
- **Encargo original:** `blueprints/fase1_chat_confiable.md`
- **Veredicto:** **casi listo, todavía no se hace commit.** Las 4 preguntas que fallaban ya salen bien por regla. Brasil sigue funcionando y no se tocó nada fuera del alcance. Pero hay **3 regresiones**: preguntas que antes iban bien a Granite ahora reciben una respuesta equivocada por regla. Además, la prueba de Brasil del script no prueba nada.

## Lo que está bien
- P3, P4, P9 y P10 por regla, con las cifras correctas. Los empates funcionan (Cascante y Calvo, 9).
- Las tarjetas salen sin «ESPN/TM» ni «Transfermarkt», y el JSON de Fer no se tocó.
- Orden de las reglas correcto: recomendación antes que táctica.
- No se tocaron el verificador, el `SYSTEM_PROMPT` ni `dashboard/`, y no hay commit.
- Comprobado en un proceso aparte con `OMNIMORPH_PARTIDO=brasil_alemania_2014`: «¿Cómo jugó Brasil?», «¿Brasil presionó alto?» y «¿Qué jugador de Alemania ganó más duelos?» siguen yendo a Granite, como antes. Brasil no se rechaza como equipo ajeno.

## Hay que corregir

### R1 — «usa» está en la lista de ajenos (regresión grave)
- `_AJENOS` incluye `"usa"`, que en español también es un verbo.
- **Resultado:** «¿Qué esquema **usa** Costa Rica?» se rechaza como fuera de tema. Antes iba a Granite.
- **Corrección:** quitar `"usa"` y revisar la lista entera en busca de palabras comunes del español o apellidos frecuentes, como `"inter"`, `"leon"`, `"juarez"`, `"roma"`, `"gales"`, `"atlas"` y `"puebla"`. Para siglas y ciudades, exigir que vayan junto a un contexto de club («el León», «del Inter») o quitarlas.
- Quitar también los duplicados (`"alemania"`, `"mazatlan"`).

### R2 — Una pregunta sobre equipos se responde con un ranking de jugadores (regresión)
- «¿Qué **equipo** tuvo más tiros?» responde «Orlando Galo: 5 tiros totales». Antes iba a Granite.
- **Corrección:** `respuesta_ranking` devuelve `None` si la pregunta habla de equipos («qué equipo», «cuál equipo», «quién tuvo más posesión»…). Solo responde cuando pregunta por un jugador: «quién», «qué jugador», «cuál jugador».

### R3 — Superlativos que no son rankings de jugadores (regresión)
- «¿Cuál fue el **mejor gol**?» responde «Orlando Galo: 2 goles». Antes iba a Granite.
- **Causa:** la segunda alternativa de `RE_RANKING` (`mas|mejor … gol`) no exige que se pregunte por un jugador.
- **Corrección:** quitar esa alternativa y exigir «quién / qué jugador / cuál jugador». «Mejor gol», «mejor jugada» y «mejor momento» van a Granite.

### R4 — Táctica de un jugador respondida con la del equipo
- «¿Cómo **jugó Galo**?» devuelve el esquema inicial de Costa Rica, que no habla de Galo.
- **Corrección:** quitar `jugo`/`jugar` de los disparadores de `RE_TACTICA`. Si la pregunta nombra a un jugador (`hechos["alias_jugadores"]`) y no nombra un concepto táctico de la tabla, devolver `None`.

### R5 — La prueba de Brasil del script no prueba nada
- Las filas 20–22 muestran «Romaine Sawyers…» y «Lectura táctica…» marcadas como OK. O sea, se cargaron los datos de Costa Rica, no los de Brasil. Cambiar la variable de entorno dentro del mismo proceso no recarga el partido.
- **Corrección:** el script debe lanzar **un subproceso** con `OMNIMORPH_PARTIDO=brasil_alemania_2014` (`subprocess.run([sys.executable, __file__, "--brasil"], env=…)`). En ese modo comprueba que:
  - ninguna respuesta contenga «Costa Rica», «Sawyers» ni «Galo»;
  - «¿Cómo jugó Brasil?» no se rechace como fuera de tema.

### R6 — `grupo_b_integrantes` escrito a mano
- `cargar_datos()` lee `contexto_competitivo["grupo_b_integrantes"]`, que solo sirve para este partido.
- **Corrección:** tomar todas las listas de nombres de `contexto_competitivo`, sea cual sea su clave, o los nombres de equipo que aparezcan en todo `contexto_partido`.

### R7 — P9 sale como REVISAR (menor)
- La respuesta por regla de recomendaciones cita la conclusión de Fer, y el auditor marca como «sin respaldo» las cifras de ese texto.
- **Corrección:** comprobar por qué esas cifras no están en el contexto de la auditoría. Si son de Fer, la respuesta por regla debe auditarse con su propio texto como contexto (`origen="regla"`), para que salga PASS.
- No bloquea la demo.

## Casos nuevos para `probar_chat_reglas.py`

| Pregunta | Debe |
|---|---|
| ¿Qué esquema usa Costa Rica? | **No** fuera de tema |
| ¿Qué equipo tuvo más tiros? | `None` (Granite) o la comparativa de equipos; **nunca** un ranking de jugadores |
| ¿Cuál fue el mejor gol? | `None` |
| ¿Cómo jugó Galo? | `None` |
| ¿Quién marcó más goles? | Ranking: Galo 2 |
| ¿Qué jugador de Costa Rica tuvo más posesión? | `None` (la métrica no existe por jugador) |
| ¿Quién es el portero del Inter? | Fuera de tema |
| [Brasil, subproceso] ¿Cómo jugó Brasil? | **No** fuera de tema y sin «Costa Rica» |
| [Brasil, subproceso] ¿Qué debería corregir Brasil? | «No doy recomendaciones», sin «Costa Rica» |

## Para cerrar
1. Bob corrige R1–R6 (R7 si alcanza), amplía el script y lo corre: todo en OK.
2. Bob agrega una sección «Correcciones tras la revisión» a `bob_sessions/sesion_30_fase1_chat_confiable.md`.
3. Claude vuelve a revisar. Si todo cuadra, se propone el commit de la fase 1.

---

## Segunda revisión (después de las correcciones de Bob)

**Veredicto: aprobado para commit.** R1–R7 corregidas. Comprobado por Claude: el script da 29/29 OK (exit 0), la prueba de Brasil ahora corre en un subproceso de verdad, y ninguna de las regresiones de la primera revisión se reproduce.

Decisión de Bob que se acepta: «América», «Inter» a secas, «Barcelona» a secas, «México» y «Panamá» ya no se rechazan por regla, porque son homónimos o vecinos de Concacaf. Esas preguntas van a Granite, que ya respondía «no tengo información». Cuestan tokens, pero no inventan.

### Pendientes menores (fase 1b, antes de compartir con el equipo)
| ID | Pregunta | Ahora | Debe |
|---|---|---|---|
| R8 | ¿Qué jugador tuvo más entradas **en el segundo tiempo**? | Da el total del partido (Mitchell 5) como si fuera del 2T | `None` o «No hay datos por jugador separados por tiempo» si la pregunta nombra un tiempo |
| R9 | ¿Qué jugador de SKN tuvo mejor **precisión de pases**? | Terrell y Browne con 100 %, con muy pocos pases | Mínimo de pases intentados (por ejemplo, `pases_totales >= 15`) para entrar en el ranking de precisión, y decirlo |
| R10 | ¿**Irán** a la siguiente ronda? | Fuera de tema (lee «iran» como el país) | Quitar «iran» de `_AJENOS` o exigir «selección de Irán» |
| R11 | ¿Se **debe** confiar en estos datos? | Responde como recomendación | Limitar `debe\w*` a «debe/debería + corregir/mejorar/cambiar/hacer» |

Agregar estos 4 casos al script.
| R12 | ¿Cómo presionó **Costa Rica** después de perder el balón? | Añade también la viñeta «Postura sin balón de San Cristóbal y Nieves» (menciona «7 de Costa Rica» y por eso pasa el filtro) | Filtrar por el **sujeto** de la viñeta (el texto antes de los dos puntos), no por cualquier mención del equipo |
