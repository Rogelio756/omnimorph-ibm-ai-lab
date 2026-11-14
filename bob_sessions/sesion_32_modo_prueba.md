# Sesión 32 — Fase 3.5: Modo prueba + R8–R12

**Fecha:** 2026-11-14  
**Agente:** IBM Bob (modo Code)  
**Rama:** `feat-costa-rica`  
**Blueprint:** `blueprints/fase3_5_modo_prueba.md`  
**Encargo:** Modo prueba para el equipo (túnel Cloudflare, 48 h, 15 preguntas/persona, formulario de opinión) + correcciones R8–R12 en el chat.

---

## Qué se hizo

### A. Modo prueba (`dashboard/serve.py`)

Se añadieron las siguientes opciones a `serve.py`:
- `--prueba-horas N` — activa el modo prueba con N horas de duración (0 = sin modo prueba).
- `--tope-chat N` — preguntas a Granite por persona (defecto: 15).
- `--estado <ruta>` — ruta alternativa para el archivo de estado (útil en tests).
- `--opiniones <ruta>` — ruta alternativa para el archivo de opiniones (útil en tests).
- `--chat-falso` — opción oculta que responde texto fijo sin llamar a watsonx (para tests).

#### Clase `ModoPrueba`
- Guarda el estado en `data/clean/prueba_estado.json` (`inicio`, `fin`, `tope_chat`, `tope_global`, `contadores`, `granite_total`, `opiniones_por_persona`).
- Al primer arranque crea el archivo con `fin = ahora + N horas`.
- Si el archivo ya existe, **no vuelve a empezar**: respeta el `fin` original.
- Para empezar una prueba nueva, el operador borra el archivo a mano.
- En modo prueba el servidor escucha **solo en `127.0.0.1`**.
- `activa()` re-lee el `fin` del archivo en cada request para detectar cambios en caliente.

#### Endpoints nuevos / modificados
| Endpoint | Descripción |
|---|---|
| `GET /api/prueba/estado` | `{"activa": true/false, "fin": "<ISO>", "restantes": <n>}` |
| `POST /api/chat` | Bloquea con 410 si prueba vencida; controla tope por persona (cookie `om_prueba`); solo cuenta preguntas que llegan a Granite |
| `POST /api/opinion` | 404 fuera de prueba; 410 si vencida; 429 si > 3 envíos; 201 OK |
| `GET /api/operaciones/ibm` | 404 en modo prueba |
| `GET /data/` etc. | Listado de directorios desactivado en modo prueba (403) |

#### Protecciones
- Path traversal (`/../.env`, `/%2e%2e/.env`): `SimpleHTTPRequestHandler` con `directory=dashboard/` ya lo impide; verificado en tests.
- Cookie `om_prueba`: `HttpOnly; SameSite=Lax`; 32 hex aleatorios; no guarda IP ni nombres.
- Tope global de 300 preguntas a Granite: al llegar, el chat solo responde por regla.

### B. Aviso de prueba (`dashboard/components/site-nav.js`)

- Consulta `/api/prueba/estado` al cargar.
- Si la prueba está activa, añade enlace «Tu opinión» al menú y una franja bajo el header con la fecha fin y el enlace al formulario.

### C. Chat en modo prueba (`dashboard/components/chat.js` + `chat-widget.js`)

- Elemento `#prueba-restantes` (oculto por defecto) que muestra «Te quedan N preguntas» cuando el servidor incluye `prueba_restantes` en la respuesta.
- Maneja `error: "tope_alcanzado"` (429) con texto en lenguaje natural apuntando a la página «Tu opinión».
- Maneja `error: "prueba_terminada"` (410) con mensaje de cierre.

### D. Página «Tu opinión» (`dashboard/pages/opinion.html`)

- Guía de 20 minutos (plegable, abierta por defecto).
- Formulario de 13 preguntas:
  - Escalas 1–5 (botones táctiles accesibles, `aria-pressed`).
  - Opciones de selección única (rol, dispositivo, enseñarías).
  - Textareas con contador de caracteres (máx. 1000).
  - Nombre opcional.
- Las tres preguntas sugeridas se cargan de `/api/chat/estado` (desde `partido.config.json`).
- Envía `POST /api/opinion`; muestra «Gracias. Tu opinión llegó al equipo.»
- Se ve sin desplazamiento horizontal en móvil.

### E. Lector de opiniones (`scripts/resumen_opiniones.py`)

Imprime cuántas respuestas hay, media de cada escala, conteo de opciones y todos los textos libres agrupados por pregunta.

### F. Script de prueba (`scripts/probar_modo_prueba.py`)

