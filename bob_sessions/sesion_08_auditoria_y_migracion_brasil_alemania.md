# Sesión 08 — Auditoría del repositorio y migración de datos Brasil-Alemania
**Fecha:** 2026-11-04  
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA (MATEO)  
**Agente:** Claude Code  
**Rama activa:** `feat-dashboard-mejoras`  
**Estado:** Paso 1 en commit `ec00cfc`; Paso 2 implementado

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

1. **Monitor M3:**
   - `governance_monitor_m3.py:148`: la revisión anti-alucinación siempre pasa.
   - `agent_narrator.py:396`: declara Granite como modelo usado incluso en modo offline.
   - `agent_narrator.py:392`: una ventana que cae a offline queda marcada `online`.
2. **Chatbot:** el M3 actual no sirve para el chat, porque exige JSON por ventana y el narrador borra el log de auditoría en cada corrida.
3. **Documentación:** `AGENTS.md` §6 sigue en ARG/FRA con 750 frames; a `.env.example` le falta `WATSONX_SPACE_ID`.
4. **Otros:** `.env.txt` duplica las credenciales; `sesion_dashboard_omnimorph_2026-11-04.md` sigue fuera del índice; `blueprints/` no existe; el Dockerfile copia `data/raw/`, que no está en Git.

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

## 6. Próximos pasos

1. Avisar a Fer de las correcciones para llevarlas al repo de origen.
2. Paso 3: chatbot con `ibm/granite-4-h-small` y auditoría propia, corrigiendo además el M3.
3. Al hacer commit, usar rutas explícitas. No usar `git add data/`, que subiría también `data/clean/`.
