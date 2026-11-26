# Sesión 42 — Entregables del programa y revisión humana de los 8 tramos

**Fecha:** 2026-11-26 · **Agente:** Claude Code · **Rama:** `feat-costa-rica`

## Qué se hizo

1. **Entregable 4 (`bob_sessions/`):** 11 tareas exportadas desde Bob IDE (menú `...` → «Export Current Task») y 6 capturas de consumo. Todas revisadas antes de subir: sin llaves, tokens ni correos. La captura de la cuenta se recortó para quitar el nombre. Índice con tabla tarea / exportación / captura / Bobcoins / reporte. Commit `dc4de65`.
2. **Entregables 2 y 3:** `DOC_PROBLEMA_SOLUCION.md` y `DOC_TECNOLOGIA.md` en la raíz, con cifras comprobadas contra el repo. Aclaran que no se usan LangChain ni CrewAI, que M3 es una auditoría propia (no usa watsonx.governance) y que Orchestrate y Code Engine están preparados, pero no se usan. Commit `9f97b0b`.
3. **Listado de pendientes de la web** antes de presentar (radar de Transmisión, M3, REVISAR del chat, letra y botones en celular, pasar a `main`, enlace al prototipo).
4. **Revisión humana de los 8 tramos** (criterio 2 de la meta).

## Revisión humana de los 8 tramos

- **Quién:** el responsable del proyecto (en lugar de Fer).
- **Material:** `docs/video_demo/hoja_8_tramos.jpg` (cuadro del video, radar, medidas y frase de MATEO por tramo).
- **Resultado:** **8 de 8 Sí**, tanto la frase como el radar. En sus palabras: visualmente cumple con todo y el texto explica bien lo que está pasando.
- **Límite:** se revisó sobre los cuadros de la hoja, no reproduciendo el video tramo por tramo.

## Pendientes

- Radar de Transmisión al nivel del de MATEO.
- M3: exigir nombrar al equipo con territorio y comparar «mitad rival» con los porcentajes; luego nueva corrida de Granite (la corre el usuario).
- Estado REVISAR en la respuesta del chat sobre el 5-4-1.
- Letra (9–10 px) y botones (28 px) de MATEO en celular.
- Escuchar las voces nuevas.
- Pasar `feat-costa-rica` a `main`; confirmar si el enlace al prototipo puede ser el repo.

## Radar de Transmisión (mismo día, Claude)

Decisiones del usuario: radar fijo (sin alternar con las alineaciones) y colores de los uniformes.

- **Cancha completa**, igual que en MATEO: áreas chicas, porterías, arcos y círculo central, con líneas más visibles.
- **Más grande:** del 22 % al 30 % del ancho del video; jugadores con radio 20 (antes 12) y borde oscuro; balón visible.
- **Siempre visible:** las alineaciones salen solo en los primeros segundos (jugada 0, de 0.5 a 3.5 s) y después el radar se queda fijo.
- **Tomas cerradas:** conserva la última posición conocida y muestra «Toma cerrada · última posición»; no dibuja el balón en esos cuadros.
- **Protagonista** marcado con un anillo verde, ligado a la estela sobre el video.
- **Leyenda** con los códigos y colores de los uniformes (CRC rojo, SKN verde).
- **Celular:** antes el radar se ocultaba; ahora aparece debajo del video (319 × 218 px a 375 px de ancho), sin desborde horizontal.
- Archivos: `dashboard/components/transmision-logica.js` (`graficosVisibles`, nueva `ultimoValido`), `transmision.js`, `pages/transmision.html`, `styles/components/transmision.css`, `scripts/probar_transmision_logica.js` (31 casos OK).
- `probar_transmision.py --hasta 7`: 32 de 33. La falla 7.3 exige que `mateo_data.json` no cambie desde el 22/11; cambió a propósito con la recalibración del 25/11.
- Nota de la prueba: en el panel del navegador de Claude, `requestAnimationFrame` corre a 2 por segundo, así que la estela se ve atrasada; las cajas del dato coinciden con los jugadores en el video.
- **Ajuste pedido por el usuario (estilo videojuego / TV):** el radar pasó abajo al centro, con el 24 % del ancho, inclinado en perspectiva (`perspective(900px) rotateX(38deg)`) como si estuviera acostado sobre la cancha, con césped semitransparente y leyenda centrada. Puntos más grandes para compensar el tamaño (jugadores radio 26, balón 16). En celular sigue plano, debajo del video.