15 casos de prueba, **sin llamar a watsonx** (`--chat-falso`):

```
  #  Estado   Descripción
──────────────────────────────────────────────────────────────────────────────────────────
  1  OK     Sin --prueba-horas → /api/prueba/estado activa: false
  2  OK     Primer arranque 48 h → fin = inicio + 48 h
  3  OK     Reinicio → fin no cambia
  4  OK     Pregunta por regla no cuenta para el tope
  5  OK     Tope alcanzado → tercera pregunta Granite da 429
  6  OK     Otra persona (otra cookie) tiene su propio contador
  7  OK     Prueba vencida → GET html 410; POST /api/chat 410
  8  OK     /api/operaciones/ibm en modo prueba → 404
  9  OK     /data/ → sin listado de carpetas
 10  OK     /../.env y /%2e%2e/.env no devuelven .env
 11  OK     POST /api/opinion válido → 201 + línea nueva
 12  OK     Opinión con escala 7 → 400 sin escribir nada
 13  OK     Cuarta opinión de la misma persona → 429
 14  OK     /api/opinion sin prueba→404 / vencida→410
 15  OK     resumen_opiniones.py imprime sin error
──────────────────────────────────────────────────────────────────────────────────────────
Resultado: 15/15 OK  OK Todo correcto
```

---

## Anexo — R8–R12 (fase 1b, `implementacion/cloud_agent/chat_agent.py`)

| ID | Corrección | Qué se hizo |
|---|---|---|
| **R8** | Ranking por tiempo | Añadido `RE_TIEMPO_RANKING`; si la pregunta menciona 1T/2T, `respuesta_ranking()` devuelve «No hay datos por jugador separados por tiempo» |
| **R9** | Precisión de pases con pocos pases | Para `campo == "precision_pases_pct"`, se exige `pases_intentados >= 15` (o `pases_completados >= 15`); si no hay candidatos, responde que no hay datos suficientes para un ranking representativo |
| **R10** | «Irán a la siguiente ronda» | Se eliminó `"iran"` de `_AJENOS` (ya estaba; ahora es `"seleccion de iran"`). Se añadió `"ronda"` y `"clasific"` a `PALABRAS_FUTBOL` para que la pregunta tenga vocabulario reconocible y no sea rechazada como off-topic |
| **R11** | «¿Se debe confiar en estos datos?» | `RE_RECOMENDACION` ya no captura `debe\w*` a secas: solo captura `debe/debería + correg|mejor|cambi|hacer` |
| **R12** | Viñeta de SKN en respuesta de CRC | El filtro por equipo en `respuesta_tactica()` ahora extrae el sujeto de la viñeta (texto antes de `:**` en `- **...**:`) con `re.match(r"^-\s+\*\*([^*:]+)", linea)` y solo compara el equipo contra ese sujeto, no contra el cuerpo completo de la viñeta |

Script tras las correcciones:
```
Resultado: 34/34 OK  OK Todo correcto
```

---

## Instrucciones para el usuario — cómo lanzar la prueba

1. **Una sola vez:** instalar `cloudflared`:
   ```
   winget install --id Cloudflare.cloudflared
   ```

2. **Preparar el entorno:** mover el log viejo y borrar los archivos de prueba si quedaron de los tests:
   ```
   move data\clean\chat_audit.jsonl data\clean\chat_audit_antes_prueba.jsonl
   del data\clean\prueba_estado.json
   del data\clean\opiniones_prueba.jsonl
   ```

3. **Terminal 1 — servidor:**
   ```
   .\.venv\Scripts\python.exe dashboard\serve.py --port 8600 --prueba-horas 48 --tope-chat 15
   ```

4. **Terminal 2 — túnel:**
   ```
   cloudflared tunnel --url http://localhost:8600
   ```
   El comando imprime una URL `https://<palabras>.trycloudflare.com`. Esa es la que se comparte con el equipo.

5. **Antes de compartir:** abrir la URL del túnel desde el celular con datos móviles (no wifi de casa), recorrer una página y enviar una opinión de prueba; después borrar esa línea de `opiniones_prueba.jsonl`.

6. **Durante las 48 h:** la PC debe seguir encendida, con las dos terminales abiertas. Si se reinicia, repetir los pasos 3 y 4: el tiempo **no** vuelve a empezar, pero la URL del túnel cambia y hay que compartirla de nuevo.

7. **Al terminar:** cerrar las dos terminales. La URL deja de existir.

8. **Para leer las respuestas:**
   ```
   .\.venv\Scripts\python.exe scripts\resumen_opiniones.py
   ```

---

## Archivos modificados (sin commit)

