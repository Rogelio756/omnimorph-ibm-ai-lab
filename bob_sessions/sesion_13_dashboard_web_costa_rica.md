# Sesión 13: dashboard web con Costa Rica y chatbot en modo solo clip
**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`

---

## 1. Videos y datos del tablero

- **`scripts/render_post_engine_video.py`:** se corrió para Costa Rica y generó el video con marcas, el video del radar, el audio maestro TTS y el VTT.
- **Bug de fps corregido:** `supervision` trunca los fps a entero (29.97 → 29). Los videos duraban 37.2 s, mientras que el audio y los subtítulos duraban 36.04 s. Ahora el script usa la fracción exacta del contenedor. **Resultado:** original, marcas, radar y audio duran 36.04 s.
- **Leyenda del video con marcas:** ya no dice "Brasil/Alemania"; sale de la configuración, sin acentos porque `cv2.putText` no los dibuja.
- **Valores por defecto de `--source` y `--outdir`:** salen del partido activo.
- **`scripts/export_dashboard_data.py`:**
  - Lee el partido activo: carpeta de percepción, video, fps, códigos, nombres, colores y etiqueta corta.
  - Recorta el video original a los cuadros analizados (1080).
  - Si el partido no tiene ficha verificada, `partido.json` sale con `pendiente: true` y borra los SVG de Brasil.
- **`partido.config.json`:** nuevos campos `etiqueta_corta` y `color_ui` por equipo. En Costa Rica, el color de cada equipo es el mismo del video (SKN rosa, CRC celeste), para que tablero, radar y video coincidan.

## 2. Páginas

- **`mateo.html`:**
  - Equipos, colores, título y etiqueta salen de `mateo_data.json`; ya no hay BRA/GER escritos en el HTML.
  - El distintivo dice "SKN en campo rival", no "domina", porque eso es lo que mide la regla.
- **`partido.html` y `partido.js`:**
  - Con `pendiente: true` se muestra el título del partido y el aviso "En preparación", sin pestañas ni cifras.
  - El título, la etiqueta y el `<title>` ya no traen Brasil fijo en el HTML. En modo Brasil se arman desde `partido.json`.
- **Chat:** las preguntas sugeridas las manda el servidor (`/api/chat/estado` → `sugeridas`). Se quitó el placeholder "¿Qué bajas tuvo Brasil?".

## 3. Chatbot en modo solo clip

Si el partido activo no tiene `partido/contexto_partido.json`:

- **Datos:** `cargar_datos()` devuelve solo el partido, un `resumen_clip` calculado por código y las 8 ventanas.
- **Prompt:** `SYSTEM_PROMPT_CLIP`. Dice que no hay marcador, alineaciones, jugadores ni estadísticas, y que el equipo de análisis las verifica. Explica que "equipo dominante" no es posesión, prohíbe deducir nada de las ventanas neutras y obliga a usar `resumen_clip` para totales.
- **Reglas y verificador de atribución:** no se aplican. Usan datos de Brasil que este partido todavía no tiene.

**Pruebas con Granite real**, en el navegador y por la API:

| Pregunta | Resultado |
|---|---|
| ¿Qué equipo pasó más tiempo en campo rival? | Primera versión: Granite se equivocó de ventana, sumó mal e "infirió" datos (REVISAR). Con `resumen_clip`: correcta (PASS) |
| ¿En qué ventanas estuvo cada equipo en campo rival? | Correcta (PASS) |
| ¿Qué datos del partido todavía no tienes? | Correcta (PASS) |
| ¿Qué mide cada métrica del clip? | Correcta (PASS) |
| ¿Cómo quedó el marcador y quién metió los goles? | Responde que no tiene ese dato (PASS) |
| ¿Cómo cambió la altura del bloque? | Cifras correctas, pero conclusión falsa ("disminuyó progresivamente"). Se retiró de las sugeridas |
| ¿Cuándo estuvo más abierto y más cerrado el bloque? | Invirtió el sentido de la compacidad. El verificador la dejó en PASS porque las cifras existen. Se retiró de las sugeridas |

**Lección:** las preguntas que piden interpretar tendencias o comparar 8 valores siguen siendo frágiles con Granite. El verificador solo detecta cifras inventadas, no conclusiones falsas. Para la demo conviene usar las preguntas sugeridas.

## 4. Verificado en el navegador (puerto 8600)

- **`mateo.html`:** "CRC vs SKN · 2026", leyendas SKN/CRC y videos de 36.04 s. En el segundo 12, el radar muestra 7 SKN y 8 CRC con la toma abierta, y se ven métricas, crónica y transcripción de Costa Rica. Sin errores en consola.
- **`partido.html`:** aviso "En preparación".
- **Chat:** estado listo y sugeridas de Costa Rica.

### Corrección: audio del video original

**Lo detectó el usuario:** el recorte del original de Costa Rica descartaba su pista de audio. Por eso "Audio original" quedaba en silencio y "Narrador MATEO" solo tenía la voz, sin el sonido del estadio de fondo.

**Corrección:** `recortar_video()` copia ahora los mismos 36 s de audio, de MP3 a AAC estéreo a 44.1 kHz. Las dos pistas se declaran antes de escribir y el audio se lee desde una segunda apertura del archivo.

**Verificado en el navegador:**
- Con "Audio original" se decodifica el audio del original y el video de marcas queda en silencio.
- Con "Narrador MATEO" suenan los dos: el original al 25 % y la voz encima, con 0.13 s de diferencia entre videos.

## 5. Comercial y fondo de la portada

**Resultado final:** la portada vuelve a tener de fondo el video original del estadio (`assets/hero/demo_omni.mp4`). El comercial de 21 s que armó Claude va en una sección propia, **arriba de la franja de logos de IBM**.

- **Sección "Demostración":**
  - Texto a la izquierda y video a la derecha; en móvil, uno debajo del otro.
  - Usa los tokens del tablero y un video con controles: `assets/intro/comercial_omnimorph.mp4` (no versionado). Para cambiarlo, se reemplaza el archivo.
  - Arranca solo, en silencio, al entrar en pantalla y se pausa al salir. No arranca solo si el usuario lo pausó o si el sistema pide movimiento reducido; en ese caso se usa el botón de reproducir.
- **Historia del cambio:**
  1. Claude armó un comercial provisional y lo puso en una intro a pantalla completa.
  2. El usuario quiso editarlo a mano, así que se borró el script del comercial.
  3. El usuario entregó una edición propia, que pasó a ser el fondo (convertida a `assets/hero/fondo_inicio.mp4`, 1080p, 41 MB) y se quitó la intro.
  4. El usuario descartó ese fondo y pidió volver al estadio, con el comercial de Claude en una sección junto a los logos.
- **Verificado en el navegador:**
  - El fondo es `demo_omni.mp4` y la sección queda entre las tarjetas y los logos.
  - El video dura 21 s a 1280×720 y se reproduce.
  - El observador arranca y pausa con el desplazamiento (probado simulando una configuración sin movimiento reducido, porque el navegador de pruebas lo tiene activado).
  - En móvil (375 px) no hay desplazamiento horizontal.
- **Archivos que ya no se usan:** `assets/hero/fondo_inicio.mp4` y `assets/intro/demo_omni (1).mp4`, ambos fuera de Git.
- **Sonido y arranque automático (pedido del usuario):**
  - **Portada:** el video del estadio intenta sonar al 35 % al cargar. Los navegadores bloquean el sonido sin un gesto; en ese caso se activa con el primer clic, toque o tecla en cualquier parte, salvo sobre el botón de sonido, que decide por su cuenta.
  - **Al bajar:** con la portada visible menos del 35 %, se silencia; al volver, el sonido regresa. "Silenciar" se guarda en la sesión y manda sobre lo demás.
  - **Comercial:** arranca en silencio al llegar a su sección, también con "reducir movimiento" activado, porque así lo pidió el usuario. Se pausa al salir.
  - **Verificado en el navegador,** con desplazamiento real:
    - Al cargar suena (este navegador ya tenía interacción previa, así que no hubo bloqueo).
    - Un gesto simulado activa el sonido.
    - Al bajar, la portada se silencia y el comercial arranca (2.2 s reproducidos).
    - Al subir, vuelve el sonido y el comercial se pausa.
    - "Silenciar" se respeta al bajar y subir.
  - **Sin verificar:** el bloqueo real de sonido en un navegador sin interacción previa con el sitio. La lógica se probó simulando el gesto.

## 6. Riesgo visible para la demo

En los videos con marcas, muchos jugadores muestran **9.5 m/s**, que es el tope del filtro M2.3. Pasa también en el tramo de Brasil. Son jugadores trotando, y un analista lo va a notar. Es el ruido de velocidad de la sesión 12: la mediana de `v_mps` es de 10 m/s.

### 6.1 Diagnóstico (prototipos fuera del repo, sin aplicar)

- **Cómo se calcula:** la velocidad sale de `phase2_kinematics`. Usa Savitzky-Golay de 9 cuadros (0.3 s) y `np.diff` cuadro a cuadro.
- **Los huecos no son la causa:** solo hay 154 de 17 500 pasos con cuadros saltados.
- **Ruido de posición:** entre cuadros seguidos un jugador "salta" 33 cm de mediana, lo que equivale a 9.8 m/s aunque esté quieto. De esos 33 cm, 20 son comunes a todos los jugadores (homografía) y 24 son propios de cada uno (caja de detección).
- **Causa principal:** hay segundos en los que el equipo entero "se mueve" 10–12 m con la cámara quieta (paneo de 0 px, por ejemplo en los segundos 3, 17 y 28). Pasa porque la homografía se calcula con solo 7–8 puntos de confianza, casi todos de la línea central y el círculo, y salta en escalón cuando cambia el conjunto de puntos visibles.

| Variante | Mediana v | p90 | Etiquetas ≥ 9.5 m/s |
|---|---|---|---|
| Actual (H guardada, SG 9) | 9.3 m/s | 41 | 49 % |
| Solo puntos con conf ≥ 0.5, SG 9 | 7.1 | 47 | 41 % |
| H guardada, SG 31 (1 s) | 7.6 | 28 | 39 % |
| Conf ≥ 0.5 + H suavizada 15 cuadros + SG 31 | 5.3 | 31 | 28 % |
| Flujo óptico de cámara + corrección lenta con puntos de cancha + SG 31 | 6.1 | 22 | 32 % |

Ninguna variante llega a lo creíble, que sería una mediana de 1.5–3 m/s. En la fusión con flujo óptico se rechazaron entre 755 y 925 de 1080 cuadros de puntos de cancha. Una hipótesis, sin verificar: las vallas LED animadas y el público contaminan el flujo óptico.

### 6.2 Medidas para la demo (aprobadas por el usuario)

- **`render_post_engine_video.py`:**
  - Cada jugador lleva solo su número (`#id`), sin velocidad.
  - El panel del video muestra altura del bloque, compacidad, presión y tramo de la ventana. Se quitaron "Vel Trans" y el texto fijo "v<=9.5m/s | 22 IDs".
