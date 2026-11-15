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
