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

## 5. Pendiente

- **Comercial de entrada** con el video de ejemplo y el de Brasil.
- **`scripts/finalize_mvp_perception.py`:** tiene el mismo bug de fps; `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4` dura 37.2 s. El tablero no lo usa.
- **Velocidad de transición:** sale topada en 9.5 m/s en las 8 ventanas de Costa Rica. Como métrica no aporta y no se investigó.
- **Video de la portada:** `assets/hero/demo_omni.mp4` parece la Arena Fonte Nova (Salvador), no el Mineirão.
- **Streamlit:** no se actualizó, porque el tablero objetivo es el web.
