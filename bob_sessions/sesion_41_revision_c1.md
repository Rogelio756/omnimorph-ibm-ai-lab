# Sesión 41 — Revisión de C1 y calibración por líneas (C1b)

**Fecha:** 2026-11-25 · **Agente:** Claude Code · **Rama:** feat-costa-rica

## Revisión de C1 (Gemini)
- Se repitieron las pruebas: `probar_radar.py` 8/8. Identidades 112 → 93 intactas; las demás columnas no cambiaron; respaldo completo.
- Se dibujó la cancha calculada sobre 18 cuadros. La media cancha coincide casi siempre; el círculo central sale chico y corrido a lo ancho.
- Causa: los puntos del modelo no caen sobre las líneas. La prueba de punto excluido (1.9 m), propuesta por Claude el 24/11, no podía verlo.

## C1b
`scripts/calibrar_lineas.py`: ajuste a las líneas blancas y propagación con flujo óptico. Sin GPU, sin modelos y sin cambiar posiciones. 1074 de 1080 cuadros.

| Medida | Original | C1 | C1b |
|---|---|---|---|
| 23 puntos a mano, mediana | 9.9 m* | 3.4 m | 0.2 m |
| 23 puntos a mano, máximo | 33.2 m* | 13.2 m | 1.4 m |
| Área grande sin usarla para calibrar | — | — | 2.4 m (p90 3.2) |

\* Medido en la cancha de 120 × 70 m. El territorio por tramo es el mismo con C1 y C1b: CRC, repartido, SKN, repartido, repartido, CRC, CRC, CRC.

## Límites
Los puntos a mano están sobre líneas que C1b usa. Se supone una cancha de 105 × 68 m. La velocidad sigue oculta: 4.4 % de las muestras suavizadas pasan de 9.5 m/s.

## Pendiente
Gemini integra C1b en las posiciones (encargo §3b) y sigue con C2.

## Revisión de C1b (25/11, tarde)

**Veredicto: C1b aprobado.** Gemini aplicó la calibración por líneas.

- `probar_radar.py`: 10/10, repetido por Claude. `probar_chat_reglas.py`: 62/62.
- Las homografías usadas son las de `calibracion_lineas.npz`. Hay 1074 cuadros válidos; los 6 de la toma cerrada (1074–1079) quedan sin posición.
- Identidades: 112 → 93, sin cambios en el equipo por fila. 0 valores vacíos y 0 infinitos en las posiciones limpias.
- Suavizado contra crudo: mediana 0.06 m, p99 1.2 m, máximo 3.8 m.
- Revisión visual: en 8 cuadros (uno por tramo) las marcas caen en los pies y el radar coincide con el video.

**Hallazgos de percepción (no los causa C1b):**
- El rastro 29 sigue a un jugador de SKN hasta cerca del cuadro 740 y a uno de CRC después (ya anotado en `rastros_dorsales.json`). Con una sola moda para todo el clip quedan 319 filas con el equipo equivocado.
- El equipo y la clase (jugador o árbitro) parpadean en algunos cuadros.
- **Regla para C2:** equipo y clase por moda de cada `track_id` dentro de cada tramo. El territorio no cambia con esta regla: CRC, repartido, SKN, repartido, repartido, CRC, CRC, CRC.

## Revisión de C2 (25/11, 16:10)

**Veredicto: C2 aprobado.**

- Repetidas por Claude: `probar_metricas.py` 8/8, `probar_radar.py` 10/10, `probar_chat_reglas.py` 62/62. Las pruebas no modifican `data/`.
- Recálculo independiente de 8 tramos × 2 equipos × 4 medidas: mismos valores. Las únicas 4 diferencias (W1 y W3) eran de la comprobación: contaba rastros cuya clase es balón; el motor los excluye, y hace bien.
- Se alteró el motor a propósito en 11 puntos. Las pruebas detectan 10. No detectan un cambio de `track_id` por `track_id_stitched` al agrupar.
- Datos sintéticos: corren con M2.0–M2.5 en PASS.
- Límite: el rastro 29 cambia de jugador dentro de W5 (69 filas CRC, 40 SKN). W5 no depende de él: la diferencia es de 88 puntos.
- **Para C3:** la voz dura 3.9 s por tramo y las frases de hoy tienen 13–18 palabras, así que el límite baja de 30 a 18.

## Revisión de C3a (25/11, 16:35)

**Veredicto: C3a casi aprobado. Pide una ronda corta de ajustes (C3a.1) antes de gastar Granite.**

- Repetido por Claude: `probar_cronica.py` 7/7. Los archivos de `data/clean` y `dashboard/data` quedan intactos.
- Con 12 frases trampa, M3 deja pasar 5:
  - «Costa Rica se repliega» en W0, donde el territorio es de CRC
  - «SKN avanza y empuja»
  - «busca el gol»
  - «ataca»
  - «sin espacio atrás, juega adelantado»: la negación de otra cláusula anula la regla
