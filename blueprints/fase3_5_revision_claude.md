# Revisión de la fase 3.5 (modo prueba) y de R8–R12 — Claude Code

- **Revisado:** los cambios sin commit de IBM Bob (sesión 32)
- **Encargo:** `blueprints/fase3_5_modo_prueba.md`
- **Veredicto:** **casi listo.** El modo prueba funciona de punta a punta. Faltan dos piezas del encargo y hay un hueco en Inicio que haría que parte del equipo no vea el formulario.

## Lo que comprobé y está bien
- **Pruebas automáticas:** `probar_modo_prueba.py` da 15/15 OK y `probar_chat_reglas.py` da 34/34 OK.
- **En vivo** (puerto aparte, archivos temporales):
  - `/api/prueba/estado` responde bien;
  - la franja aparece en Partido, Mateo y Método, y «Tu opinión» está en el menú;
  - `/data/` devuelve 403, `/api/operaciones/ibm` 404 y `/../.env` 404.
- **Formulario:** se envió desde la página, la respuesta se guardó con todos los campos y sin IP, y apareció «Gracias. Tu opinión llegó al equipo.».
- **Vencimiento:** con el `fin` en el pasado, las páginas dan 410 con una página de cierre clara («La prueba de Omnimorph terminó»), y `/api/chat` da 410 sin llamar a Granite.
- **R8, R10, R11 y R12** quedan bien:
  - «más entradas en el segundo tiempo» → «No hay datos por jugador separados por tiempo»;
  - «Irán» ya no se rechaza;
  - «Se debe confiar» ya no se toma como recomendación;
  - en «presión de Costa Rica» ya no aparece la viñeta de SKN.

## Hay que corregir antes de lanzar

### P1 — Inicio no tiene franja ni enlace a «Tu opinión» (importante)
- `pages/index.html` usa su propio menú (`om-nav`) y no carga `site-nav.js`. El equipo entra por Inicio, ve el enlace «Ver partido de muestra» y puede no enterarse nunca de que hay un formulario ni de cuándo acaba la prueba.
- **Corrección:** en modo prueba, Inicio también muestra la franja y añade «Tu opinión» a su menú. Lo mejor es sacar la lógica de la franja a una función compartida que use `site-nav.js` y que también cargue `index.html`.

### P2 — Las opiniones se subirían a Git (importante)
- `git check-ignore` no ignora `data/clean/opiniones_prueba.jsonl` ni `data/clean/prueba_estado.json`. Hoy solo está ignorado `chat_audit.jsonl`, y las opiniones pueden llevar nombres.
- **Corrección:** añádelos a `.gitignore` y comprueba con `git check-ignore -v`. Estaba en la sección 2.6 del encargo.

### P3 — Si el envío falla, se pierde lo escrito (importante)
- `opinion.html` no usa `localStorage`. Si la laptop está apagada o sin red cuando alguien envía, pierde todo lo que escribió.
- **Corrección:** guarda el borrador en `localStorage` mientras la persona escribe (con `try/catch`). Si el envío falla, muestra «No se pudo enviar. Tu respuesta sigue aquí; vuelve a intentarlo en unos minutos.». Al enviar con éxito, borra el borrador. Estaba en la sección 2.6 del encargo.

### P4 — `probar_modo_prueba.py` se cae en la consola de Windows (menor)
- Sin `PYTHONIOENCODING=utf-8`, el script revienta al imprimir la línea `──` (cp1252). Con UTF-8 da 15/15.
- **Corrección:** al inicio, `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`. Haz lo mismo en `resumen_opiniones.py`, que imprime los textos del equipo con acentos. El usuario los va a correr en PowerShell.

### P5 — R9 no dice el mínimo de pases (menor)
- El ranking de precisión ya excluye a quien dio pocos pases, pero no lo dice.
- **Corrección:** añade «(solo jugadores con al menos N pases)» a la respuesta.

## Para cerrar
1. Bob corrige P1–P5 y añade un caso a `probar_modo_prueba.py` para P1: Inicio en modo prueba contiene el enlace a `opinion.html`.
2. Bob añade un anexo «Correcciones tras la revisión» a `bob_sessions/sesion_32_modo_prueba.md`.
3. Claude vuelve a revisar y se propone el commit. Después, el usuario lanza la prueba (sección 4 del encargo).
