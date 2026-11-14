# Sesión 25 — Datos del partido validados por Fer

**Fecha:** 2026-11-14 · **Agente:** Claude Code · **Rama:** feat-costa-rica

---

## 1. Qué se pidió

Fer (equipo de análisis) entregó su validación del partido Costa Rica 4-0 San Cristóbal y Nieves en el repo `FerTC8/omnimorph-costa-rica-skn-2024` (commit `8010944`). Había que pasar esos datos a Omnimorph.

## 2. Comparación con lo que ya había

- Las alineaciones coinciden en los 46 jugadores, salvo los minutos de #10 Aguilera (25 → 26) y #13 Brenes (65 → 64; el cambio fue al 64') y cuatro nombres de San Cristóbal: G'Vaune Amory, Tyrique Davis, Jal'Den Myers y Vibert Stephen.
- Los cuatro goles coinciden (40', 49', 82', 84'). La cronología oficial de FIFA resuelve las discrepancias de minuto que había en las notas (50' y 83').
- Los 10 dorsales del borrador de identificación manual (sesión 16) existen entre los titulares de Fer, con el mismo jugador.
- Nuestros identificadores de FIFA (400017351), ESPN (699898) y Transfermarkt (4356616) no coincidían con los de Fer (400017724, 698147 y 4343320). Se usan los de Fer, que vienen de las API oficiales.
- Estadísticas: Fer trae 1T y 2T, que no teníamos. En el total corrige tiros (15 → 23), bloqueados (1 → 8), fuera del área (5 → 13) y pases precisos (485 → 483, 222 → 221). Ahora los tiros cuadran: 7 + 8 + 8 = 23.
- xG: Fer indica que ninguna fuente lo publicó para este partido. El 2.51-0.20 que tenía Gemini se quita y se muestra «—».
- Clima: Fer confirma lluvia intensa durante todo el partido (antes decía «Nublado, lluvia previa»).

## 3. Cambios

| Archivo | Cambio |
|---|---|
| `scripts/importar_datos_fer.py` | Script nuevo que aplica los datos de Fer. Sin `--aplicar` solo muestra las diferencias. Se puede correr varias veces sin cambiar el resultado. |
| `data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/` | Copia del paquete de Fer (datos, README, FUENTES y ANALISIS_PARTIDO.md) |
| `.../partido/contexto_partido.json` | Minutos, nombres, eventos de cambio, identificadores externos, fuentes F2/F7/F8 corregidas, F17 (Fer) añadida, clima y `procedencia.validado: true` |
| `.../partido/estadisticas_partido.json` | 1T, 2T y total desde FotMob/Opta (vía Fer); xG sin dato |
| `.../partido/cronologia_goles.json` | Segundo oficial y parte del cuerpo de cada gol; notas de discrepancia resueltas |
| `.../rastros_dorsales.json` | Nuevo. Cada asignación tiene su propio `validado`: las 5 de certeza alta (Galo, Madrigal, Ugalde, Zamora, Lassiter) quedan validadas y las 5 de certeza media (Cascante, Brenes, Rogers, Lewis, Sterling-James) siguen «por validar» |
| `scripts/export_dashboard_data.py` | Lee `validado` por asignación y exporta cuántos jugadores están validados |
| `dashboard/components/metodo.js` | Muestra «5 de 10 jugadores por validar» en vez de todo o nada |
| `dashboard/data/*.json` | Regenerados con `export_dashboard_data.py` |

## 4. Verificado en el tablero (puerto 8600)

- Partido: ya no aparece el aviso de datos sin validar. La comparativa 1T/2T muestra las cifras nuevas y xG con «—».
- Método: «17 fuentes públicas · validados por el equipo de análisis» y «5 de 10 jugadores identificados a mano en el clip» por validar.
- Mateo: Lewis y Rogers aparecen con la etiqueta «por validar»; los de certeza alta, sin ella.

## 5. Chat completo para Costa Rica

El modo completo del chat estaba escrito para Brasil 1-7: su prompt fijaba ese marcador y leía los datos de `brasil_alemania_2014` (gol de Müller incluido). Se generalizó:

| Archivo | Cambio |
|---|---|
| `implementacion/partido_config.py` | Campo `chat` con el bloque del mismo nombre de `partido.config.json` |
| `data/partidos/*/partido.config.json` | Bloque `chat` (descripción, orden del marcador, nota sobre los datos, avisos y preguntas sugeridas). Costa Rica activa `chat_datos_completos` |
| `implementacion/cloud_agent/chat_agent.py` | Lee contexto, estadísticas y goles de la carpeta del partido activo. El prompt toma descripción, duración del clip y primer/último marcador de los datos. Métricas sin dato (xG) se omiten. El gol de Müller y el rendimiento individual solo se cargan si existen. Si el partido no tiene datos individuales, la regla lo dice sin pasar por Granite. `avisos_calidad` recibe los datos del partido |
| `implementacion/cloud_agent/chat_verificador.py` | Tolera métricas o tiempos sin dato y goles sin asistencia; reconoce los equipos por sus menciones (`skn`, `san cristóbal`, `ticos`) |
| `dashboard/serve.py`, `implementacion/dashboard/pages/3_Chatbot_Granite.py` | Pasan los datos a `avisos_calidad` |