- Las frases offline usan «se repliega»: es un movimiento que no se mide.
- El exportador cambió cosas fuera del encargo: quitó la interpolación corta del balón y dejó de dibujar a los árbitros en los dos radares.
- MATEO: las barritas mezclan los dos equipos, porque toman el mayor de los dos valores. Tampoco hay costo estimado: el registro sin conexión anota RU.

## Revisión de C3a.1 (25/11, 16:55)

**Veredicto: aprobado para la corrida con Granite (C3b).**

- Repetido por Claude: `probar_cronica.py` 8/8. Las 5 frases trampa de C3a ya dan FAIL.
- **Huecos que quedan.** Estas frases dan PASS cuando el territorio es del otro equipo: «se instala en campo rival», «sube sus líneas», «retrasa sus líneas». Además, «88 por ciento» da FAIL por la palabra «ciento». Se cubren revisando a mano las 8 frases de Granite antes de publicar.
- `data/raw` es idéntico a `clip_15`, así que la corrida real no cambia las posiciones.
- Respaldo de `data/clean` (json), `dashboard/data` y `data/audio` en `backups/pre_c3b_2026-11-25/`, que git ignora.

## Corrida C3b con Granite (25/11, 16:56, la corrió el usuario)

- 9/9 monitores en PASS. M3: 6 tramos de Granite y 2 con plantilla (W5 y W7, después de 3 intentos por «avanza» y «controlando»). Costo estimado: 1.36 RU.
- **Revisión a mano (Claude): 4 de los 6 tramos de Granite contradicen los datos y M3 no lo detectó.**
  - W0: la narración dice «Territorio repartido», pero el territorio es de CRC (88 % contra 6 %). El análisis copia el ejemplo del prompt.
  - W1, W3 y W4: dicen que Costa Rica «se encuentra en la mitad rival», pero su mediana está en su mitad (48, 48 y 52 m; 40, 34 y 38 % en campo rival).
  - W2 y W6 están bien.
- Huecos de M3: no exige nombrar al equipo con territorio, y no comprueba «mitad rival» ni «su mitad» contra los datos.

## Cierre del día: demo funcional (25/11, 17:40)

**Decisión del usuario:** terminar lo que hay y tener una demo funcional antes de diseñar el pitch.

**Crónica:**
- W0, W1, W3 y W4 usan la plantilla verificada (`mode: offline`, con el campo `revision_humana`). Granite conserva W2 y W6. W5 y W7 ya eran de plantilla.
- Los 4 cambios quedan registrados en `governance_audit.jsonl`. M3 en PASS: 2 tramos con Granite y 6 con plantilla, con WARNING.

**Regenerado:**
- 8 voces (M4 en PASS).
- Videos con marcas y del radar.
- `mateo_data.json`, `metodo.json` y `transmision.json`.

**Revisado en el navegador (Claude):**
- Inicio, Partido, MATEO, Método y Transmisión: sin errores de consola.
- MATEO muestra las 4 medidas de los dos equipos y el territorio correcto en W0, W2, W4 y W7, y el texto «Comprobaciones del proceso: 9 de 9».
- Método muestra «Error del radar: mediana 2.4 m».

**Puerta humana:** la hoja `docs/video_demo/hoja_8_tramos.jpg` se envió para que Fer y el usuario la aprueben.

**Pendiente para el 26/11:** cerrar los 2 huecos de M3 (exigir que se nombre al equipo con territorio; comprobar «mitad rival» y «su mitad» contra el % de campo rival). Después, volver a correr Granite (~1.4 RU) si se quiere más voz de Granite en el video.

## Prueba en vivo del chat con Granite y vista en celular (25/11, noche, Claude)

- Chat en partido.html: estado «listo». La pregunta de Alfaro fue a Granite: 674 ms, 0.37 RU, PASS, respuesta apoyada en partido.json. La pregunta del 5-4-1 se respondió por regla con estado REVISAR (el verificador no encuentra respaldo para algunos números de la lectura del analista; revisar si son «40 minutos» y «15 minutos»).
- Celular a 375 px: ninguna página tiene desborde horizontal (Inicio, Partido, MATEO, Método, Transmisión, Opinión, Operaciones). Videos a 372 px en MATEO y 340 px en Transmisión.
- Detalles menores para el equipo: en MATEO hay textos de 9–10 px (pestañas de tramo, controles de audio y video, preguntas sugeridas) y botones de 28 px de alto (lo recomendado es ≥ 44 px). En Operaciones las preguntas largas se salen de su caja (la página no desborda).
- Servicio arriba en el puerto 8600 (0.0.0.0) para que lo revise el usuario.
- Opinión del usuario al cerrar: el radar de MATEO «se ve súper»; falta trabajar el radar de Transmisión. Se retoma el 26/11. Servidor apagado.
