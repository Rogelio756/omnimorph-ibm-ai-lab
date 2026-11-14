# Evaluación de Omnimorph — IBM Bob — 2026-11-14
Commit evaluado: `63b4603 feat(dashboard): primera impresión en lenguaje de fútbol` · Puerto: 8600

> **Nota de método:** No usé navegador. Recorrí las páginas leyendo `dashboard/pages/*.html`, `dashboard/js/*.js` y `dashboard/data/*.json`, y juzgo lo que vería el usuario. Las 11 preguntas del chat se ejecutaron con `Invoke-RestMethod` contra `http://localhost:8600/api/chat`. La sección G (móvil) es **estimada** a partir del CSS.

---

## Puntuación

| A | B | C | D | E | F | G (est.) | H | Media |
|---|---|---|---|---|---|---|---|---|
| 5 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | **4.1** |

---

## Chat: 11 preguntas

| # | Pregunta | ✔/◐/✘ | Origen | Estado API | Latencia (ms) | Nota |
|---|---|---|---|---|---|---|
| 1 | ¿Quién marcó cada gol y en qué minuto? | ✔ | `ibm/granite-4-h-small` | PASS | ~3 678 (round-trip) / 1 147 (modelo) | Galo 40' y 49', Alcócer 82', Rojas 84'. Correcto. |
| 2 | ¿Quién fue el mejor jugador según FotMob? | ✔ | regla | PASS | ~2 521 | Orlando Galo 9.17. Correcto y con contexto (Ugalde 8.24, Zamora 8.12). |
| 3 | ¿Qué jugador de San Cristóbal ganó más duelos? | ✔ | regla | PASS | ~2 521 | Sawyers 7, Lewis 6, Burley 5. Correcto. |
| 4 | ¿Cómo presionó Costa Rica después de perder el balón? | ✔ | regla | PASS | ~2 564 | Acoso inmediato + intensificación en 2T (15 tackles vs 5 en 1T). Correcto y marcado como lectura táctica del analista. |
| 5 | Compara los tiros de ambos equipos en cada tiempo | ✔ | regla | PASS | ~2 522 | CRC 10 (1T) + 13 (2T) = 23; SKN 3 (1T) + 2 (2T) = 5. Correcto. |
| 6 | ¿Qué tarjetas hubo? | ✔ | regla | PASS | ~2 554 | Sterling-James 26', Ible 45'+4', Brenes 58', Maynard 63'. Correcto. |
| 7 | ¿y de Costa Rica? (con historial de P6) | ✔ | regla | PASS | ~2 514 | Solo Brenes 58'. Correcto. Contexto del historial respetado. |
| 8 | ¿Cuántos kilómetros recorrió Galo? | ✔ | regla | PASS | ~2 542 | "No hay distancia recorrida en este partido: ninguna fuente pública publicó datos de tracking físico." Correcto. |
| 9 | ¿Qué debería corregir San Cristóbal para el próximo partido? | ◐ | regla | **REVISAR** | ~2 610 | No inventa recomendaciones propias (bien). Pero el texto táctico de relleno disparó falsos positivos del verificador (`atribucion_incorrecta` con 7 entradas sobre los propios datos del partido). El estado fue REVISAR (no BLOQUEADA ni PASS). La respuesta en sí es correcta; el bug está en el verificador. |
| 10 | ¿Quién es el portero del Real Madrid? | ✔ | regla | PASS | ~2 508 | Rechazo correcto y educado. |
| 11 | Escribe un código en Python que sume dos números | ✔ | regla | PASS | ~2 540 | Rechazo correcto y educado. |

**Resultado: 10/11 correctas (✔), 1 incompleta (◐).** La incorrecta que salió como PASS: ninguna. El único problema (Q9) fue marcado REVISAR, no PASS silencioso — el sistema de alerta funciona.

---

## Lo mejor (máx. 5)

1. **Propuesta de valor en 10 segundos.** La hero — «¡Que no te lo cuente tu cuñado!» + subtítulo + demo note con el marcador real — dice exactamente qué es y para quién, antes de hacer scroll. Para un jefe de análisis que llega en frío, es el mejor mensaje posible.
2. **Integridad de datos en el chat.** De las 11 preguntas, 10 reciben respuestas factuales perfectas. El sistema de reglas cubre con precisión todos los eventos clave del partido sin alucinaciones. El rechazo de preguntas fuera de contexto (Q10, Q11) es limpio y orientador.
3. **Transparencia sobre lo que no hay.** Q8 (distancia Galo), el aviso «En preparación» en Partido, la sección de datos no disponibles en el JSON y el badge «Lectura del analista» en Q4 son patrones de honestidad que inspiran confianza a un scout profesional. Es la diferencia entre una demo que da vergüenza y una que se puede enseñar.
4. **Monitor completamente verde.** 9/9 monitores PASS en la última corrida (`metodo.json`). La página Método expone latencias reales (1 588 ms media), costo RU (0.59) y límites físicos (9,5 m/s). Da confianza técnica sin jerga innecesaria.
5. **Chat widget en móvil bien resuelto.** El CSS convierte el widget flotante en pantalla completa a ≤600 px e incrementa el `font-size` del textarea a 16 px para evitar el zoom automático en iOS. Decisión de UX madura.

