# Sesión 34 — Caída y relanzamiento de la prueba, causa y blindaje de la laptop

**Fecha:** 2026-11-15 · **Agente:** Claude Code · **Rama:** feat-costa-rica

## 1. Relanzamiento del servicio
- El servicio de la prueba estaba caído: ni `serve.py` (puerto 8600) ni `cloudflared` estaban corriendo.
- El reloj de la prueba se conservó en `data/clean/prueba_estado.json` (fin **16/11/2026 15:08**, hora de México), con sus contadores y opiniones.
- Se relanzó `serve.py --port 8600 --prueba-horas 48 --tope-chat 15` (leyó el estado existente) y `cloudflared tunnel --url http://localhost:8600`, cada uno en una pestaña de la terminal de la app de Claude.
- **Hay una URL nueva de trycloudflare**; la anterior ya no sirve y hay que reenviarla al equipo y a IBM.
- Verificación por la URL pública (IPv4): página 200, `/data/` 403, `.env` 404. Se volvió a comprobar a las 12:10 (200).

## 2. Causa de la caída (registros de Windows)
- Del 14/11 a las 17:00 al 15/11 a la 1:00, la laptop entró varias veces en el modo de espera moderno.
- **15/11 a la 1:29:** `winlogon.exe`, en nombre de `SYSTEM`, inició el apagado del equipo (evento 1074). No fue una falla de la app. Probablemente fue Windows Update, pero no se pudo confirmar.
- 15/11 a las 11:03: el equipo arrancó, pero nada relanza solo el servidor y el túnel.
- Fernando Maciel (IBM) preguntó por la caída. Se redactó para el usuario un mensaje de respuesta: apagado automático de Windows, URL nueva, datos conservados y plan de pasar a IBM Cloud.

## 3. Blindaje de la laptop (lo hizo el usuario en Configuración)
- Suspensión y pantalla en **Nunca**, con corriente y con batería (confirmado con `powercfg`).
- Ahorro de energía **desactivado**.
- Tapa y botón de suspensión con corriente → **No hacer nada**.
- **Windows Update pausado.**
- Riesgos que quedan: corte de luz o de wifi, caída del túnel gratuito, cierre de la app de Claude o de las pestañas. Nadie puede relanzarlo mientras el usuario está fuera.

## 4. Consulta: ¿puede vivir toda la app en IBM Cloud?
Sí. Propuesta (solo análisis, sin cambios):
- `serve.py` en **Code Engine** (URL HTTPS fija, escala a cero); credenciales como **secrets**.
- `opiniones_prueba.jsonl`, `prueba_estado.json` y `chat_audit.jsonl` en **COS o Cloudant**, porque el disco de Code Engine es efímero.
- Medios (~372 MB en `dashboard/`) en **COS**. Operaciones con **App ID** o apagado en la versión pública.
- Cambios de código: aceptar el Host de Code Engine y escuchar en `0.0.0.0`; mover las 3 escrituras a disco; leer las credenciales de variables de entorno.
- El pipeline de percepción (YOLO/torch, GPU) se queda fuera por ahora y sube sus resultados a COS.
- **Decisión del usuario:** se hará **después de recibir la retro del equipo**, con un blueprint brownfield en `blueprints/` que implementarán Bob o Gemini.

## Siguiente paso
- El equipo revisa la app la noche del 15/11. Al regresar, el usuario avisa para verificar que siga en línea.
- Con las opiniones: `scripts/resumen_opiniones.py` → `evaluaciones/PLAN_MEJORAS_2026-11-14.md`.
- Después: blueprint de la migración a IBM Cloud. Sigue pendiente la fase 3 (crónica de Mateo sin «posesión»).

Sin cambios de código.

## 5. Cierre anticipado de la prueba (2026-11-16, ~13:50)
- El usuario cerró la prueba antes de las 15:08 porque necesita la laptop para otro proyecto. Se detuvieron el servidor y el túnel; ya no responden.
- **Resultado:** 0 opiniones en `data/clean/opiniones_prueba.jsonl`. El chat se usó una sola vez (15/11 por la mañana).
- El log muestra visitas el 15/11 (14:09, 17:07 y 22:00) y el 16/11 (4:47 y 12:48), sin contar las verificaciones de Claude. A las 4:47 alguien recorrió inicio, Mateo, partido y método. El 15/11 a las 17:07 alguien abrió la página de opinión sin enviarla. Por el túnel todas las visitas llegan como 127.0.0.1, así que no se distinguen las personas.
- **Aprendizaje:** el formulario no se usó. Conviene pedir la retro de forma directa (mensaje o llamada) o con un recordatorio, y hospedar la siguiente prueba en IBM Cloud para no depender de la laptop.

## 6. Segunda ronda de prueba de 3 h (2026-11-18, 00:54 a 03:54, hora de México)
- A pedido del usuario, se levantó una prueba nueva de 3 horas para volver a probar con el equipo.
- El estado anterior se archivó como `data/clean/prueba_estado_2026-11-14.json`, para que el reloj empezara de cero (`serve.py` reutiliza `prueba_estado.json` si existe).
- `serve.py --port 8600 --prueba-horas 3 --tope-chat 15` y `cloudflared tunnel --url http://localhost:8600`, con una URL nueva de trycloudflare.
- Verificación pública: inicio 200, opinión 200, `/api/prueba/estado` activa (fin 03:54), `/data/` 403, `.env` 404. Esta vez el precheck de cloudflared salió sano en ambas regiones.
- **Cierre de la ronda 2:** el usuario la cerró antes de las 3 h. Resultado: **0 opiniones**. Una persona recorrió la app de 19:17 a 20:37 (inicio, Mateo, partido, método; abrió también la página de Operaciones, cuyas API siguen bloqueadas por el túnel) e hizo **5 preguntas al chat** (2 contaron como Granite). Abrió el formulario de opinión a las 20:09 y no lo envió. Nota: el reloj de Windows saltó durante la sesión (el log pasa de 18/11 01:00 a 17/11 19:17), así que las horas de los registros son aproximadas.

## 7. Tercera ronda de prueba de 1 h (2026-11-20, 19:05 a 20:05, hora de México)
- A pedido del usuario se levantó una prueba de 1 hora para el equipo.
- Se archivó el estado de la ronda 2 como `data/clean/prueba_estado_2026-11-18.json`.
- `serve.py --port 8600 --prueba-horas 1 --tope-chat 15` y un túnel de cloudflared con URL nueva.
- Verificación pública: inicio 200, opinión 200, prueba activa (fin 20:05), `/data/` 403, `.env` 404.
- **Cierre de la ronda 3:** la prueba cerró sola a las 20:05 (410 «Prueba terminada»). El servidor y el túnel se apagaron a las 22:24, a pedido del usuario. Resultado: **0 opiniones y 0 preguntas al chat**. El usuario recorrió la app de 19:07 a 19:29 y abrió el formulario de opinión dos veces sin enviarlo. De 19:29 a 19:48 el video de portada se pidió con ritmo alternado, lo que sugiere un posible segundo dispositivo, sin confirmar. A las 20:01 y 20:03 se pidió solo el HTML de MATEO y de inicio, un patrón compatible con la vista previa de un enlace en WhatsApp o Telegram. Una pestaña siguió pidiendo el video cada 88 s hasta el apagado.
- **Aprendizaje:** con el túnel no se pueden contar visitantes. Propuesta para Bob: registrar un identificador anónimo por visitante (hash de `CF-Connecting-IP` y User-Agent) para saber cuántas personas distintas entran.
