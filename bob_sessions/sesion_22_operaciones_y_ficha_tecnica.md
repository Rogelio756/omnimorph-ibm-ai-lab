# Sesión 22 — Página Operaciones y ficha técnica del MVP en Método

**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`
**Plan aprobado por el usuario:** página nueva Operaciones y comprobación real de la conexión con IBM sin gasto (0 RU).

---

## 1. Qué se pidió

Mientras llegan los datos de Fer, el usuario pidió tres cosas para la demo:
1. Ver cómo trabajan los monitores.
2. Una terminal con el consumo de tokens del chat y el estado de la conexión con IBM.
3. En Método, una ficha técnica con un diagrama de flujo del MVP.

## 2. Cambios

### Datos
- **`scripts/export_dashboard_data.py` → `monitores_detalle()`:** normaliza los 9 monitores de `data/clean/monitor_m*.json` a `{id, nombre, estado, checks[]}`. Cada comprobación tiene `descripcion`, `observado`, `limite`, `unidad` y `pass`.
  - Cada monitor guarda su JSON con otra forma: `checks` en M1 y M4, `details` en M2 y `summary` en M3.
  - El M3 se arma sumando las comprobaciones de cada llamada en `governance_audit.jsonl`: modelo, formato, largo y equipo dominante.
  - No se inventa ningún umbral: si el monitor no guarda límite, queda `null`.
  - El resultado va en `metodo.json` → `monitores_detalle`.

### Servidor (`dashboard/serve.py`)
Las dos rutas nuevas son solo locales, igual que el chat:
- **`GET /api/operaciones/chat`:** devuelve las últimas 15 llamadas de `chat_audit.jsonl` y los totales de hoy y del histórico (preguntas, por regla, a Granite, tokens, RU, latencia, bloqueadas y errores).
  - La pregunta se recorta a 80 caracteres.
  - No incluye respuestas ni contexto.
- **`GET /api/operaciones/ibm`:** hace dos comprobaciones sin generar texto (0 RU):
  - Un `POST` al token de IBM Cloud IAM.
  - Un `GET` al catálogo `foundation_model_specs` de watsonx.ai, que confirma que `ibm/granite-4-h-small` está disponible en la región.

  Además:
  - Guarda el resultado en caché 60 s. Con `?forzar=1` vuelve a comprobar, como máximo cada 10 s.
  - Usa solo `urllib`, sin dependencias nuevas.
  - **Nunca devuelve la clave ni el token.** Si falla, solo devuelve el tipo de error.
  - Orchestrate aparece como "probado en desarrollo · sin comprobación en vivo".

### Página Operaciones (`dashboard/pages/operaciones.html` + `components/operaciones.js` + `styles/components/consola.css`)
- **Servicios:** chips para el servidor local, IBM Cloud IAM (con su latencia), watsonx.ai us-south (Granite disponible, con su latencia), el chat Granite y Orchestrate. También tiene un botón "Comprobar ahora" y la hora de la última comprobación.
- **Monitores:** 9 tarjetas, cada una con su chip PASS/FAIL y sus comprobaciones (observado frente al límite). Cuando hay un límite numérico, lleva barra; por ejemplo, el desfase de M4: 19.0 de 40 ms.
- **Terminal en vivo:** se actualiza cada 5 s mientras la pestaña está visible. Una línea por llamada:
  `hora  granite  in 1,282 · out 116 tok  1,492 ms (1.er token 406 ms)  0.163 RU  PASS`
  - Debajo de cada línea aparece la pregunta.
  - Las respuestas por regla se marcan como "0 RU · sin llamada al modelo". Las bloqueadas y los errores van en rojo.
  - También registra cada comprobación de IBM.
- **Totales de hoy:** preguntas, tokens, RU y latencia, con el histórico como referencia.
- **Narrador:** resumen de la última corrida, tomado de `metodo.json` → `m3`.
- **Menú:** "Operaciones" se añadió a `site-nav.js` y a `index.html`.

### Método (`dashboard/components/metodo.js`)
- **Ficha técnica del MVP:** producto, partido, clip, percepción, motor, modelo de lenguaje, voz, interfaz, gobernanza, ejecución, estado de los datos y última corrida. Las cifras salen de `metodo.json`.
- **Diagrama de flujo en SVG:** Video → Percepción → Motor táctico → Narrador Granite → Voz → Tablero.
  - Cada etapa lleva su cifra y su monitor.
  - Una rama punteada, "Datos del partido · 16 fuentes · POR VALIDAR", llega al Tablero.
  - Es horizontal a partir de 900 px y vertical en móvil. Los colores salen de los tokens.
- **Cambios en las secciones:** la sección de flujo anterior (5 tarjetas y una tabla) se reemplazó por el diagrama, con un enlace a Operaciones. Las demás secciones se mantienen.

## 3. Verificación

- **`/api/operaciones/ibm`:**
  - IAM `ok`, entre 386 y 663 ms.
  - watsonx.ai `ok`, entre 147 y 372 ms, con Granite disponible en us-south.
  - La respuesta no contiene `access_token` ni `apikey`.
- **`/api/operaciones/chat`:** 15 entradas. Totales históricos: 131 preguntas, 62 a Granite, 31 por regla y 19.5 RU.
- **Prueba en vivo:** una pregunta real al chat (1 280 tokens de entrada, 29 de salida, 0.137 RU) apareció en la terminal en menos de 7 s, y los totales de hoy subieron de 11 a 12.
- **Navegador:**
  - Operaciones y Método, sin errores de consola.
  - Diagrama horizontal a 1366 px y vertical a 375 px.
  - Sin scroll horizontal a 375 px: un chip largo desbordaba y se corrigió dejando que los chips se partan.
- **No probado:** la caída de red real (desactivar el Wi-Fi). El código atrapa el error y pone los chips en alerta, pero no se ejecutó.

## 4. Hallazgo

`monitor_m2.json` llama al M2.4 "Ventanas Tácticas de 4.0 s", pero las ventanas reales duran 4.5 s (`tactical_summaries.json`). La página muestra el nombre en español sin la duración, para no repetir el dato equivocado. Falta corregir ese texto en el monitor del engine.
