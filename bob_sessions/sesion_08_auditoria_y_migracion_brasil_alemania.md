# Sesión 08 — Auditoría del repositorio y migración de datos Brasil-Alemania
**Fecha:** 2026-11-04  
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA (MATEO)  
**Agente:** Claude Code  
**Rama activa:** `feat-dashboard-mejoras`  
**Estado:** Pasos 1 a 3 y verificación en GitHub (`d9a8248`); frontend web implementado, sin commit

---

## 1. Qué se hizo

1. Auditoría de solo lectura del repo, del dashboard Streamlit, de la capa LLM y de los datos de `omnimorph-brasil-alemania-2014`.
2. Contraste de las estadísticas con el reporte oficial FIFA del Partido 61 y con fuentes públicas.
3. Paso 1 del roadmap: datos copiados y corregidos en `data/partidos/brasil_alemania_2014/`. El usuario eligió corregir antes de copiar.

No se modificó código ni el clon de origen. No se llamó a Granite.

---

## 2. Migración de datos

- **Origen:** commit `7dc3661` del repo de FerTC8.
- **Destino:** `partido/`, `gol_muller/`, `assets/`, `FUENTES.md` y `PROCEDENCIA.md` (11 archivos, 228 KB).
- **Detalle completo:** cada corrección, su motivo y lo que sigue sin verificar están en `PROCEDENCIA.md`.

| Dato | Antes | Ahora | Estado |
|---|---|---|---|
| Tiros a puerta de Alemania, 1T / 2T | 9 / 1 | 7 / 3 | Derivado |
| Tiros fuera/bloqueados de Alemania, 1T / 2T | 1 / 3 | 3 / 1 | Derivado |
| Posesión total, Brasil–Alemania | 47–53 | 52–48 | Fuente secundaria |
| Distancia de los 8 goles | Solo eje X | Euclidiana | Calculado |
| Distancia del gol de Müller (JSON y radar SVG) | 9.2 m | 11.3 m | Calculado |

**Hallazgo:** los totales de tiros a puerta (8 y 10) no eran un error. FIFA publica 13 y 12, que equivalen a `a puerta + bloqueados`.

**Validación:** el validador de origen pasa sobre la copia. Además pasaron 41 comprobaciones nuevas de coherencia, entre ellas goles + atajadas = tiros a puerta. Esas comprobaciones se ejecutaron con un script temporal y no quedaron en el repo.

---

## 3. Sin verificar

- La posesión total depende de la fuente: FIFA vía Wikipedia 52–48, ESPN 51–49, footballcritic 47–53.
- No se encontró fuente pública para los desgloses por tiempo.
- No se pudo abrir `web.archive.org`, así que falta contrastar el reporte técnico TSG y la página archivada de FIFA.
- El xG es estimado y la telemetría de Müller es ilustrativa.

---

## 4. Hallazgos pendientes en el código

1. **Documentación:** `AGENTS.md` §6 sigue en ARG/FRA con 750 frames; a `.env.example` le falta `WATSONX_SPACE_ID`.
2. **Otros:** `.env.txt` duplica las credenciales; `sesion_dashboard_omnimorph_2026-11-04.md` sigue fuera del índice; `blueprints/` no existe; el Dockerfile copia `data/raw/`, que no está en Git.

---

## 5. Paso 2 — Página de análisis

- **Nueva página:** `pages/2_Analisis_Brasil_Alemania.py`, con cuatro pestañas: ficha previa, comparativa 1T/2T, los 8 goles y gol de Müller.
- **Datos compartidos:** `partido_data.py` carga los datos sin depender de Streamlit, para que también lo use el chatbot.
- **Encoding:** `app.py` y Observabilidad ya leen sus archivos en UTF-8.
- **Observabilidad:** renombrada a `4_Observabilidad.py`, para que el chatbot ocupe la posición 3.
- **Decisiones:** se mantuvo `pages/` por convención del repo. Del modo brownfield se aplicó el mapeo y no el blueprint completo de 20 secciones, por ser una sola página sobre un mapa ya hecho.
- **Colores:** los gráficos usan `#2563eb` y `#dc2626`, validados para modo claro y oscuro. La paleta naranja/crema de `DESIGN.md` no se usó porque el crema casi no se ve sobre fondo blanco.

**Verificado en el navegador, en modo oscuro:** las cuatro pestañas, el selector de gol, las páginas `app` y Observabilidad, sin excepciones y con los acentos correctos.

**Sin verificar:** el modo claro.

---

## 6. Paso 3 — Chatbot con Granite

