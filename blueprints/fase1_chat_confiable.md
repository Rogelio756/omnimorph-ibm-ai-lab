# Encargo — Fase 1: chat confiable

- **Implementa:** IBM Bob, modo 💻 Code
- **Diseña y revisa:** Claude Code
- **Rama:** `feat-costa-rica`
- **Plan general:** `evaluaciones/PLAN_MEJORAS_2026-11-14.md` (mejoras A1, A2, A3, A4 y A6)
- **Estado:** listo para empezar

---

## 1. Por qué

En las tres evaluaciones (Claude, Gemini y Bob), el chat se equivocó en las mismas preguntas y la respuesta salió con el sello verde **PASS**:

| Pregunta | Qué dijo Granite | Qué es lo correcto |
|---|---|---|
| P3. ¿Qué jugador de San Cristóbal ganó más duelos? | «Andre Burley, 5» | Romaine Sawyers 7 (Mervin Lewis 6, Burley 5) |
| P4. ¿Cómo presionó Costa Rica después de perder el balón? | «Presión media» y cifras de SKN atribuidas a CRC | Acoso inmediato tras pérdida, más intenso en el 2T (entradas: 5 en 1T y 15 en 2T). Es lectura de Fer |
| P9. ¿Qué debería corregir San Cristóbal para el próximo partido? | 4–5 recomendaciones inventadas | No dar recomendaciones propias |
| P10. ¿Quién es el portero del Real Madrid? | «No tengo información…», pero gastando ~16 000 tokens de Granite | Rechazo directo por regla, sin Granite |

**Por qué pasa:** el verificador (`chat_agent.py:auditar_respuesta` y `chat_verificador.py:verificar_atribucion`) solo comprueba que cada cifra exista en los datos y que esté atribuida a quien corresponde. No puede comprobar un superlativo («el que más»), ni una opinión táctica, ni una recomendación.

**La solución:** responder **por regla, sin Granite,** estos cuatro tipos de pregunta, igual que ya se hace con tarjetas, tiros y distancias. **No hay que tocar el verificador.**

---

## 2. Qué hay que hacer

Todo en `implementacion/cloud_agent/chat_agent.py`, dentro de `respuesta_por_regla()` (línea ~764). El orden de las reglas importa: van **después** de `fuera_de_tema` y **antes** de `respuesta_comparativa`.

### A4 — Otros equipos y jugadores, fuera de tema
- **Problema:** «¿Quién es el portero del Real Madrid?» pasa el filtro porque «portero» es vocabulario de fútbol.
- **Qué hacer:** en `fuera_de_tema()`, **antes** de revisar el vocabulario, detectar si la pregunta menciona un club o una selección que **no** es de este partido. Si es así, la pregunta está fuera de tema.
- **La lista de ajenos** va en una constante, con unos 40 nombres: clubes europeos grandes, clubes de la Liga MX y selecciones frecuentes, ya normalizados con `sin_acentos`.
- **Excepción:** no cuenta como ajeno un equipo que aparezca en los datos del partido. Por ejemplo, los rivales del grupo de `contexto_previo` (Trinidad y Tobago, Granada y Bahamas) están en los datos y no se rechazan.
- **Respuesta:** la que ya existe, `respuesta_fuera_de_tema(datos)`.

### A1 — Rankings de jugadores
- **Qué detectar:** preguntas del tipo «quién / qué jugador … más / menos / mayor / mejor / peor + métrica», con equipo opcional.
- **Datos:** la lista `rendimiento_individual_destacado` de `estadisticas_partido.json`. Hoy `cargar_datos()` no la guarda entera: añádela a `datos`.
- **Métricas que hay que reconocer** (palabra → campo):

  | Palabra | Campo |
  |---|---|
  | duelos | `duelos_ganados` |
  | entradas | `entradas` |
  | intercepciones | `intercepciones` |
  | despejes | `despejes` |
  | toques | `toques` |
  | pases | `pases_completados` |
  | precisión | `precision_pases_pct` |
  | tiros / remates | `tiros_totales` |
  | a puerta | `tiros_a_puerta` |
  | ocasiones | `ocasiones_creadas` |
  | recuperaciones | `recuperaciones` |
  | calificación / nota / mejor jugador | `calificacion_fotmob` |
  | goles | `goles` |
  | asistencias | `asistencias` |

