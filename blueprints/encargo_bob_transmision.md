# Encargo para IBM Bob: página «Transmisión»

**Asignado a:** IBM Bob IDE
**Preparado por:** Claude Code, 2026-11-21
**Tipo:** construcción de una página nueva del dashboard, en 7 pasos con pruebas.

---

## 0. Antes de empezar

1. Lee `AGENTS.md`, la última bitácora de `bob_sessions/` y **todo** `blueprints/transmision-blueprint.md`.
2. **Misma carpeta y misma rama que Claude Code y Gemini: `feat-costa-rica`.** No cambies de rama ni
   hagas `stash`, `reset --hard`, `git add -A` o `git add .`. En cada commit nombra tus archivos
   (vienen en el `Checkpoint` de cada paso).
3. **Antes de cada commit, muéstrale al usuario lo que vas a subir y espera su aprobación.** El push
   también lo aprueba el usuario.
4. Comandos en Git Bash, desde la raíz del repo. Python: `.venv/Scripts/python.exe`. Node ya está en
   el PATH.
5. Corre el bloque **Bootstrap** de §10 del blueprint. Si alguna línea falla, detente y avisa.

## 1. Qué construir

Sigue §9 del blueprint, paso 1 a paso 7, sin adelantarte. Un paso está listo cuando su `Verify` sale
con código 0 y los anteriores siguen en verde (`probar_transmision.py --hasta N` los vuelve a correr).

| Paso | Entrega |
|---|---|
| 1 | `scripts/export_transmision.py` → `dashboard/data/transmision.json` |
| 2 | `dashboard/components/transmision-logica.js` + pruebas con Node |
| 3 | `dashboard/pages/transmision.html`: video, botón «Ver transmisión», marcador y sello |
| 4 | Protagonista, velocidad flotante y estela |
| 5 | Mini radar y «Los más rápidos» |
| 6 | Franja y voz de MATEO |
| 7 | «Transmisión» en el menú + regresión |

## 2. Lo que no se toca

`dashboard/serve.py`, `dashboard/data/mateo_data.json`, `data/clean/`, el pipeline y las demás
páginas. Solo se modifica una línea de `dashboard/components/site-nav.js` (paso 7). Ninguna llamada
nueva a Granite ni a ningún LLM.

## 3. Al terminar

1. Corre la puerta de aceptación de §20.1 y pega la salida en tu reporte.
2. Registra la sesión en `bob_sessions/` (siguiente número) y actualiza la tabla de
   `bob_sessions/README.md`.
3. Avisa al usuario para la revisión visual de la lista de lanzamiento (§20.1). Claude revisa las
   capturas contra el boceto y `dashboard/DESIGN.md`.

Si un paso falla tres veces por la misma causa, detente y reporta: es un hueco de diseño y lo
resuelve Claude.