- **Nueva página:** `pages/3_Chatbot_Granite.py`, con preguntas sugeridas, respuesta en streaming, latencia y tokens por respuesta, y un límite de 30 preguntas por conversación.
- **Agente:** `cloud_agent/chat_agent.py`, con `ibm/granite-4-h-small` y sin credenciales en código.
- **Contexto por pregunta:** se envían solo las secciones relevantes, lo que baja de unos 7.000 a entre 2.000 y 4.000 tokens en la mayoría de las preguntas.
- **Formato de datos:** una línea autónoma por dato, con el sentido del cambio y los goles por tiempo y jugador calculados por código. Con JSON anidado o tablas por columnas, el modelo atribuía cifras al equipo equivocado.
- **Respuestas sin LLM:** si se pide una estadística individual de un jugador sin datos, responde el código. Granite tomaba de forma consistente la cifra de otro jugador, aunque recibía la lista.
- **Avisos:** los de xG estimado y datos sin confirmar los pone el código.
- **Auditoría:** `data/clean/chat_audit.jsonl`, ignorado por Git, con estado PASS, REVISAR (cifras que no aparecen en los datos) o FAIL.

### Correcciones al Monitor M3

- Solo acepta los dos modelos de `AGENTS.md`; antes bastaba el prefijo `ibm/granite`.
- La revisión anti-alucinación ya puede fallar; antes siempre pasaba.
- El modo se registra por ventana, con `offline` y `mixto` a nivel global, y el reporte incluye `offline_calls`.

Las 8 narraciones reales siguen en PASS al reauditarlas, y los casos negativos fallan como se espera. El narrador se probó en modo offline y mixto en un directorio aislado. **`run_pipeline.py` completo se ejecutó después (sección 8).**

### Limitaciones conocidas

- **Preguntas abiertas o comparaciones amplias:** Granite sigue atribuyendo cifras al equipo equivocado. «¿Cómo cambió el partido del 1T al 2T?» falló en casi todas las pruebas, y por eso se retiró de las sugeridas. El verificador las marca, pero no las evita.
- **Detalles inventados:** en explicaciones narrativas, como la del gol de Müller, puede añadir detalles que no están en los datos. El verificador no los detecta, porque solo revisa cifras.
- **Primera carga:** conectar con Granite tarda unos 45 s; después queda en caché.
- **Mediciones:** las pruebas sumaron unas 17 RU estimadas. Costo y tokens son aproximados.

---

## 7. Verificación de atribución

`cloud_agent/chat_verificador.py` comprueba por reglas, sin LLM, que cada cifra corresponda al equipo o jugador, la métrica y el tiempo indicados. Las cifras que no coinciden se muestran en pantalla, se guardan en `atribucion_incorrecta` y dejan la respuesta en REVISAR. Se eligió REVISAR y no FAIL porque es una comprobación por reglas, no un veredicto.

**Resultado:** 8 de 8 respuestas malas reales detectadas, 0 falsos positivos en 22 respuestas correctas y 16 de 16 casos dirigidos. En una prueba con Granite por la página, marcó una respuesta mala y dejó en PASS una correcta.

**Importante:** esos casos se usaron también para ajustar las reglas, así que no son una medición independiente. Una versión anterior marcó 9 errores en una respuesta casi correcta, y eso solo apareció al probar con Granite real.

**Limitaciones:**

- PASS significa que no encontró problemas, no que la respuesta sea correcta.
- Solo revisa cifras en las que reconoce equipo o jugador y métrica. Las afirmaciones sin cifras, como «Brasil mejoró», no se comprueban.
- En comparaciones como «Alemania dominó en tiros a puerta (10 vs 8)», puede atribuir la segunda cifra al primer equipo y marcarla por error.
- Marca, pero no corrige ni bloquea la respuesta.

---

## 8. Ejecución completa del pipeline

`run_pipeline.py --use-real` con respaldo previo de `data/clean`, `data/audio` y `data/raw` en `backups/pre_pipeline_2026-11-04/` (23 archivos, checksums verificados).

**Resultado:** 9 de 9 monitores en PASS en 74,8 s. El M3 corregido registró 8 llamadas a `ibm/granite-4-h-small`, 8 en PASS, 0 offline, con 1,39 s de latencia media. Las ventanas tácticas salieron idénticas a las anteriores.

**Efecto secundario:** el pipeline regenera las narraciones y el audio por ventana, pero no el audio maestro (`NARRACION_COMPLETA_60S.wav`), los subtítulos (`narrations_es.vtt`) ni el video, que se hicieron a mano. Con las narraciones nuevas, el texto del dashboard ya no coincidía con el audio y los subtítulos.