## Paneles laterales tipo transmisión de F1 (mismo día, Claude)

Idea del usuario: paneles a los lados del video, SKN a la izquierda y CRC a la derecha, impulsados por Granite.

- **Cada panel:** encabezado (código, nombre, esquema y entrenador); «En este tramo» (distancia a su portería, % en campo rival, largo, ancho y quién ocupa más campo rival; las mismas cifras de MATEO, cambian cada 4.5 s); «En pantalla» (protagonista de la jugada si es de ese equipo); «Partido completo» (goles, posesión, tiros, tiros de esquina, amarillas y goleadores, marcados como fuente pública); «Dato curioso» que rota por jugada.
- **Granite:** `scripts/generar_datos_curiosos.py` hace 1 llamada por equipo (2 en total) con hechos tomados de `partido.json`. Cada frase se verifica: 18 palabras o menos, números y nombres presentes en los hechos, sin velocidad ni xG. Lo que no pasa se reemplaza por el hecho tal cual. Salida: `dashboard/data/datos_curiosos.json`; el panel marca cada dato como «IBM Granite» o «Dato verificado». Por ahora solo se corrió `--offline` (0 RU); falta la corrida con Granite (la corre el usuario).
- **Botón «Ocultar / Mostrar estadísticas»** para volver al modo TV; se recuerda en el navegador.
- **Acomodo:** tres columnas desde 1200 px; en pantallas medianas los paneles bajan lado a lado; en celular, uno debajo del otro. Sin desborde a 375 px y sin textos de menos de 12 px.
- `export_transmision.py` agrega la clave `paneles`; el resto de `transmision.json` queda igual (comprobado).
- Pruebas: lógica 32 de 32 (nuevo `datoCurioso`); `probar_transmision.py` 32 de 33 (la misma falla 7.3 de antes).
- **Corrida con Granite (la hizo el usuario):** 2 llamadas (SKN: 385 tokens de entrada y 229 de salida, 2.2 s; CRC: 399 y 107, 1.2 s). Tres frases de CRC pasaban la primera verificación, pero calificaban sin respaldo: «Costa Rica **dominó** con un 65 % de posesión», «Galo anotó **dos** goles **tempranos**» (fueron a los minutos 40 y 49) y «una atajada **clave**». Se endureció el verificador (juicios como dominó, clave, temprano o decisivo, y números en letras) y se agregó `--reverificar`, que revisa lo ya generado sin volver a llamar a Granite. Resultado: 9 frases de Granite y 3 de plantilla; las 3 rechazadas quedan en la auditoría del archivo.
- **Versión 2 de los paneles (pedido del usuario: «que no se vea tan técnico» y botones pegados al video):**
  - Letra normal en lugar de títulos en mayúsculas tipo código; textos más grandes.
  - Se quitaron largo y ancho.
  - «Ahora mismo» habla como aficionado: «Está adelantado», «Juego parejo» o «Está en su mitad»; «Juega a 71 m de su portería»; «88 % de sus jugadores en campo rival». Cada frase lleva una barra del color del equipo.
  - «En el partido» muestra cifras grandes (goles, tiros, a puerta), «Tuvo el balón el 65 % del tiempo» con barra, y los goleadores con su minuto.
  - «¿Sabías que…?» lleva la etiqueta «Escrito por IBM Granite» o «Dato del partido».
  - Los botones (Pausa, Voz de MATEO, Repetir, Ocultar estadísticas) quedan justo debajo del video, a 8 px, en computadora y en celular.
  - Comprobado a 1600 px y a 375 px: sin desborde, sin textos de menos de 12 px y sin errores en consola. Pruebas: lógica 32 de 32 y `probar_transmision.py` 32 de 33 (la misma falla 7.3).
- **Portada (pedido del usuario):** el botón «Ver partido de muestra» ahora dice «Prueba MATEO» (lleva a MATEO). Se agregó «Disfruta el partido», que lleva a Transmisión. El botón de sonido se queda. En celular los botones bajan de renglón sin salirse de la pantalla.
