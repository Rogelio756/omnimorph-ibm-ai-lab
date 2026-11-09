# Sesión 10: cambio de clip a Costa Rica y partido configurable
**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica` (sale de `feat-dashboard-mejoras` en `c3819cb`)
**Contexto:** demo en línea con Gallos Blancos de Querétaro esta semana. La reunión con IBM del 2026-11-05 salió bien.

---

## 1. Por qué cambia el clip

El clip 13 de Brasil 1-7 Alemania es el peor partido de Brasil y se presenta ante brasileños. Además rinde mal en percepción. Se midieron los clips del dataset con dos criterios: cortes de cámara por histograma HSV y jugadores detectados por segundo con `football-player-detection.pt`.

| Clip | Racha táctica más larga | Jugadores visibles (mediana) |
|---|---|---|
| Video de ejemplo `2e57b9_0.mp4` | 31 s (todo) | 21 |
| **`HP3zxNuoWXE-720-15.mp4` Costa Rica vs. SKN** | **36 s** | **15** |
| `7GL2KvcCrfk` Seattle vs. Vancouver (mejor clip) | 17.5 s | 11 |
| `L6sbfskaTDQ-480-13` Brasil vs. Alemania (anterior) | 7.5 s | 5 |

**Decisión del usuario:** el partido principal pasa a ser Costa Rica vs. San Cristóbal y Nieves, clip 15, segundos 0 a 36. El video de ejemplo y el de Brasil quedan como "comercial" de entrada. El clip 15 en 720p es de 1280×720, 29.97 fps y 1799 frames.

Hallazgo aparte: el clip 1 de Brasil muestra el estadio, que es el Mineirão. Con eso queda resuelto el pendiente del video de inicio.

## 2. Reparto entre agentes

- **Gemini (Antigravity):** percepción del clip 15. Encargo en `blueprints/encargo_gemini_percepcion_costa_rica.md`. Trabaja en la misma rama y carpeta, solo en `scripts/run_mvp_perception.py` y `scripts/finalize_mvp_perception.py`, y registra la sesión 11.
- **Equipo de análisis del usuario:** datos del partido con fuentes, en `data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx`. La prioridad es la pestaña Clip_15.
- **Claude Code:** núcleo del pipeline e integración.
- **IBM Bob:** sin asignar todavía. Los candidatos son el contexto Granite del chatbot para Costa Rica y el comercial de entrada.

## 3. Partido configurable

Antes, Brasil-Alemania estaba escrito a mano en engine, narrador, M3, chatbot y pipeline. Ahora:

- **`data/partidos/<id>/partido.config.json`:** fps, frames, video, carpeta de percepción y, por `team_id`, código, nombre, menciones válidas para M3 y sentido de ataque (`+x`/`-x`).
- **`data/partidos/partido_activo.json`:** elige el partido. La variable `OMNIMORPH_PARTIDO` tiene prioridad. **Sigue en `brasil_alemania_2014`** hasta que exista la percepción de Costa Rica.
- **`implementacion/partido_config.py`:** carga la configuración. Acepta los códigos históricos ARG/FRA como team_id 0/1.

| Archivo | Cambio |
|---|---|
| `omnimorph_engine.py` | Los fps del clip real salen de la configuración, ya no de la regla "más de 1000 frames = 30 fps". El equipo dominante usa el sentido de ataque y el código del partido. Los datos sintéticos siguen con ARG/FRA a 25 fps. |
| `agent_narrator.py` | El prompt y la narración offline usan los nombres del partido. Se añadió al prompt "sin inventar jugadores, goles ni marcador". |
| `governance_monitor_m3.py` | Las menciones válidas salen de la configuración. Se quitaron los alias "argentin"/"franc" que aceptaba para Brasil y Alemania. |
| `chat_agent.py` | Los nombres del equipo dominante salen de la configuración. **El resto del chatbot sigue siendo de Brasil** (prompt y `partido_data`) hasta que lleguen los datos de Costa Rica. |
| `dataset_manager.py` | Toma los parquets de la carpeta de percepción del partido activo y deja `data/raw/origen.json`, que está ignorado. Avisa si `data/raw` trae otro partido. Ya no recurre en silencio a `outputs/experiment/C_data`. |
| `run_pipeline.py` | La etiqueta del clip sale de la configuración. |
| `Dockerfile` | Copia `data/partidos/`. Sin eso, el engine fallaba en la nube con datos reales. |

## 4. Verificación

Respaldo previo en `backups/pre_costa_rica_2026-11-09/` (23 archivos).

- **Engine sobre Brasil:** las 8 ventanas salen iguales a las del respaldo, salvo `dominant_team`, que pasa de ARG/FRA a BRA/GER. `objects_cleaned.parquet` sale idéntico. M2.0–M2.5 en PASS.
- **M3 sobre las 8 narraciones reales anteriores:** 8 de 8 encuentran el equipo dominante.
- **Configuración de Costa Rica sobre los datos de Brasil (prueba de lógica):** con `+x` domina CRC en W0–W5 y SKN en W6–W7. Al invertir el sentido domina SKN en W0–W1, CRC en W6–W7 y el resto queda neutro, lo que coincide con los centroides. El prompt y la narración offline salen con Costa Rica y San Cristóbal y Nieves.
- **Modo sintético:** PASS.
- **`run_pipeline.py --use-real` con Granite real:** 9 de 9 en PASS en 24 s. 8 llamadas a `ibm/granite-4-h-small`, 8 en PASS y 0 offline.

**Sin verificar:**
- El pipeline con datos reales de Costa Rica, porque todavía no existe la percepción.
- La narración offline de Brasil cambió de texto. Es más genérica y ya no dice "precisión letal".
- El dashboard web y Streamlit siguen mostrando Brasil.

## 5. Pendientes

1. Gemini corre la percepción y reporta el mapeo de `team_id`. Con eso se completa `partido.config.json` de Costa Rica: equipos y sentido de ataque.
2. Cambiar `partido_activo.json` a Costa Rica y correr el pipeline completo.
3. Cuando llegue la plantilla del equipo de análisis: `partido_data`, el prompt del chatbot, el verificador y el cruce de dorsales con `track_id` para el fichero.
4. Dashboard web (`dashboard/`) con Costa Rica y el comercial de entrada con el video de ejemplo y el de Brasil.
5. Actualizar `AGENTS.md` §6, que sigue describiendo ARG/FRA con 750 frames.
