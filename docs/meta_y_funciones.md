# Omnimorph — Meta, funciones y correcciones

**Fecha:** 2026-11-24 · **Autor:** Claude Code (diseño y revisión) · **Estado:** meta y correcciones aprobadas por el responsable del proyecto el 24/11; falta compartirlas con el equipo
**Implementan:** Bob o Gemini. Este documento no cambia código.

## 1. Meta fundamental

> **Omnimorph convierte un clip de partido en una explicación táctica en español que un cuerpo técnico puede entender sin ayuda y comprobar en el mismo video.**

| Parte de la meta | Qué exige |
|---|---|
| «un clip de partido» | Video ya grabado. No es en vivo. Hoy: 36 s de Costa Rica vs. San Cristóbal y Nieves |
| «explicación táctica en español» | Dónde está cada equipo y qué hace, escrito y narrado por IBM Granite |
| «un cuerpo técnico» | Usuario principal. Amateur, reclutadores y TV son usos posteriores |
| «entender sin ayuda» | Se prueba con personas. Hoy hay 0 opiniones en tres rondas |
| «comprobar en el mismo video» | **La regla que hoy no se cumple:** lo que dice la crónica debe verse en el video |

**Cómo sabremos que se cumple**
1. El radar coincide con el video: error mediano de 3 m o menos en puntos que no se usaron para calibrar.
2. Ninguna frase de la crónica contradice el video. Lo revisa una persona, tramo por tramo (8 de 8).
3. El chat no agrega hechos que no estén en los datos (0 en la lista de preguntas de prueba).
4. Al menos 5 personas del público lo prueban y dicen si lo entendieron.

**Qué NO promete hoy:** análisis en vivo, velocidades, distancias o sprints, identificar jugadores de forma automática, xG o PPDA, posesión medida en el clip, ni video amateur.

## 2. Hallazgo principal: por qué falla el radar

- La calibración usa **todos** los puntos de la cancha que devuelve el modelo, también los de baja confianza. El filtro es solo `x > 1 y y > 1` (`scripts/run_mvp_perception.py:197`).
- La sesión 11 ya lo había visto y supuso que el motor lo corregía. **No lo corrige:** `omnimorph_engine.py` calcula `H_ema`, pero no la usa para ubicar a nadie.
- M1 y M2.1 dan PASS porque revisan que la matriz exista, no que sea correcta.

**Prueba hecha el 24/11** (fuera del repo, con los puntos ya guardados en `data/raw/frames.parquet`; sin GPU, sin Granite): usar solo puntos con confianza mayor que 0.5 y fuera del borde de la imagen, con RANSAC. Se dejó fuera un punto por vez y se midió a cuántos metros lo ubica cada método (4 413 mediciones en 975 cuadros).

| Método | Error mediano | 90 % de los casos | Error mayor a 5 m |
|---|---|---|---|
| Actual (punto excluido) | 9.7 m | 29.5 m | 77 % |
| **Con filtro (punto excluido)** | **1.9 m** | **5.6 m** | **12 %** |

Límites de la prueba: la referencia son puntos detectados con confianza mayor que 0.9, no medidas hechas por una persona. Siete cuadros se quedan sin calibración y hay que conservar la anterior. **La velocidad sigue sin servir:** 37 % de los pasos cuadro a cuadro superan 9.5 m/s (hoy, 51 %).

**Corrección del 25/11:** el 1.9 m no es el error real. Esa prueba usa como referencia los puntos que detecta el modelo, y esos puntos no caen sobre las líneas blancas aunque traigan confianza 1.00. Con 23 puntos marcados a mano en 6 cuadros (cancha de 105 × 68 m), la mediana con el filtro es 3.4 m y el máximo 13.2 m; el problema está a lo ancho. C1b (`scripts/calibrar_lineas.py`) ajusta cada cuadro a las líneas blancas: mediana 0.2 m y máximo 1.4 m en esos puntos. Esos puntos están sobre líneas que C1b usa, así que no son independientes. La prueba independiente calibra sin el área grande y mide dónde queda: **mediana 2.4 m, p90 3.2 m** en 284 cuadros. El territorio por tramo no cambia.

**Qué cambia en la historia del partido** (posiciones de la prueba, por validar):

| Tramo | La crónica actual dice | % de SKN en su mitad | % de CRC en campo rival | Lectura |
|---|---|---|---|---|
| 1 | SKN presiona y controla | 92 % | 86 % | **Al revés:** SKN replegado |
| 2 | SKN domina la presión | 50 % | 40 % | Repartido |
| 3 | SKN presiona en campo rival | 38 % | 17 % | Apoya que SKN está adelantado |
| 4 | SKN domina la posesión | 57 % | 35 % | Repartido; la posesión no se mide |
| 5 | Mediocampo | 60 % | 40 % | Repartido |
| 6 | SKN lucha, CRC defiende bajo presión | 94 % | 95 % | **Al revés:** juego en la mitad de SKN |
| 7 | SKN presiona alto | 90 % | 90 % | **Al revés:** SKN replegado |
| 8 | CRC presiona en mediocampo | 100 % | 95 % | Juego en la mitad de SKN |

Solo cuenta a los jugadores visibles en cada cuadro.

## 3. Funciones: hoy y después de corregir