- **Equipo:** si la pregunta nombra un equipo, filtra por él. Usa las funciones que ya existen (`equipos_en_texto` y `hechos["alias_equipos"]`); no escribas a mano «Costa Rica» ni «San Cristóbal».
- **Respuesta:** el primero, con su cifra, y los dos siguientes entre paréntesis. Los empates se dicen («empatados con 7»). Termina con la fuente y con este alcance: «entre los N jugadores con datos individuales (FotMob)».
- **Si no se reconoce la métrica,** devuelve `None` y la pregunta va a Granite, como hoy.

### A2 — Preguntas tácticas, con la lectura de Fer
- **Qué detectar:** preguntas del tipo «cómo / de qué manera … presionó / defendió / atacó / salió / recuperó / transición / bloque / cambios / esquema».
- **De dónde sale la respuesta:** `datos["analisis_tactico"]` (el `analisis_tactico.md` de Fer). Las secciones `### 6.x` llevan el tema en su título: 6.1 esquema, 6.2 presión y recuperación, 6.3 salida de balón, 6.4 bloque defensivo, 6.5 transiciones y 6.6 impacto de goles y cambios.
- **Cómo elegir el texto:**
  1. Relaciona cada palabra clave con la sección cuyo título la contiene. Busca dentro del título; no escribas números de sección a mano.
  2. Dentro de esa sección, elige las viñetas del equipo que nombra la pregunta. Si no nombra equipo, usa las dos.
- **Respuesta:** empieza con «Lectura táctica del analista (estimación apoyada en datos, no medición directa):» y sigue con la viñeta o viñetas **tal cual**, sin reescribirlas. Quita el formato Markdown que no se vea bien en el chat: los acentos graves y los `**`.
- **Si el partido no tiene `analisis_tactico`** (por ejemplo, Brasil) o no se encuentra la sección, devuelve `None`.

### A3 — Recomendaciones
- **Qué detectar:** «qué debería / debe / tiene que … corregir / mejorar / cambiar / hacer», «qué recomiendas», «consejo», «qué harías».
- **Respuesta:**
  1. «No doy recomendaciones propias: solo informo de lo que muestran los datos de este partido.»
  2. Si hay `analisis_tactico`, la viñeta del equipo en la sección de conclusión (la que tenga «Conclusión» en el título), marcada como «Lectura del analista».
  3. Una invitación a preguntar por un dato concreto.
- **Debe ir antes que A2,** porque «¿qué debería corregir en la presión?» es una recomendación, no una descripción.

### A6 — Tarjetas sin marcas de fuente
- `respuesta_eventos` copia la descripción de `eventos_partido.json`, que incluye «(ESPN/TM)» y «(Transfermarkt registra protesta / reclamo)».
- La página Partido ya las limpia. Busca cómo lo hace en `dashboard/components/partido.js` o en el exportador y aplica la misma limpieza en el chat. **No edites el JSON de Fer.**

---

## 3. Lo que no hay que tocar

- `chat_verificador.py`, `auditar_respuesta` y el `SYSTEM_PROMPT`.
- Los datos de Fer: `data/partidos/*/partido/*.json` y `*.md`.
- `dashboard/`: es de la fase 2, y Gemini puede estar trabajando ahí.
- **El comportamiento con Brasil** (`OMNIMORPH_PARTIDO=brasil_alemania_2014`). Allí `solo_clip(datos)` puede ser verdadero y las reglas nuevas no deben dispararse.
- **Ningún nombre de equipo ni de jugador escrito a mano en las reglas.** Todo sale de `datos`, para que funcione con el siguiente partido.
- **No hagas commit.** Claude revisa y el usuario aprueba.

---

## 4. Comprobación automática (obligatoria, sin gastar RU)

