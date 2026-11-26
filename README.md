# Omnimorph · MATEO

> Omnimorph convierte un clip de partido en una explicación táctica en español que un cuerpo técnico puede entender sin ayuda y comprobar en el mismo video.

Esa es la meta del proyecto; `docs/meta_y_funciones.md` explica qué parte se cumple hoy y qué se está corrigiendo.

La demo analiza un clip de TV ya grabado, de 36 segundos, de **Costa Rica 4–0 San Cristóbal y Nieves** (eliminatorias de Concacaf al Mundial 2026). La visión por computadora ubica a los jugadores y al balón, un motor resume lo que pasa en tramos de 4.5 segundos e IBM Granite (`ibm/granite-4-h-small`, en watsonx.ai) redacta la crónica y responde en el chat.

## Arrancar el tablero

Requiere Python 3.12. Los comandos son para PowerShell, desde la raíz del repositorio.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe dashboard/serve.py
```

Abre <http://localhost:8600>.

Para usar el chat con Granite, edita `.env` antes de arrancar: `IBM_CLOUD_API_KEY`, `WATSONX_URL` y `WATSONX_SPACE_ID` o `WATSONX_PROJECT_ID`. Sin credenciales, todo lo demás funciona igual y el chat indica que Granite no está disponible.

## Páginas

| Página | Contenido | ¿Requiere algo más? |
|---|---|---|
| Inicio | Portada | Sin el video, muestra un fondo animado |
| MATEO | Video, radar, métricas, crónica y jugadores en un mismo reloj | Los videos, para reproducir |
| Partido | Ficha, jugadores, comparativa, goles y eventos | No |
| Transmisión | Vista tipo TV con la voz de MATEO, radar y alineaciones | Los videos, para reproducir |
| Método | Fuentes, flujo, monitores y límites | No |
| Tu opinión | Guía y formulario de la prueba | No |
| Operaciones | Consola interna; solo en la PC que corre el servidor | Credenciales, para comprobar IBM |
| Burbuja de chat | Preguntas sobre el partido | Credenciales de watsonx.ai |

## Herramientas

- **Percepción:** roboflow/sports, YOLOv8, ByteTrack, clasificación por equipo (SigLIP, UMAP y KMeans) y homografía.
- **Motor:** unión de rastros con el algoritmo húngaro y trayectorias Savitzky-Golay.
- **Lenguaje:** solo IBM Granite en watsonx.ai. **Voz:** síntesis local.
- **Web:** HTML, CSS y JavaScript con un servidor en Python.
- **Desarrollo:** IBM Bob, Claude Code y Gemini.

## Límites

- No es en vivo: analiza un clip ya grabado. No se ha probado con video de celular.
- La posición en el radar es aproximada y la calibración está en corrección.
- No muestra velocidades, distancias ni sprints: la calibración todavía no da cifras confiables.
- No mide la posesión del clip, xG ni PPDA. La posesión que aparece en Partido viene de fuentes públicas.
- Los nombres de los jugadores se identificaron a mano: 10 de 46, 5 de ellos validados.
- Los monitores revisan el proceso; no sustituyen la lectura de un analista.

### Chat

- Cada pregunta a Granite gasta cuota de watsonx.ai, así que el servidor limita las peticiones.
- Los goles, los eventos, los rankings y las comparaciones los responde el código con los datos, sin LLM.
- Si las cifras de una respuesta de Granite no coinciden con los datos, se descarta.
- Aun así puede equivocarse: no detecta afirmaciones falsas con cifras reales ni detalles sin cifras.

## Videos

Los videos no están en Git, por regla del proyecto (`AGENTS.md` §3). Sin ellos el reproductor no funciona, pero los datos, el radar y la línea de tiempo sí. Consíguelos con el equipo y cópialos en `dashboard/media/` (videos, audio y subtítulos) y `dashboard/assets/hero/` (portada).

## Datos

- `data/partidos/<partido>/` guarda la configuración y los datos de cada partido; `data/partidos/partido_activo.json` elige cuál se usa.
- Costa Rica vs. San Cristóbal y Nieves: fuentes en `data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/FUENTES.md`.
- Brasil 1–7 Alemania (2014) fue el primer partido y se conserva como referencia histórica.
- Tras cambiar los datos del partido, ejecuta `python scripts/export_dashboard_data.py --solo-partido`.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts/probar_chat_reglas.py
.\.venv\Scripts\python.exe -X utf8 scripts/probar_transmision.py --hasta 7
```

## Pipeline

`run_pipeline.py` no se puede ejecutar desde un clon limpio con los datos reales: `data/raw/`, `data/clean/` y los videos no están en Git.

> [!WARNING]
> Sin `--use-real`, el pipeline **sobrescribe `data/raw/`** con datos sintéticos.

## Más información

- `AGENTS.md`: reglas del proyecto.
- `docs/meta_y_funciones.md`: meta, funciones y correcciones.
- `docs/resumen_ejecutivo/`: un resumen por página.
- `bob_sessions/`: bitácora de cada sesión de desarrollo.
- `dashboard/DESIGN.md`: sistema de diseño.
- `implementacion/dashboard/`: versión anterior en Streamlit, conservada como respaldo.