- **Narrador:** la velocidad de transición del balón también salía topada en 9.5 m/s en las 8 ventanas. Por eso Granite decía "transición rápida" y una narración citaba "9.50 m/s". Se quitó del prompt y de la narración offline, y el prompt prohíbe ahora inventar velocidades.
- **Pipeline completo con Granite real:** 9 de 9 en PASS, 8 de 8 llamadas en PASS. Ninguna narración nueva menciona velocidad ni "rápido".
- **Videos y tablero:** se volvieron a renderizar y exportar los videos de Costa Rica.
- **Comercial:** se volvió a armar con los tramos de Brasil y Costa Rica sin velocidades. El tramo de Brasil se renderizó con `OMNIMORPH_PARTIDO=brasil_alemania_2014` sobre una copia del respaldo, para no modificar `backups/`. El script del comercial vive solo en la carpeta temporal de la sesión, no en el repo. El tramo de Brasil ya no lleva los puntos de cancha, porque la copia no incluía `json_por_modelo/`.
- **Verificado:** etiquetas solo con número en el video del tablero y en el comercial, narraciones nuevas en la crónica y en la transcripción, y videos de 36 s.

### 6.3 Hallazgo: los equipos de Brasil-Alemania parecen invertidos

Al volver a renderizar el tramo de Brasil, los jugadores de amarillo (Brasil) salen con el color del `team_id 1` y los de Alemania con el del `team_id 0`. La configuración de Brasil, el tablero y las narraciones anteriores asumen lo contrario (0 = BRA). **Probable** inversión desde el clip 13 original; solo se vio en dos cuadros y no se midió. No afecta a la demo porque el partido activo es Costa Rica. Antes de volver a usar Brasil hay que verificarlo y, si se confirma, intercambiar los equipos en `brasil_alemania_2014/partido.config.json`.

