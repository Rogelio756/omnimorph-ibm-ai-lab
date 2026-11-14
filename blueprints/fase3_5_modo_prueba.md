# Encargo — Fase 3.5: modo prueba para el equipo

- **Implementa:** IBM Bob, modo 💻 Code
- **Diseña y revisa:** Claude Code
- **Rama:** `feat-costa-rica` (base: `63b4603`)
- **Plan general:** `evaluaciones/PLAN_MEJORAS_2026-11-14.md` (fase 3.5, decisión D7)
- **Estado:** listo para empezar

---

## 1. Qué decidió el usuario

| | Decisión |
|---|---|
| Duración | **48 horas** desde que arranca la prueba. Al terminar, la app muestra «La prueba terminó» y el chat deja de responder |
| Chat | **15 preguntas por persona** durante toda la prueba |
| Servicio | **Túnel desde la PC del usuario** (Cloudflare quick tunnel), temporal |

La app se publica por internet con una URL temporal. Por eso el servidor, además de poner los límites, **no debe exponer nada que no haga falta**.

---

## 2. Qué hay que hacer

### 2.1 Arranque en modo prueba (`dashboard/serve.py`)
- Añade estas opciones:
  - `--prueba-horas N`: activa el modo prueba con N horas de duración. Sin la opción, el servidor funciona exactamente como hoy.
  - `--tope-chat N`: preguntas por persona; por defecto 15 en modo prueba.
- **El fin de la prueba se fija al primer arranque y se guarda** en `data/clean/prueba_estado.json` (`inicio`, `fin`, contadores). Si el servidor se reinicia, **no vuelve a empezar**: lee el archivo y respeta el `fin` original. Para empezar una prueba nueva, se borra el archivo a mano; dilo en la ayuda de `--help`. Añade también `--estado <ruta>` y `--opiniones <ruta>` para que las pruebas usen archivos temporales.
- En modo prueba, el servidor escucha **solo en `127.0.0.1`**: el túnel se conecta desde la misma PC.

### 2.2 Cuando se acaba el tiempo
- **Cualquier página** (`GET` de `.html`) devuelve `410` con una página sencilla y con el estilo de la app: «La prueba de Omnimorph terminó el <fecha y hora>. Gracias por probarla.» No enlaza al formulario: ya cerró con la prueba.
- **`POST /api/chat`** devuelve `410` con `{"error": "prueba_terminada"}`, **sin llamar a Granite**.
- Los recursos estáticos (CSS, JS, imágenes) pueden seguir sirviéndose para que la página de cierre se vea bien.

### 2.3 Tope de 15 preguntas por persona
- **Cómo se identifica a una persona:** con una cookie `om_prueba` (identificador aleatorio, `HttpOnly`, `SameSite=Lax`) que se pone en la primera visita. Detrás del túnel, todas las IP llegan iguales, así que no sirven. No guardes nombres, correos ni IP.
- El contador se guarda en `prueba_estado.json`. Solo cuentan las preguntas que **llegan a Granite**: las que responde una regla no gastan RU y no cuentan.
- **Al llegar al tope:** `429` con `{"error": "tope_alcanzado", "tope": 15}`, y el chat lo muestra en lenguaje normal: «Llegaste a las 15 preguntas de la prueba. Gracias. Cuéntanos qué te pareció en el formulario.»
- **Tope global de seguridad:** 300 preguntas a Granite en toda la prueba. Al llegar ahí, el chat solo responde por regla y dice que el resto está pausado.

### 2.4 Qué no se expone por internet en modo prueba
- `GET /api/operaciones/ibm` (con `?forzar=1` llama a IBM Cloud IAM): devuelve `404` en modo prueba.
- **Listado de carpetas:** desactívalo en modo prueba. Por ejemplo, abrir `/data/` no debe listar los archivos.
- Comprueba que no se puede salir de `dashboard/` (`/../.env`, `/%2e%2e/.env`) y que `.env` nunca se sirve. Hoy `SimpleHTTPRequestHandler` con `directory=dashboard` ya lo impide. **Pruébalo y deja la prueba en el script de 2.6.**
- La página Operaciones puede seguir abierta: muestra las preguntas del equipo, y eso sirve para la revisión. Antes de arrancar la prueba se archiva el registro viejo (paso 3.1).

### 2.5 Aviso de prueba en la app
- Nuevo `GET /api/prueba/estado` → `{"activa": true, "fin": "<ISO>", "restantes": <preguntas de esa persona>}`. Fuera del modo prueba: `{"activa": false}`.
- En `dashboard/components/site-nav.js`, si la prueba está activa, muestra una franja pequeña bajo el menú: «Versión de prueba · disponible hasta el <día> a las <hora> · **Danos tu opinión**», con el enlace a `opinion.html` (2.6).
- En el chat, junto al campo de texto: «Te quedan N preguntas».
- **Ya no hace falta `--formulario`:** el formulario está dentro de la app (decisión del usuario, 2026-11-14).

