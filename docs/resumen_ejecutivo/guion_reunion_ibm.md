# Guion de la reunión con IBM (Fernando Maciel) — 2026-11-23

## Antes de empezar
- Abrir la demo por el enlace del túnel de Cloudflare (lo da el equipo el mismo día; cambia cada vez que se levanta).
- **Plan B si el enlace falla:** compartir pantalla con `http://localhost:8600/pages/transmision.html` en la PC del equipo.
- Tener abiertos `docs/resumen_ejecutivo/00_resumen_general.md` y este guion.

## Demo (10 minutos)
| Min | Página | Qué decir |
|---|---|---|
| 0–3 | **Transmisión** | «Así se vería una transmisión con Omnimorph»: marcador, protagonista de la jugada, radar, alineaciones y la voz de MATEO. Señalar la nota «la velocidad está en pruebas»: no mostramos un dato que no es confiable. |
| 3–5 | **MATEO** | Las narraciones las escribe IBM Granite (`ibm/granite-4-h-small`, watsonx.ai). Hacer una pregunta al chat en vivo. |
| 5–7 | **Método** | 9 monitores de calidad (M1–M4), todos en PASS en la última corrida; costo de la corrida: 0,60 RU. Regla: ningún dato sin fuente. |
| 7–8 | **Partido** | Datos del partido con fuentes públicas y validación humana; el xG está marcado como estimado. |
| 8–10 | **Preguntas y pedidos** | Ver abajo. |

## Cifras clave (todas salen del repo)
| Dato | Valor | Fuente |
|---|---|---|
| Duración del clip | 36 s (1080 cuadros) | dashboard/data/mateo_data.json |
| Monitores | 9/9 PASS | dashboard/data/metodo.json |
| Costo de la corrida en watsonx | 0,60 RU | dashboard/data/metodo.json |
| Jugadores con nombre | 10 de 46 (5 validados) | dashboard/data/metodo.json |
| Cuadros con balón detectado | 860 de 1080 | dashboard/data/transmision.json |
| Modelo de IA | IBM Granite `ibm/granite-4-h-small` | AGENTS.md |

## Preguntas difíciles y respuesta corta
- **¿Por qué no hay velocidad?** La calibración de la cámara salta en cada cuadro e infla las cifras; preferimos ocultarlas y decirlo.
- **¿Funciona en vivo?** No: hoy se procesa después del partido.
- **¿Funciona con video de celular / para amateur?** Todavía no se ha probado. Faltan: probar video amateur, mejorar calibración, leer dorsales automáticamente (el modelo probado reconoció 0 de 20 en video real), métricas físicas confiables y reglas de privacidad para menores. Ver `00_resumen_general.md`.
- **¿Cuánto cuesta un partido completo?** Medimos 0,60 RU por clip de 36 s; un partido completo serían unos 150 clips. Falta calcularlo en dinero.
- **¿Qué es propio y qué no?** La detección parte de código abierto (`roboflow/sports`); lo propio es la explicación en español con IBM Granite, la gobernanza con monitores y la experiencia.
- **¿Por qué se cayó el servicio la vez pasada?** Corre en una laptop: Windows la apagó (15/11). Por eso queremos llevarlo a IBM Cloud.

## Qué pedirle a IBM
1. Orientación para llevar la app a **IBM Cloud Code Engine** (URL fija, sin depender de la laptop).
2. Contactos en medios o streaming para un piloto de **Transmisión** con video con derechos.
3. Opinión sobre empezar por **técnicos amateur y academias** (propuesta de Mariana) con un piloto en el Tec.