**Decisión:** se guardó la ejecución nueva en `backups/post_pipeline_2026-11-04/` y se restauraron desde el respaldo `narrations.json`, `governance_audit.jsonl`, `monitor_m3.json`, `monitor_m4.json` y los `W*.wav`. Así el dashboard sigue coherente con el video y los subtítulos. Los monitores M1 y M2 y `pipeline_summary.json` quedan con los de la ejecución nueva, también en PASS. Se verificó que cada narración aparece en el VTT.

**Consecuencia:** el `monitor_m3.json` activo es el anterior, sin el campo `offline_calls`. La evidencia del M3 corregido está en la carpeta `post_pipeline`.

**Para que el pipeline sea repetible:** falta integrar la generación del audio maestro y de los subtítulos en `run_pipeline.py`. Hasta entonces, cada ejecución desfasa esos archivos.

---

## 9. Cambio de rumbo: frontend web de `dashboard/`

El usuario aclaró que el dashboard sobre el que quería trabajar es el frontend web que ya tenía (el del video, `dashboard/`), no el Streamlit. Las páginas de Streamlit se conservan como respaldo y no se tocaron más.

**Qué se hizo en `dashboard/`:**

- **`pages/partido.html`** con `components/partido.js`: las cuatro pestañas (ficha previa, comparativa 1T/2T, los 8 goles y gol de Müller), con gráfico SVG propio, tooltip, tabla de 12 métricas y el aviso de calidad de datos. Los datos se insertan con `textContent`.
- **`pages/chat.html`** con `components/chat.js`: chatbot con preguntas sugeridas, avisos de cifras, métricas por respuesta, límite de 30 preguntas y «Nueva conversación».
- **`serve.py`:** `POST /api/chat` y `GET /api/chat/estado`, que reutilizan `chat_agent.py` y el verificador. Carga Granite en segundo plano. Además, los `.js` y `.css` ya salen sin caché.
- **Navegación común** (`site-nav.js`) en las cuatro páginas y la portada.
- **Datos:** `scripts/export_dashboard_data.py --solo-partido` genera `dashboard/data/partido/` (JSON, 2 SVG y `PROCEDENCIA.md`).
- **Estilos:** cinco archivos CSS nuevos que solo usan los tokens de `tokens.css`.

**Seguridad del endpoint** (gasta cuota de watsonx.ai): solo conexiones locales; `Host` y `Origin` locales (frena el DNS rebinding); `Content-Type` JSON; cuerpo máximo de 16 KB; pregunta máxima de 500 caracteres; 12 peticiones por minuto; solo roles `user` y `assistant` en el historial. Se probaron todas con peticiones reales: 403, 415, 400, 413, 429 y el descarte de un mensaje con rol `system`.

**Colores:** el validador de paleta da FAIL en banda de luminosidad y saturación mínima para naranja/crema, porque el crema es casi blanco. Sí pasa la separación entre equipos (23,6 en visión normal, 22,5 con daltonismo) y el contraste. Se mantuvieron los colores de `DESIGN.md`, que define el crema «diferenciado por luminosidad», y se añadió codificación secundaria: etiquetas BRA/GER, valores sobre las barras y leyenda.

**Hallazgos de las pruebas:**

- La primera pregunta tras un rato de inactividad tarda unos 20 s en el servicio, y las siguientes unos 0,4 s. Un calentamiento al arrancar no lo evitó, así que se quitó y la página avisa al usuario tras 6 s de espera.
- La pregunta abierta «¿Cómo cambió el partido del 1T al 2T?» sigue fallando, y ahora el aviso aparece en pantalla con cada cifra discrepante.
- El puerto 8600 lo ocupaba el servidor que el usuario ya tenía corriendo (PID 20744). No se tocó. Las pruebas se hicieron en el 8601. Ese servidor necesita reiniciarse para tener el endpoint del chat; las páginas estáticas funcionan sin reiniciar.

**Sin verificar:** el límite de 30 preguntas en pantalla, el diseño en móvil, el despliegue en Code Engine y las capturas con el panel en primer plano. La verificación visual se limitó a las páginas del chat y de la comparativa.

---

## 10. Próximos pasos

1. Reiniciar el servidor del puerto 8600 y probar el chat allí.
2. Avisar a Fer de las correcciones para llevarlas al repo de origen.
3. Integrar audio maestro y subtítulos en el pipeline.
4. Descargar las fuentes locales (Jost, Inter, JetBrains Mono), que siguen pendientes y dan 404 en todas las páginas.
5. Al hacer commit, usar rutas explícitas. No usar `git add data/`, que subiría también `data/clean/`.