### 2.6 Página «Tu opinión» (guía de 20 minutos y formulario)
- **Nueva página `dashboard/pages/opinion.html`**, con el mismo estilo que las demás (tokens, `site-nav`, `site-credit`). Va en el menú **solo en modo prueba**, como «Tu opinión». En el móvil debe verse sin desplazamiento horizontal.
- **Arriba: la guía**, plegable y abierta la primera vez. Texto exacto:

  > **Cómo probar Omnimorph (20 minutos)**
  > Imagina que eres analista de un club y vas a enseñar esto a tu cuerpo técnico.
  > 1. **Inicio (1 min):** ¿entiendes qué es y para quién?
  > 2. **Mateo (5 min):** reproduce el video, cambia entre «Con marcas» y «Original», mira el radar y la crónica.
  > 3. **Partido (6 min):** recorre las 5 pestañas.
  > 4. **Método (3 min):** ¿te fías de cómo se hizo?
  > 5. **Chat (4 min):** prueba estas tres preguntas y luego pregunta lo que quieras (tienes 15):
  >    «¿Qué jugador de San Cristóbal ganó más duelos?» · «¿Cómo presionó Costa Rica después de perder el balón?» · «¿Qué tarjetas hubo?»
  > 6. **Si puedes, ábrelo también en tu celular.**
  > 7. **Cuéntanos qué te pareció** en el formulario de abajo.

  Las tres preguntas sugeridas se toman de las sugeridas por el partido cuando existan. Si se escriben en el HTML, que sea en `data/partidos/<partido>/partido.config.json` (bloque `chat`), no a mano en la página.
- **Abajo: el formulario.** Todo es opcional menos las puntuaciones.

  | # | Pregunta | Tipo |
  |---|---|---|
  | 1 | ¿Cuál es tu rol? | Opciones: Analista / Cuerpo técnico / Jugador / Desarrollo o datos / Otro |
  | 2 | ¿Entendiste en 10 segundos qué es y para quién? | 1–5 |
  | 3 | ¿Se entiende sin saber de programación? | 1–5 |
  | 4 | ¿Te sirve para analizar un partido? | 1–5 |
  | 5 | ¿Te fías de los datos? | 1–5 |
  | 6 | ¿Qué tal el chat? | 1–5 (o «No lo usé») |
  | 7 | ¿Funcionó bien? (velocidad, errores) | 1–5 |
  | 8 | ¿Dónde lo probaste? | Computadora / Celular / Los dos |
  | 9 | ¿Se lo enseñarías a un entrenador? | Sí, tal cual / Sí, con avisos / Todavía no |
  | 10 | Lo que más te gustó | Texto, máx. 1000 caracteres |
  | 11 | Lo que te confundió o falló, y dónde | Texto, máx. 1000 |
  | 12 | Una mejora que harías | Texto, máx. 1000 |
  | 13 | Tu nombre (opcional, para poder preguntarte) | Texto, máx. 60 |

  Las escalas 1–5 se ven como 5 botones grandes, con «1 = nada» y «5 = totalmente». Deben poder usarse con el teclado y con el dedo.
- **`POST /api/opinion`:**
  - Valida tipos y longitudes, y añade una línea JSON a `data/clean/opiniones_prueba.jsonl` con `fecha`, `id_prueba` (el de la cookie) y las respuestas. No guarda IP.
  - Una persona puede enviar **hasta 3 veces**: así puede corregir; la lectura se queda con la última.
  - Responde `201`, y la página muestra «Gracias. Tu opinión llegó al equipo.»
  - Fuera del modo prueba responde `404`. Cuando la prueba venció, `410`.
- **Cuando la prueba vence:** la página de cierre (2.2) da las gracias y dice que el formulario ya cerró.
- **Que no se suban a Git:** añade `data/clean/opiniones_prueba.jsonl` y `data/clean/prueba_estado.json` a `.gitignore`. Hoy solo está ignorado `chat_audit.jsonl`, y las opiniones pueden llevar nombres. Comprueba con `git check-ignore`.
- **Si el envío falla** (servidor caído o sin red), la página conserva lo escrito en el navegador (`localStorage`) y muestra «No se pudo enviar. Tu respuesta sigue aquí; vuelve a intentarlo en unos minutos.». No se pierde lo que la persona escribió.
- **Script para leer las respuestas:** `scripts/resumen_opiniones.py` imprime cuántas respuestas hay, la media de cada escala, la cuenta de la pregunta 9 y todos los textos agrupados por pregunta. Claude lo usará para sumar las respuestas al plan.

