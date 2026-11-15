# Sesión 33 — Lanzamiento de la prueba con el equipo y con IBM

**Fecha:** 2026-11-14 · **Agente:** Claude Code · **Rama:** feat-costa-rica

## Qué se hizo
- Se lanzó el modo prueba: `serve.py --prueba-horas 48 --tope-chat 15` (inicio 14/11 15:08, **fin 16/11/2026 15:08**, hora de México) y un túnel rápido de Cloudflare (`cloudflared tunnel --url http://localhost:8600`).
- **Bug encontrado al probar desde el celular:** por el túnel, el chat decía «Granite no disponible». Una protección antigua de `serve.py` solo aceptaba Host `localhost`. Claude Code lo corrigió como excepción por urgencia (commit `f82f052`): en modo prueba, el chat acepta Host `*.trycloudflare.com` desde cloudflared, y Operaciones sigue solo local. `probar_modo_prueba.py` da 18/18.
- Se comprobó por la URL pública: páginas, chat (por regla y con Granite), contador de preguntas (15 → 14), formulario (201) y protecciones (`/data/` 403, `.env` 404, Operaciones 403). Las opiniones de prueba se borraron.
- Se redactaron dos mensajes para que el usuario los envíe: uno a su equipo y otro al equipo de IBM.

## Riesgos aceptados para la prueba
Enlace sin contraseña (solo se comparte por mensaje directo). Las cookies se pueden borrar para saltarse los topes por persona; lo limita el tope global de 300 preguntas a Granite y de 12 por minuto. Si algo va mal, se cierra el túnel.

## Siguiente paso
Esperar las opiniones del equipo y de IBM. Luego, `scripts/resumen_opiniones.py` y sumarlas a `evaluaciones/PLAN_MEJORAS_2026-11-14.md`. Si el túnel se cae, relanzarlo y reenviar la URL nueva. Pendiente: fase 3 (crónica de Mateo sin «posesión»).
