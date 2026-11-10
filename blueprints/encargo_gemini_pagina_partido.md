# Encargo para Gemini (Antigravity): página Partido de Costa Rica vs. San Cristóbal y Nieves

**Asignado a:** Gemini en Antigravity
**Preparado por:** Claude Code, 2026-11-09
**Objetivo:** que `dashboard/pages/partido.html` deje de mostrar "En preparación" y presente el partido activo con el **mismo estilo** que tenía la página de Brasil 1–7 Alemania, usando los datos que ya llenaste en la plantilla (sesión 14).

---

## 0. Antes de empezar

1. Lee `AGENTS.md`, `bob_sessions/sesion_14_datos_partido_gemini.md` (tu sesión) y `bob_sessions/sesion_16_identificacion_manual_dorsales.md`.
2. **Misma carpeta y misma rama que Claude Code: `feat-costa-rica`.** No cambies de rama, ni hagas `stash`, `reset`, `git add -A` o `git add .`. En el commit, nombra tus archivos uno por uno.
3. Python: `.\.venv\Scripts\python.exe`, con `$env:PYTHONIOENCODING = "utf-8"`. Para leer el Excel, si el `.venv` no trae `openpyxl`, usa el Python del sistema.
4. Para servir el tablero: `.\.venv\Scripts\python.exe dashboard\serve.py --port 8600` y abre `http://localhost:8600/pages/partido.html`.

## 1. Situación actual

- **El partido activo** es `costa_rica_skn_eliminatorias_2026` (`data/partidos/partido_activo.json`). Su configuración (equipos, códigos, colores `color_ui`) está en `data/partidos/costa_rica_skn_eliminatorias_2026/partido.config.json`.
- **`scripts/export_dashboard_data.py` → `export_partido()`:** si no existe `partido/contexto_partido.json` en la carpeta del partido, escribe `dashboard/data/partido/partido.json` con `"pendiente": true`. Con ese valor, `dashboard/components/partido.js` muestra el aviso "En preparación".
- **La página de Brasil** tenía 5 pestañas: Ficha previa, Fichero, Comparativa 1T/2T, Los 8 goles y Gol de Müller. **Brasil está escrito a mano** en estos lugares:
  - `dashboard/components/partido.js`: `EQUIPOS = [['brasil', …], ['alemania', …]]`, textos "Brasil"/"Alemania", la imagen `mineirao.jpg`, la pestaña `muller` y las notas de calidad propias de ese partido.
  - `dashboard/components/fichero.js`: `EQUIPOS` y el estado inicial `equipo: 'brasil'`.
  - `export_partido()`: lee `gol_muller/gol_muller_min11.json` y copia los SVG `mapa_8_goles.svg` y `radar_gol_muller.svg`.
- **Formato de referencia:** `data/partidos/brasil_alemania_2014/partido/contexto_partido.json`, `estadisticas_partido.json` y `cronologia_goles.json`. En `contexto_partido.json`, cada equipo tiene `team_id`, `pais`, `codigo`, `entrenador`, `esquema_inicial`, `capitan`, `bajas_previas` y `plantilla` (dorsal → `nombre`, `posicion`, `titular`, `minutos`, `eventos`).

## 2. Pasos

### Paso 1: convertir la plantilla al formato del partido

Crea en `data/partidos/costa_rica_skn_eliminatorias_2026/partido/`:
- `contexto_partido.json`
- `estadisticas_partido.json`
- `cronologia_goles.json`

Sigue la misma estructura que Brasil:

- **Claves de equipo:** `costa_rica` y `san_cristobal_y_nieves`. El `team_id` debe ser el de `partido.config.json`: **0 = San Cristóbal y Nieves y 1 = Costa Rica**. No lo inviertas.
- **`SIN DATO` en la plantilla → `null`** en el JSON. **No estimes ni completes nada.** Nada de xG, coordenadas de goles ni distancias si no vienen de una fuente.
- **Minutos jugados:** calcúlalos de las columnas "Minuto entra/sale" de Alineaciones (titular sin cambio = 90). Es lo único que puedes calcular.
- **`eventos` de cada jugador:** salen de la pestaña Eventos (goles, asistencias, tarjetas, cambios).
- **Metadatos:** agrega a `contexto_partido.json` un bloque `"procedencia": {"origen": "PLANTILLA_datos_partido.xlsx", "recopilado_por": "Gemini (IA)", "validado": false, "fuentes": [...]}` con las URLs de la pestaña Fuentes.

**Criterio:** los tres JSON se cargan con `json.load`, los dos planteles completos están presentes y ningún valor de la plantilla marcado `SIN DATO` aparece como número.

### Paso 2: generalizar `export_partido()`