### 2.7 Comprobación automática (sin gastar RU)
Crea `scripts/probar_modo_prueba.py`. El script:
- levanta el servidor en un puerto libre con `--prueba-horas`, usando un archivo de estado temporal (añade la opción `--estado <ruta>` para no tocar el real);
- simula el paso del tiempo escribiendo un `fin` ya pasado en el archivo de estado.

Debe comprobar:

| # | Caso | Debe |
|---|---|---|
| 1 | Sin `--prueba-horas` | Todo igual que hoy; `/api/prueba/estado` → `activa: false` |
| 2 | Primer arranque con 48 h | Se crea el estado con `fin` = inicio + 48 h |
| 3 | Reinicio | El `fin` no cambia |
| 4 | Pregunta respondida por regla | No cuenta para el tope |
| 5 | Tope alcanzado (con `--tope-chat 2` y un sustituto de Granite, sin llamar a watsonx) | La tercera pregunta da `429` |
| 6 | Otra persona (otra cookie) | Tiene su propio contador |
| 7 | Prueba vencida | Página de inicio `410`; `/api/chat` `410`, sin llamar a Granite |
| 8 | `/api/operaciones/ibm` en modo prueba | `404` |
| 9 | `/data/` | Sin listado de carpetas |
| 10 | `/../.env` y `/%2e%2e/.env` | No devuelven el contenido de `.env` |
| 11 | `POST /api/opinion` válido | `201` y una línea nueva en el archivo de opiniones (usa uno temporal) |
| 12 | Opinión con texto de 5000 caracteres o con una escala de 7 | `400`, sin escribir nada |
| 13 | Cuarta opinión de la misma persona | `429` |
| 14 | `POST /api/opinion` sin modo prueba o con la prueba vencida | `404` / `410` |
| 15 | `resumen_opiniones.py` sobre el archivo de prueba | Imprime las medias y los textos sin error |

Para los casos 4–6, inyecta un sustituto de Granite: una opción oculta `--chat-falso` que responde un texto fijo con `origen: "granite"`. **No llames a watsonx en las pruebas.**

---

## 3. Lo que no hay que tocar

- `implementacion/cloud_agent/` (la lógica del chat) y los datos de los partidos.
- El comportamiento normal del servidor sin `--prueba-horas`.
- **No instales nada ni lances el túnel:** eso lo hace el usuario (sección 4).
- **No hagas commit.**

---

## 4. Cómo lo lanza el usuario (va también en la sesión de Bob)

1. **Una sola vez:** instalar `cloudflared` con `winget install --id Cloudflare.cloudflared`.
2. **Archivar el registro viejo del chat** (y borrar `data/clean/prueba_estado.json` y `data/clean/opiniones_prueba.jsonl` si quedaron de las pruebas): mover `data/clean/chat_audit.jsonl` a `data/clean/chat_audit_antes_prueba.jsonl`.
3. **Terminal 1:**
   ```
   .\.venv\Scripts\python.exe dashboard\serve.py --port 8600 --prueba-horas 48 --tope-chat 15
   ```
4. **Terminal 2:**
   ```
   cloudflared tunnel --url http://localhost:8600
   ```
   El comando imprime una URL `https://<palabras>.trycloudflare.com`. Esa es la que se comparte con el equipo.
5. **Antes de compartir:** abrir la URL del túnel desde el celular con datos móviles (no con el wifi de la casa), recorrer una página y enviar una opinión de prueba; después, borrar esa línea de `opiniones_prueba.jsonl`.
6. **Durante las 48 h:** la PC debe seguir encendida, con las dos terminales abiertas. Si se reinicia, se repiten los pasos 3 y 4: el tiempo **no** vuelve a empezar, pero la URL del túnel cambia y hay que compartirla de nuevo.
7. **Al terminar:** cerrar las dos terminales. La URL deja de existir.

---

## 5. Qué entregar

1. Los cambios en `dashboard/serve.py`, `dashboard/components/site-nav.js`, el chat y la nueva `dashboard/pages/opinion.html`, más `scripts/probar_modo_prueba.py` y `scripts/resumen_opiniones.py`, **sin commit**.
2. La salida del script con los 15 casos en OK.
3. `bob_sessions/sesion_32_modo_prueba.md` y su fila en el índice.

Si R8–R12 (`blueprints/fase1_revision_claude.md`) siguen pendientes, son de otros archivos y puedes hacerlas en la misma sesión, pero en un anexo aparte.

Si algo no cuadra con el código, **para y pregunta**.