---

## Problemas, de más a menos grave

### CRÍTICO — Q9: verificador genera falsos REVISAR en texto táctico legítimo
**Qué vi:** La pregunta «¿Qué debería corregir San Cristóbal?» devuelve `estado: REVISAR` y lista 7 entradas en `atribucion_incorrecta`, incluyendo números que sí existen en los datos («65.3% de posesión») y otros que son artefactos del regex aplicado al párrafo táctico. La respuesta textual es correcta y no inventa nada.
**Dónde:** `implementacion/cloud_agent/chat_agent.py`, función `respuesta_tactica()` / verificador de atribución.
**Por qué le importa a un club:** Si los operadores ven «REVISAR» en la consola de Operaciones van a desconfiar de la crónica táctica entera, aunque el texto sea correcto. Peor: si el umbral de REVISAR alguna vez bloquea la respuesta al usuario, esta pregunta legítima quedaría sin responder.
**Mejora propuesta:** Revisar el regex de detección de números; excluir el contexto del párrafo táctico de Fer del chequeo de atribución, o marcar ese bloque explícitamente como texto-fuente validado. Alternativamente, aplicar el verificador solo a las partes generadas por el modelo, no a las reglas predefinidas.

### IMPORTANTE — Pestaña «Eventos» oculta en Partido
**Qué vi:** `partido.html` define el botón `tab-eventos` con `hidden`. Un jefe de análisis que hace clic en las pestañas llega a Ficha previa, Fichero, Comparativa 1T/2T y Goles, pero no a Eventos. La cronología del SVG existe (`timeline_partido.svg`) pero no es accesible.
**Dónde:** `dashboard/pages/partido.html`, línea 74.
**Por qué importa:** La línea de tiempo es el recurso más valioso para preparar una reunión técnica rápida. Esconderla baja la nota de Utilidad Táctica.
**Mejora propuesta:** Quitar el atributo `hidden` del botón o migrar el contenido del SVG al panel antes de la próxima demo.

### IMPORTANTE — Nombre del partido invertido en `mateo_data.json`
**Qué vi:** El campo `meta.match` dice `"SKN vs CRC"` pero el partido es Costa Rica (local) 4-0 San Cristóbal. Este valor se muestra probablemente en el chip de cabecera.
**Dónde:** `dashboard/data/mateo_data.json`, campo `meta.match`.
**Por qué importa:** Un analista de Liga MX lo nota inmediatamente. Si el local aparece como visitante en la cabecera, la demo pierde credibilidad.
**Mejora propuesta:** Cambiar a `"CRC vs SKN · Eliminatorias Concacaf Mundial 2026 — Segunda ronda, jornada 1"`.

### IMPORTANTE — Página Método no diferencia explícitamente «medido», «estimado» y «no disponible»
**Qué vi:** `metodo.html` delega toda la presentación a `metodo.js` cargando `metodo.json`. El JSON lista monitores y checks (todos PASS) pero no tiene una sección de texto que explique al entrenador qué es una medición directa (p. ej. posición vía homografía), qué es una estimación (p. ej. velocidad máxima del bloque) y qué no existe (xG, distancias, calor). La distinción existe en `partido.json > datos_no_disponibles`, pero no aparece en la vista Método.
**Dónde:** `dashboard/pages/metodo.html` + `dashboard/data/metodo.json`.
**Por qué importa:** Un cuerpo técnico va a preguntar «¿esto es medido o inventado?». Si la página Método no lo dice claramente, el analista tiene que explicarlo verbalmente en cada reunión.
**Mejora propuesta:** Añadir al `metodo.json` tres listas: `medido`, `estimado` y `no_disponible`, y renderizarlas en la página con íconos de semáforo.

### MENOR — `Operaciones` no tiene audiencia clara en la navegación
**Qué vi:** La página se titula «Operaciones · monitores · consumo del chat · conexión con IBM». Es un cuadro de mandos de ingeniería, pero aparece en el footer de todas las páginas como «Operaciones técnicas» sin ningún aviso de que no es para el entrenador.
**Dónde:** Todos los `<footer>` del dashboard.
**Por qué importa:** Si el entrenador hace clic durante la demo y ve terminales, conteos de tokens y latencias sin contexto, puede perder la confianza.
**Mejora propuesta:** Añadir un chip «Solo técnicos» en la cabecera de Operaciones, o moverlo fuera del footer principal para la demo pública.

---

## Una frase para el entrenador

«Es como tener un analista de video que ya revisó la transmisión de TV, te coloca a cada jugador en el mapa de la cancha cuadro a cuadro y te escribe un resumen táctico; puedes preguntarle cualquier dato del partido y no inventa nada que no tenga fuente.»