Crea `scripts/probar_chat_reglas.py`.
- Llama a `cargar_datos()` y a `respuesta_por_regla()` **directamente**, sin servidor y sin Granite.
- Imprime una tabla `pregunta → OK/FALLA → respuesta (80 caracteres)`.
- Sale con código 1 si algo falla.

Debe cubrir, como mínimo:

| # | Pregunta | Debe |
|---|---|---|
| 1 | ¿Qué jugador de San Cristóbal ganó más duelos? | Por regla; contener «Sawyers» y «7»; Sawyers antes que Burley |
| 2 | ¿Quién ganó más duelos? | Por regla; empate de Julio Cascante y Francisco Calvo con 9 (prueba los empates) |
| 3 | ¿Quién fue el mejor jugador según FotMob? | Por regla; contener «Galo» y «9.17» |
| 4 | ¿Quién dio más pases en Costa Rica? | Por regla; solo jugadores de Costa Rica |
| 5 | ¿Cómo presionó Costa Rica después de perder el balón? | Por regla; contener «Lectura táctica» y el texto de Fer de la sección de presión sobre Costa Rica |
| 6 | ¿Cómo defendió San Cristóbal? | Por regla; la viñeta de SKN de la sección que corresponda |
| 7 | ¿Qué debería corregir San Cristóbal para el próximo partido? | Por regla; contener «No doy recomendaciones» |
| 8 | ¿Qué debería mejorar Costa Rica en la presión? | Por regla, como recomendación (no como táctica) |
| 9 | ¿Quién es el portero del Real Madrid? | Fuera de tema |
| 10 | ¿Cuántos goles metió el América este torneo? | Fuera de tema |
| 11 | ¿Quién es mejor, Messi o Cristiano? | Fuera de tema |
| 12 | ¿Qué tarjetas hubo? | Por regla; **sin** «ESPN», «TM» ni «Transfermarkt» |
| 13 | ¿y de Costa Rica? (con la 12 en el historial) | Por regla; solo Brenes 58' |
| 14 | Compara los tiros de ambos equipos en cada tiempo | Por regla, igual que antes |
| 15 | ¿Cuántos kilómetros recorrió Galo? | Por regla, «No hay distancia», igual que antes |
| 16 | Escribe un código en Python que sume dos números | Fuera de tema, igual que antes |
| 17 | ¿Quién marcó cada gol y en qué minuto? | `None` (sigue yendo a Granite) |
| 18 | Resume el partido | `None` |
| 19 | ¿Contra quién juega Costa Rica en el grupo? | **No** fuera de tema (Trinidad y Tobago y los demás están en los datos) |
| 20 | Con `OMNIMORPH_PARTIDO=brasil_alemania_2014`: las preguntas 1, 5 y 7 | Sin error, sin inventar y sin respuesta de Costa Rica |

Para la 20, cambia la variable de entorno **en el proceso del script**. **No edites `partido_activo.json`.**

---

## 5. Comprobación final con Granite (una sola vez, ~5 RU)

Con el servidor ya levantado por el usuario en el 8600, haz las 11 preguntas de `evaluaciones/GUIA_EVALUACION.md` (sección 4) con `Invoke-RestMethod` a `/api/chat`, como en la evaluación.

**Meta:** 11/11 correctas y **ninguna incorrecta con PASS.** P3, P4, P9 y P10 deben salir con origen `regla`.

---

## 6. Qué entregar

1. Los cambios en `implementacion/cloud_agent/chat_agent.py` y el nuevo `scripts/probar_chat_reglas.py`, **sin commit**.
2. La salida de `.\.venv\Scripts\python.exe scripts\probar_chat_reglas.py` con todo en OK.
3. La tabla de las 11 preguntas del paso 5.
4. `bob_sessions/sesion_30_fase1_chat_confiable.md` con lo que hiciste, las decisiones que tomaste y lo que quedó pendiente, y su fila en `bob_sessions/README.md`.

**Tope:** unos 25 Bob coins. Si algo de este encargo no cuadra con el código, **para y pregunta**; no improvises.