| Archivo | Acción |
|---|---|
| `dashboard/serve.py` | +450 líneas: `ModoPrueba`, `--prueba-horas`, cookies, `/api/opinion`, `/api/prueba/estado` |
| `dashboard/components/site-nav.js` | Franja de aviso + enlace «Tu opinión» en modo prueba |
| `dashboard/components/chat.js` | Manejo de `prueba_restantes`, `tope_alcanzado`, `prueba_terminada` |
| `dashboard/components/chat-widget.js` | Elemento `#prueba-restantes` en el marcado |
| `dashboard/styles/components/site-nav.css` | `.prueba-franja` |
| `dashboard/styles/components/chat.css` | `.composer__prueba` |
| `dashboard/pages/opinion.html` | Nueva: guía 20 min + formulario 13 preguntas |
| `scripts/probar_modo_prueba.py` | Nuevo: 15 casos sin RU |
| `scripts/resumen_opiniones.py` | Nuevo: lector de opiniones |
| `implementacion/cloud_agent/chat_agent.py` | R8–R12 |
| `scripts/probar_chat_reglas.py` | Casos 28–32 (R8–R12) |

**No se hizo commit** (instrucción explícita del blueprint).

---

## Correcciones tras la revisión (Claude Code — `blueprints/fase3_5_revision_claude.md`)

**Fecha:** 2026-11-14 (misma sesión, segunda ronda)

| ID | Problema | Corrección |
|---|---|---|
| **P1** | `index.html` usa `om-nav` propio y no cargaba `site-nav.js`, así que el equipo que entrara por Inicio no veía la franja ni el enlace al formulario | Añadido script inline al pie de `pages/index.html` que consulta `/api/prueba/estado` y, si la prueba está activa, inyecta `<li>Tu opinión</li>` en `#nav-links` y la franja de aviso tras `#main-nav` |
| **P2** | `opiniones_prueba.jsonl` y `prueba_estado.json` podían subirse a Git con nombres de personas | Añadidas ambas rutas a `.gitignore`; verificado con `git check-ignore -v` |
| **P3** | Si falla la red al enviar, el usuario pierde todo lo escrito | Borrador guardado en `localStorage` (`om_opinion_draft`) en cada clic/tecla; restaurado al recargar; borrado al enviar con éxito (201) o tope alcanzado (429); mensaje en el `catch`: «No se pudo enviar. Tu respuesta sigue aquí; vuelve a intentarlo en unos minutos.» |
| **P4** | Sin `PYTHONIOENCODING=utf-8`, el script revienta al imprimir `──` en la consola de Windows (cp1252) | Añadido `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` al inicio de `probar_modo_prueba.py` y `resumen_opiniones.py` |
| **P5** | El ranking de precisión de pases excluía jugadores con pocos pases pero no lo explicaba | Añadida nota «(solo jugadores con al menos 15 pases)» al final de la respuesta cuando el campo es `precision_pases_pct` |

### Caso nuevo en `probar_modo_prueba.py`

Caso 16 — **P1: `index.html` en modo prueba contiene enlace a `opinion.html`:** verifica que el HTML servido incluye la cadena `opinion.html` (inyectada por el script de la franja).

### Resultado final

```
probar_modo_prueba.py:
──────────────────────────────────────────────────────────────────────────────────────────
  1  OK     Sin --prueba-horas → /api/prueba/estado activa: false
  2  OK     Primer arranque 48 h → fin = inicio + 48 h
  3  OK     Reinicio → fin no cambia
  4  OK     Pregunta por regla no cuenta para el tope
  5  OK     Tope alcanzado → tercera pregunta Granite da 429
  6  OK     Otra persona (otra cookie) tiene su propio contador
  7  OK     Prueba vencida → GET html 410; POST /api/chat 410
  8  OK     /api/operaciones/ibm en modo prueba → 404
  9  OK     /data/ → sin listado de carpetas
 10  OK     /../.env y /%2e%2e/.env no devuelven .env
 11  OK     POST /api/opinion válido → 201 + línea nueva
 12  OK     Opinión con escala 7 → 400 sin escribir nada
 13  OK     Cuarta opinión de la misma persona → 429
 14  OK     /api/opinion sin prueba→404 / vencida→410
 15  OK     resumen_opiniones.py imprime sin error
 16  OK     P1: index.html en modo prueba contiene enlace a opinion.html
──────────────────────────────────────────────────────────────────────────────────────────
Resultado: 16/16 OK  OK Todo correcto

probar_chat_reglas.py:
Resultado: 34/34 OK  OK Todo correcto
```

**No se hizo commit** (instrucción del blueprint). Listo para segunda revisión de Claude.
