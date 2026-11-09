# Omnimorph · MATEO

Análisis táctico y narración de fútbol con IA, sobre la semifinal Brasil 1–7 Alemania (Mundial 2014).
El modelo es IBM Granite (`ibm/granite-4-h-small`) en watsonx.ai.

Un flujo de visión por computadora extrae posiciones del video, las convierte en ventanas tácticas de datos, y Granite trabaja sobre esos datos para narrar y responder preguntas.

## Arrancar el tablero

Requiere Python 3.12. Los comandos son para PowerShell, desde la raíz del repositorio.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dashboard.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe dashboard/serve.py
```

Abre <http://localhost:8600>.

Para usar el chatbot, edita `.env` antes de arrancar: `IBM_CLOUD_API_KEY`, `WATSONX_URL` y `WATSONX_SPACE_ID` o `WATSONX_PROJECT_ID`. Sin credenciales, todo lo demás funciona igual y el chat indica que Granite no está disponible.

## Páginas

| Página | Contenido | ¿Requiere algo más? |
|---|---|---|
| Inicio | Portada | Sin el video, muestra un fondo animado |
| MATEO | Video, radar, métricas y crónica sincronizados | Los videos, para reproducir |
| Partido | Ficha, comparativa 1T/2T, los 8 goles y gol de Müller | No |
| Burbuja de chat (en MATEO y Partido) | Preguntas sobre el partido | Credenciales de watsonx.ai |

## Videos

Los videos no están en Git, por regla del proyecto (`AGENTS.md` §3). Sin ellos, MATEO muestra un aviso: el reproductor no funciona, pero datos, radar y línea de tiempo sí.

Para el tablero completo, consíguelos con el equipo y cópialos aquí:

| Carpeta | Archivos |
|---|---|
| `dashboard/assets/hero/` | `demo_omni.mp4` |
| `dashboard/media/` | `VIDEO_OMNIMORPH_POST_MATEMATICA.mp4`, `VIDEO_RADAR_POST_MATEMATICA.mp4`, `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4`, `ORIGINAL_L6sbfskaTDQ-720-13.mp4`, `NARRACION_COMPLETA_60S.wav`, `narrations_es.vtt` |

## Límites del chatbot

- Solo atiende conexiones locales, porque cada pregunta gasta cuota de watsonx.ai.
- Las comparaciones y los resúmenes estadísticos los redacta el código, sin LLM.
- Si las cifras de una respuesta de Granite no coinciden con los datos, esta se descarta.
- Aun así puede equivocarse: no detecta afirmaciones falsas con cifras reales ni detalles sin cifras.

## Datos

- `data/partidos/brasil_alemania_2014/PROCEDENCIA.md` documenta el origen, las correcciones y lo que sigue sin confirmar. Entre otros, la posesión y los desgloses por tiempo no tienen confirmación oficial, y el xG es estimado.
- Tras cambiar esos datos, ejecuta `python scripts/export_dashboard_data.py --solo-partido` para actualizar el tablero.

## Pipeline

`run_pipeline.py` no se puede ejecutar desde un clon limpio con los datos reales: `data/raw/`, `data/clean/` y los videos no están en Git.

> [!WARNING]
> Sin `--use-real`, el pipeline **sobrescribe `data/raw/`** con datos sintéticos.
> Además, regenera las narraciones pero no el audio maestro ni los subtítulos, que quedarían desfasados del video.

## Más información

- `AGENTS.md`: reglas del proyecto.
- `bob_sessions/`: bitácora de cada sesión de desarrollo.
- `dashboard/DESIGN.md`: sistema de diseño.
- `implementacion/dashboard/`: versión anterior en Streamlit, conservada como respaldo. Necesita `data/clean/` y sus propias dependencias (`streamlit`, `altair`, `matplotlib`).