**Pruebas:**
- Brasil (`OMNIMORPH_PARTIDO=brasil_alemania_2014`): con 15 preguntas y 4 respuestas de prueba, sin llamar a Granite, el prompt, las secciones, las respuestas por regla, los avisos y la verificación son idénticos antes y después.
- Costa Rica sin Granite: el prompt dice 4-0 y 36 s; las comparaciones por tiempo salen por regla; el verificador marca «Costa Rica 15 tiros» (son 23) y «Alcócer 1 asistencia» (son 0).
- Costa Rica con Granite (5 preguntas, ~1,05 RU): goles, cambios, clima, marcador al descanso y «no hay xG». Las cinco dieron PASS en la auditoría y coinciden con los datos de Fer.
- Tablero: `/api/chat/estado` devuelve las preguntas sugeridas de Costa Rica y `/api/chat` responde la comparación de tiros por regla.

## 6. Segunda pasada: el resto del paquete de Fer

La primera integración usó solo una parte del paquete y dejó dos errores ya subidos en `4f66fc9`: el chat negaba que hubiera estadísticas por jugador, y el clima mostraba 20 °C, 88 % y 11 km/h, que Fer marca como no disponibles.

`scripts/importar_datos_fer.py` ahora aplica también:
- **Estadísticas individuales** de FotMob/Opta para los 32 jugadores con minutos (`rendimiento_individual_destacado`): calificación, toques, pases, tiros, duelos, recuperaciones, y atajadas en el caso de los porteros.
- **Clima:** solo «Lluvia intensa». Temperatura, humedad y viento sin dato. La página Partido muestra «Lluvia intensa · temperatura sin dato oficial».
- **22 métricas de equipo** más, por tiempo (`metricas_adicionales`): postes, grandes ocasiones, duelos, regates, intercepciones, despejes, centros, etc.
- **Los 30 eventos** (`partido/eventos_partido.json`): tarjetas, atajadas, postes, cambios, ocasión clara, atención médica, con hora UTC.
- **Ficha:** rol táctico por jugador, nota de esquema (3-4-3 FIFA / 3-4-2-1 FotMob), uniformes detallados, nacionalidad de los DT, contexto del grupo, discrepancias resueltas y lista de datos no disponibles.
- **Goles:** la jugada descrita por Fer, la zona y las coordenadas FIFA.
- **Análisis táctico** (sección 6 de `ANALISIS_PARTIDO.md`) en `partido/analisis_tactico.md`.

Cambios en el chat (`chat_agent.py`):
- Nuevas secciones `eventos` y `analisis_tactico`. Del análisis solo se envían los 4 párrafos que más palabras comparten con la pregunta: con el análisis completo, Granite mezclaba cifras y el verificador bloqueaba las respuestas.
- Tarjetas, postes, atajadas y cambios se responden por regla desde los eventos. Granite había dado mal un minuto de tarjeta y contó el descanso como poste.
- Reglas sin LLM para «distancia recorrida» (no existe en este partido) y para los jugadores que no jugaron.
- Más palabras clave de estadísticas (calificación, FotMob, duelos, toques) y de análisis (defender, romper, cerrojo).

**Pruebas:**
- Brasil: los prompts, las respuestas por regla y la verificación siguen idénticos.
- Granite sobre Costa Rica:
  - pases de Galo, mejor jugador, jugada de cada gol, clima y el ajuste que pidió Alfaro: PASS;
  - dos preguntas tácticas abiertas, con el análisis completo, terminaron BLOQUEADAS por cifras mal atribuidas. Con los fragmentos, el ajuste de Alfaro sale correcto.

**Límite conocido:** el verificador no revisa las `metricas_adicionales`. En una prueba Granite citó «14 recuperaciones», que en realidad eran intercepciones, y la respuesta pasó.

## 7. Lo que NO se hizo

- No se corrió el validador de Fer (`validate_data.py`): era código descargado.
- Los diagramas SVG de Fer y una línea de tiempo de eventos en la página Partido.
- El tramo T18 de Lassiter sigue sin confirmar a mano, aunque el jugador quedó validado por el tramo T70.
- Sin commit.