- `gol_muller` y los SVG pasan a ser **opcionales**: solo se exportan si existen.
- `partido.json` lleva también:
  - `"equipos_orden"`: las claves en orden de `team_id` (0, 1).
  - `"colores"`: el `color_ui` de cada equipo, tomado de `partido.config.json` vía `implementacion.partido_config`.
  - `"validado"`: el valor de `procedencia.validado`. Si el partido no tiene bloque `procedencia`, como Brasil, que ya se verificó en la sesión 8, vale `true`.
- Corre `.\.venv\Scripts\python.exe scripts\export_dashboard_data.py --solo-partido`.

**Criterio:** con Costa Rica activo, `dashboard/data/partido/partido.json` ya no tiene `"pendiente"`. Con `$env:OMNIMORPH_PARTIDO = "brasil_alemania_2014"`, Brasil exporta los mismos datos que antes: compáralo con `git show 11dd40a~1:dashboard/data/partido/partido.json`, que es el último `partido.json` de Brasil. Solo deben aparecer de más los campos nuevos (`equipos_orden`, `colores`, `validado`). **Al terminar, vuelve a exportar con Costa Rica activo.**

### Paso 3: generalizar `partido.js` y `fichero.js`

- **Equipos:** quita los `EQUIPOS` escritos a mano. Equipos, nombres, códigos y colores salen de `D.equipos`, `D.equipos_orden` y `D.colores`. El primer equipo seleccionado en el fichero es el primero de `equipos_orden`.
- **Pestañas según los datos:**
  - Ficha previa: siempre.
  - Fichero: siempre.
  - Comparativa: si hay estadísticas. Si solo hay totales y 1T/2T son `null`, muestra una sola columna "Total" en vez de tres.
  - Goles: si hay goles. El título usa el número real, por ejemplo "Los 4 goles". El mapa solo aparece si hay coordenadas.
  - **Gol de Müller:** solo si existe `D.gol_muller`. Para Costa Rica no aparece.
- **Imagen del estadio:** quita `mineirao.jpg` fijo. Si encuentras una foto del Estadio Nacional de Costa Rica con **licencia libre** (Wikimedia Commons, CC BY o CC BY-SA), guárdala en `dashboard/assets/estadio/` y cita autor, licencia y URL en `dashboard/assets/estadio/README.md`. Si no, la ficha va sin foto.
- **Aviso de calidad:** si `D.validado` es falso, el aviso superior dice: *"Datos públicos recopilados por IA con sus fuentes, pendientes de validación por el equipo de análisis."* y enlaza a la lista de fuentes. Mantén el aviso actual de Brasil solo para Brasil, o muévelo a sus datos.
- **Mismo estilo:** usa los componentes y estilos existentes (`match-hub.css`, `fichero.css`, `tabs.css`, tokens de `tokens.css`) sin crear colores nuevos. Los colores de los equipos salen de `D.colores`, que son los mismos que usa MATEO.
- **Opcional, solo si sobra tiempo:** en el fichero, si `data/partidos/<partido>/rastros_dorsales*.json` identifica a un jugador, muestra una insignia "Visto en el clip". Requiere exportar ese dato en `partido.json`.

**Criterio:** `partido.html` muestra Costa Rica vs. San Cristóbal y Nieves sin ninguna mención a Brasil, Alemania, Müller o Mineirão. Con Brasil activo, la página se ve como antes.

### Paso 4: verificar en el navegador de Antigravity

- **Con Costa Rica activo:** recorre las pestañas en escritorio y en móvil (375 px) y revisa la consola. Toma capturas de cada pestaña.
- **Con Brasil activo:** exporta y comprueba que las 5 pestañas se ven como antes. **Después vuelve a dejar Costa Rica activo y exportado.**

## 3. Lo que NO debes tocar

- **`implementacion/cloud_agent/`, chatbot incluido:** sigue en modo "solo clip" a propósito. No pongas `chat_datos_completos` en la configuración de Costa Rica. Eso lo hace Claude cuando Fer valide los datos.
- **Otros archivos:** `dashboard/pages/mateo.html`, `dashboard/pages/index.html`, `run_pipeline.py`, el engine, `data/raw/`, `data/clean/` y la plantilla Excel.
- **Git:** no subas videos, `.env` ni nada de `outputs/`.

## 4. Entregables

1. Los tres JSON del paso 1, los cambios en `scripts/export_dashboard_data.py`, `dashboard/components/partido.js`, `dashboard/components/fichero.js` y, si cambiaste `partido.html`, también este. Además, `dashboard/data/partido/partido.json` exportado con Costa Rica y la foto con su README, si la agregaste.
2. **`bob_sessions/sesion_17_pagina_partido_gemini.md`:** qué cambiaste, capturas o rutas a ellas, qué datos quedaron en `null` y la comprobación de Brasil.
3. La fila nueva en `bob_sessions/README.md`.
4. **Un commit**, nombrando archivo por archivo. Mensaje: `feat(partido): mostrar Costa Rica vs. SKN en la pagina Partido`. **Sin push.**
