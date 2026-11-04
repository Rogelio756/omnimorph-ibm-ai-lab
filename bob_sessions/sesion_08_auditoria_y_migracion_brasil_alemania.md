# Sesión 08 — Auditoría del repositorio y migración de datos Brasil-Alemania
**Fecha:** 2026-11-04  
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA (MATEO)  
**Agente:** Claude Code  
**Rama activa:** `feat-dashboard-mejoras`  
**Estado:** Pasos 1 a 3 en GitHub (`ff2ff2b`); verificación de atribución implementada

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

Las 8 narraciones reales siguen en PASS al reauditarlas, y los casos negativos fallan como se espera. El narrador se probó en modo offline y mixto en un directorio aislado. **No se ejecutó `run_pipeline.py` completo.**

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

## 8. Próximos pasos

1. Avisar a Fer de las correcciones para llevarlas al repo de origen.
2. Ejecutar `run_pipeline.py` completo para confirmar los 9 monitores con el M3 corregido.
3. Al hacer commit, usar rutas explícitas. No usar `git add data/`, que subiría también `data/clean/`.
