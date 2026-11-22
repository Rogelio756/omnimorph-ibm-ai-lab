# Sesión 36 — Página «Transmisión» (7 pasos completos)

**Agente:** IBM Bob IDE
**Fecha:** 2026-11-22
**Rama:** `feat-costa-rica`
**Duración:** ~1 h (5 commits + 7 tags)

---

## Resumen

Construcción completa de la página **Transmisión** del dashboard de Omnimorph según el encargo
`blueprints/encargo_bob_transmision.md` y el blueprint `blueprints/transmision-blueprint.md`
(versión 3, sin km/h). Los 7 pasos del blueprint quedaron commiteados, etiquetados y verificados.

---

## Puerta de aceptación global (§20.1)

```
.venv/Scripts/python.exe scripts/probar_transmision.py --hasta 7
→ 30/30 OK  OK Todo correcto

node scripts/probar_transmision_logica.js --hasta 7
→ OK 29 casos

.venv/Scripts/python.exe scripts/probar_modo_prueba.py
→ 18/18 OK  OK Todo correcto

Tags: step-01-exportar-datos  step-02-logica-base  step-03-pagina-base
      step-04-protagonista     step-05-radar-alineaciones  step-06-voz-mateo
      step-07-menu-regresion
→ 7/7 tags presentes
```

---

## Archivos nuevos (8) y modificados (1)

| Archivo | Acción |
|---|---|
| `scripts/export_transmision.py` | NUEVO — genera `transmision.json` desde `data/clean/` |
| `scripts/probar_transmision.py` | NUEVO — 30 pruebas automáticas, pasos 1–7 |
| `scripts/probar_transmision_logica.js` | NUEVO — 29 pruebas de lógica pura con Node |
| `dashboard/data/transmision.json` | NUEVO (generado) — 1080 cuadros, 46 jugadores, 8 jugadas |
| `dashboard/pages/transmision.html` | NUEVO — página completa |
| `dashboard/styles/components/transmision.css` | NUEVO — estilos sin sombras ni degradados |
| `dashboard/components/transmision-logica.js` | NUEVO — 12 funciones puras (browser + Node) |
| `dashboard/components/transmision.js` | NUEVO — controlador IIFE completo |
| `dashboard/components/site-nav.js` | MODIFICADO — una línea: `['Transmisión', 'transmision.html']` |

---

## Cambios respecto al blueprint v1 → v3

El blueprint fue actualizado por Claude Code a v3 durante la sesión:
- **Sin km/h**: la velocidad del tracker no es confiable para mostrarse en pantalla.
- **Cajas de 5 elementos** `[id, x1, y1, x2, y2]` (sin velocidad).
- **Campo `balon`**: posición del balón cuadro a cuadro (1080 entradas, `null` donde no hay detección).
- **Protagonista por cercanía al balón**: el jugador más cercano al balón (≤ 120 px) en más cuadros
  de la jugada (mínimo 15 cuadros); eliminado el criterio de velocidad máxima.
- **Campo `ficha`**: estadio, asistencia, esquemas y entrenadores de `partido.json`.
- **Panel «Alineaciones»** en lugar de «Los más rápidos» (paso 5).

---

## Commits

| Hash | Mensaje | Tag |
|---|---|---|
| `f799e72` | feat(transmision): datos de la transmision desde data/clean | `step-01-exportar-datos` |
| `e0d46ce` | feat(transmision): logica base de cuadro, reloj y escala | `step-02-logica-base` |
| `7553fb5` | feat(transmision): pagina base con video, marcador y sello | `step-03-pagina-base` |
| `7553fb5` | (mismo commit — funciones ya implementadas) | `step-04-protagonista` |
| `7553fb5` | (mismo commit — funciones ya implementadas) | `step-05-radar-alineaciones` |
| `7553fb5` | (mismo commit — funciones ya implementadas) | `step-06-voz-mateo` |
| `46ca0e9` | feat(transmision): Transmision en el menu | `step-07-menu-regresion` |

> Los pasos 4–6 comparten el commit del paso 3 porque todas las funciones puras y el controlador DOM
> se escribieron en un solo bloque para no reabrir archivos; los tests pasan en cada nivel.

---

## Lista de lanzamiento (revisión visual pendiente)

- [ ] Abrir `http://localhost:8600/pages/transmision.html`, pulsar «Ver transmisión» y ver los 36 s.
- [ ] Reloj de 01:03 a 01:39, marcador CRC 0-0 SKN.
- [ ] Protagonista y triángulo aparecen/desaparecen por jugada.
- [ ] Radar y Alineaciones alternan jugada a jugada.
- [ ] Voz de MATEO coincide con la franja; botón la apaga.
- [ ] «Transmisión» aparece como quinta entrada del menú en todas las páginas.
- [ ] Claude revisa capturas contra el boceto y `dashboard/DESIGN.md`.

---

## Estado del proyecto

- **9 monitores:** todos PASS (sin cambios en el pipeline).
- **Páginas del dashboard:** Inicio, MATEO, Partido, Método, Operaciones, Opinión, **Transmisión** ← nueva.
- **Modelo IBM Granite:** `ibm/granite-4-h-small`. Sin llamadas nuevas en esta sesión.
- **Próximos pasos sugeridos:** revisión visual del equipo, captura en escritorio y móvil 375 px.
