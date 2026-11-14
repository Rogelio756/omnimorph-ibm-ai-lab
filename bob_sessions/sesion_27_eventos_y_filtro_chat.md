# Sesión 27 — Filas de Eventos y filtro de tema del chat

**Fecha:** 2026-11-14 · **Agente:** Claude Code · **Rama:** feat-costa-rica

---

## 1. Qué se pidió

1. En la pestaña Eventos de la página Partido, la fila del descanso se veía con el texto partido letra por letra.
2. El chat respondía preguntas ajenas al partido (por ejemplo, de Python). Debe responder solo sobre el partido y el análisis.

## 2. Eventos

- **Causa:** la fila es una rejilla de 6 columnas. Los eventos sin jugador ni equipo (inicio, descanso, final) no tienen esos dos elementos, así que la descripción caía en la columna angosta del jugador. Ahora cada parte tiene su columna fija (`match-hub.css`).
- El tipo de evento ya no usa `capitalize`, que dejaba «Atención Médica»: ahora usa los nombres en español.
- El segundo jugador se explica según el evento: «Entra X · sale Y» en los cambios y «X · asistencia de Y» en los goles. Antes era «X → Y» para todo.

## 3. Filtro de tema del chat (`chat_agent.py`)

La regla 8 del prompt ya pedía no salir del partido, pero Granite no siempre la cumple. Ahora `fuera_de_tema()` decide antes de llamar al modelo, y `respuesta_por_regla()` contesta sin Granite: «Solo puedo responder sobre el partido …», con una pregunta de ejemplo.

- **Fuera de tema siempre:** programación (Python, código, SQL…), recetas, chistes, política, criptomonedas y pedidos de ignorar las reglas o revelar el prompt. Esto vale aunque la pregunta mencione el partido.
- **Dentro de tema:** vocabulario de fútbol y del tablero, palabras clave de las secciones, nombres o menciones de los equipos, jugadores y entrenadores.
- **Seguimientos cortos** (≤ 8 palabras con historial, como «¿y el segundo?»): se permiten.
- `respuesta_por_regla()` recibe ahora el historial (`dashboard/serve.py` y la página de Streamlit lo pasan).

**Error encontrado al probar:** «¿y San Cristóbal?» después de «¿Qué cambios hizo Costa Rica?» iba a Granite, que inventó un minuto (49' en vez de 53') y un jugador (Maynard en vez de Mitchum). Ahora `respuesta_eventos()` toma el tipo de evento de la pregunta anterior en los seguimientos cortos y responde desde los datos.

## 4. Pruebas

- Filtro sin Granite: 9 preguntas ajenas, todas rechazadas, y 13 del partido, todas aceptadas. Entre las aceptadas están «¿Qué función tuvo Galo?», «¿Qué hizo Alfaro?» y las preguntas sugeridas de Costa Rica y de Brasil.
- Brasil: los prompts no cambian. La única respuesta distinta es «¿Qué hizo Alfaro?», que ahora se rechaza porque Alfaro no es de ese partido.
- Tablero (`/api/chat`): la pregunta de Python sale por regla con el mensaje de alcance, y el seguimiento de cambios sale por regla con los 5 cambios correctos.
- Página Eventos: ninguna fila se desarma; el descanso ocupa una sola línea.

## 5. Notas

- El puerto 8600 estaba ocupado por otro servidor (probablemente el de la sesión 26 de Bob), así que la vista previa corrió en 8601.
- Sin commit.