| Función | Qué hace hoy | Corrección | Qué podremos prometer |
|---|---|---|---|
| **Radar** | Ubica mal parte del clip | C1 | Posición aproximada, con su error medido y visible en Método |
| **Métricas** | Nombres que no corresponden al cálculo | C2 | Posición media, territorio, largo y ancho visibles de **cada** equipo |
| **Crónica y voz** | Afirma presión, dominio y posesión sin medirlos | C3 | Describe dónde está cada equipo, comprobable en el video |
| **Verificación (9 monitores)** | Comprueba que los datos existen | C3 | Comprueba también el error del radar y las palabras sin respaldo |
| **Chat** | Goles redactados por Granite; inventó un penal | C4 | Los goles salen del dato, sin redacción libre |
| **Partido** | Ficha, jugadores, comparativa, goles y 30 eventos | C5 | Igual, con formato único |
| **Transmisión** | Vista de TV con voz, radar y alineaciones | C1, C3, C5 | Igual, con radar y voz corregidos |
| **MATEO** | Video, radar, métricas, crónica y jugadores en un reloj | C1–C3, C5 | Igual, con datos comprobables |
| **Método** | Fuentes, límites y flujo | C5 | Publica el error del radar y sus límites |
| **Inicio** | Anuncia «velocidad de transición» | C5 | Solo anuncia lo que se ve |
| **Operaciones** | Consola interna, solo en la PC | — | Igual |
| **Opinión** | Formulario de 20 minutos | C5 | Incluye Transmisión |

## 4. Correcciones

### Antes del video
**C1 · Radar.** Recalcular las posiciones de jugadores, árbitro y balón desde los recuadros y los puntos ya guardados. Puntos con confianza > 0.5 y a más de 2 px del borde; RANSAC; si hay menos de 4, conservar la calibración anterior. Guardar copia de los datos actuales antes. No volver a correr los modelos.
*Aceptación:* error mediano con punto excluido ≤ 3 m; en los segundos 1, 2.4, 24, 31 y 35.5 los jugadores quedan del lado de la media cancha que muestra el video.

**C2 · Métricas** (`implementacion/cloud_tool/omnimorph_engine.py:377-439`). Hoy «altura del bloque» suma la dispersión a lo ancho de los dos equipos, «compacidad» es la dispersión a lo largo solo de SKN y la velocidad de transición está en el tope (9.5 m/s) en los 8 tramos. Reemplazar por, para cada equipo: posición media (mediana), % de jugadores en campo rival, largo visible y ancho visible (percentil 10 a 90 por cuadro, mediana del tramo). Quitar la velocidad de transición. El equipo con territorio se decide con la misma regla para los dos; hoy se revisa primero a SKN.
*Aceptación:* intercambiar los equipos no cambia el resultado; cada etiqueta de la web describe su fórmula.

**C3 · Crónica, voz y M3.** Regenerar los 8 textos con los datos nuevos, y después voz, videos con marcas, radar y JSON de la web. El prompt pide describir posiciones y prohíbe «posesión», «presiona» y «domina». M3 rechaza esas palabras y compara con los dos equipos. M2.1 falla si el error del radar pasa de 3 m. Costo esperado de Granite: similar a la corrida anterior (0.60 RU).
*Aceptación:* 8 de 8 tramos aprobados por una persona viendo el video; una crónica falsa de prueba hace fallar M3.

**C4 · Chat.** Las preguntas sobre goles se responden por regla, copiando `jugada` de los datos. Agregar «¿Quién marcó cada gol y cómo fue la jugada?» a las pruebas.
*Aceptación:* la respuesta no contiene «penal» ni «de primera»; la pregunta sobre el tramo 1 no dice que SKN dominó.

**C5 · Textos y detalles.**
- Inicio: quitar «velocidad de transición».
- MATEO: cambiar «Análisis verificado» por «Comprobaciones del proceso: 9 de 9»; corregir «Toma cerrada» al inicio; que «Con marcas» no tape el marcador y el botón del chat no tape texto en el celular.
- Partido y Transmisión: mismo formato de aforo (15,700). La formación se queda: Partido ya explica 3-4-3 y 3-4-2-1.
- Método y Opinión: agregar Transmisión. Método publica el error del radar y deja de decir que Orchestrate «se integró y probó»: la sesión 20 registra que la importación no se completó.
- `README.md` todavía describe Brasil–Alemania; `docs/resumen_ejecutivo/00` y `02` repiten las métricas mal nombradas. El `README.md` es lo primero que verá el jurado.

**Orden:** C1 → C2 → C3. C4 y C5 pueden ir aparte.

**Si no alcanzan los Bobcoins** (~24 al 23/11, hasta el 2/12): hacer solo C4 y C5, retirar la crónica de los tramos 1, 4, 6 y 7 y rotular el radar «en pruebas». Es honesto, pero la meta queda sin cumplir.

### Después de la entrega
Velocidades, identidad automática de jugadores, video amateur, chat con más partidos y despliegue en la nube (si el programa lo permite).

## 5. Evidencia de Bobcoins
Faltan las capturas. La lista está en `bob_sessions/capturas/README.md`.

## 6. Decisiones del equipo
1. ¿Se aprueba la meta de la sección 1?
2. ¿Quién implementa C1–C3: Bob o Gemini?
3. ¿Quién revisa los 8 tramos viendo el video? (propuesta: Fer)
