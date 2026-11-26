# Encargo para IBM Bob: chat y textos (C4–C5)

**Asignado a:** IBM Bob IDE (modo Code, una tarea nueva por paso) · **Preparado por:** Claude Code, 2026-11-25
**Plazo:** hoy, miércoles 25, antes de las 18:00. **Presupuesto:** quedaban ~24 Bobcoins el 23/11; no leas datos grandes ni corras el pipeline.
**Por qué:** `docs/meta_y_funciones.md` §4.

## 0. Reglas

1. Lee `AGENTS.md` y este archivo. Nada más hasta que haga falta.
2. Rama `feat-costa-rica`. Sin `stash`, `reset --hard`, `git add -A` ni `git add .`.
3. **Antes de cada commit muestra el diff y espera la aprobación del usuario.** El push también.
4. Gemini trabaja a la vez en la misma carpeta. **Solo tocas los archivos de §1.**
5. Sin llamadas nuevas a ningún modelo. No leas ni muestres `.env`.
6. Si un paso falla tres veces por la misma causa, detente y repórtalo.

## 1. Archivos tuyos

`implementacion/cloud_agent/chat_agent.py`, `scripts/probar_chat_reglas.py`, `dashboard/pages/{index,partido,transmision,metodo,opinion}.html`, `dashboard/components/{partido,transmision,metodo}.js`, `README.md`, `docs/resumen_ejecutivo/{00_resumen_general,02_mateo}.md`.

**No toques:** `mateo.html`, `data-adapter.js`, `omnimorph_engine.py`, `agent_narrator.py`, `governance_monitor_m3.py`, `data/`, `dashboard/data/` (son de Gemini).

## 2. Paso 1 · Chat (C4) — lo más importante

En `chat_agent.py`, nueva `respuesta_goles(pregunta, datos, historial)` llamada desde `respuesta_por_regla`, después de `respuesta_sin_datos` y antes de `respuesta_eventos`.
- Se activa con preguntas sobre quién marcó, cada gol, cómo fue un gol o la jugada (en plural o de un gol: «el tercer gol», «el 3-0», «el de Alcócer», «al 82»). Conserva las reglas actuales de rankings y de «mejor gol».
- Por cada gol pedido: marcador, minuto, anotador, asistencia (o «sin asistencia») y el texto de `jugada` **copiado tal cual**, sin el marcador repetido.
- Todo sale de `datos["goles"]["lista"]`. Sin Granite. `origen = "regla"`.
- Tiene que servir también con el partido de Brasil: si un gol no tiene `jugada`, muestra solo los datos.

En `_ventanas_clip()`: si el tramo trae `equipos` y `territorio` (contrato de abajo), pásalos al contexto con nombres claros. Si no los trae, pasa **solo** `ventana`, `t0_s` y `t1_s`: los campos viejos están mal nombrados. Que no truene con ninguno de los dos formatos.

```json
{"window_id":"W0","t0":0.0,"t1":4.5,"territorio":"CRC","dominant_team":"CRC",
 "equipos":{"SKN":{"posicion_m":44.0,"pct_campo_rival":8,"largo_m":20.1,"ancho_m":31.5},"CRC":{}}}
```
En `mateo_data.json` la ventana usa `id` en vez de `window_id`.

**Pruebas nuevas en `probar_chat_reglas.py`:**
- «¿Quién marcó cada gol y cómo fue la jugada?» → regla; contiene los 4 anotadores; no contiene «penal» ni «de primera».
- «¿Cómo fue el 3-0?» → regla; contiene «Alcócer» y «presión alta»; no contiene «penal».
- «¿Quién fue el mejor jugador según FotMob?» → sigue igual que hoy.
- `_ventanas_clip()` con formato nuevo y con formato viejo.

**Listo cuando:** `.venv/Scripts/python.exe -X utf8 scripts/probar_chat_reglas.py` da todo OK (hoy: 34/34) más los casos nuevos.

## 3. Paso 2 · Textos de la web (C5)

| Archivo | Cambio |
|---|---|
| `index.html:212` | «Posición, territorio, largo y ancho visibles de cada equipo, en tramos de 4,5 segundos.» |
| `transmision.js:388` | Aforo con el mismo formato que Partido (`15,700`); hoy sale `15.700` |
| Método, diagrama | El cuadro «Tablero» incluye Transmisión |
| `metodo.js:317` | Que el territorio que da la narración coincida con los datos y no use palabras sin respaldo |
| `metodo.js:322` | Orchestrate: «La herramienta quedó preparada para IBM watsonx Orchestrate (OpenAPI); hoy no forma parte del flujo.» |
| Método | Si `metodo.json` trae `radar_error`, mostrar «Error del radar: mediana X m; 90 % de los casos hasta Y m». Si no, nada |
| Opinión | Agregar «Transmisión (2 min): mira el partido con la voz de MATEO» y ajustar el total a 22 minutos |

**Listo cuando:** las páginas cargan sin errores de consola en escritorio y en 375 px, y `probar_transmision.py --hasta 7` sale con 0.

## 4. Paso 3 · Documentos

- `README.md`: describe Costa Rica vs. San Cristóbal y Nieves, la meta de `docs/meta_y_funciones.md` §1, las páginas actuales, los límites y cómo arrancar. Brasil–Alemania queda como referencia histórica. No prometas velocidad, posesión del clip ni video de celular.
- `docs/resumen_ejecutivo/00` y `02`: cambia «altura del bloque, compactación, qué equipo dominó» por las métricas nuevas.

## 5. Al terminar

Registra la sesión en `bob_sessions/` (siguiente número libre), agrega **solo tu fila** al índice y anota los Bobcoins usados. Toma una captura del consumo y guárdala en `bob_sessions/capturas/`, sin correos ni llaves a la vista.

**Si se acaban los Bobcoins:** termina el paso 1 y avisa. Los pasos 2 y 3 los puede hacer Gemini.