## 7. Pendiente

- **Ruido de velocidad:** corregir de fondo la homografía (sección 6.1). En los videos ya no se muestra velocidad (6.2).
- **Barra lateral de MATEO (resuelto en la demo):** "Distancia" y "Vel. media" por rastro salían infladas aunque usaban un filtro de 1 s: velocidad media mediana de 5.4 m/s, unos 190 m en 36 s. El usuario aprobó ocultarlas.
  - La lista ordena ahora por tiempo visible en toma abierta.
  - La tarjeta muestra "Visible", "Zona habitual" (tercio izquierdo, centro o tercio derecho del radar, según el mapa de calor) y el mapa de calor.
  - El aviso explica que la distancia y la velocidad no se muestran mientras se mejora la calibración.
  - Verificado en el navegador: sin "m/s" en la página y sin errores nuevos en consola.
  - Los datos (`dist_m`, `segundos`) siguen en `mateo_data.json` para cuando se corrija la homografía.
- **Equipos de Brasil invertidos:** verificar (6.3).
- **`scripts/finalize_mvp_perception.py`:** tiene el mismo bug de fps; `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4` dura 37.2 s. El tablero no lo usa.
- **Velocidad de transición:** sigue en los datos del engine (topada en 9.5 m/s), pero ya no llega a la narración.
- **Video de la portada:** `assets/hero/demo_omni.mp4` parece la Arena Fonte Nova (Salvador), no el Mineirão.
- **Streamlit:** no se actualizó, porque el tablero objetivo es el web.
