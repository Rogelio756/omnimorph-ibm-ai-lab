# Sesión 19 — Página "Método": principios, flujo, confianza y límites

**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`
**Base:** propuesta de Bob con las correcciones de la sesión 18. El plan lo aprobó el usuario.

---

## 1. Qué se hizo

- **`scripts/export_dashboard_data.py` → `export_metodo()`:** escribe `dashboard/data/metodo.json` a partir de:
  - `pipeline_summary.json`: estado y duración de la corrida.
  - `monitor_m1.json` a `monitor_m4.json`.
  - El primer registro de `governance_audit.jsonl`: límite de palabras del M3.
  - `tactical_summaries.json`: duración de cada ventana.
  - La configuración del partido activo: fps y cuadros.
  - `procedencia.validado` y el número de fuentes.
  - `rastros_dorsales*.json`: jugadores y rastros identificados a mano.

  Se ejecuta también con `--solo-partido`.
- **Partido de otra corrida:** `data/clean/` guarda solo la última corrida. Si sus cuadros no coinciden con el partido activo, `coincide_partido` vale `false`. En ese caso, la página muestra el aviso "Otra corrida" en vez de mezclar partidos.
- **`dashboard/pages/metodo.html` + `dashboard/components/metodo.js`:** 6 secciones con las clases de `match-hub.css`, `tabs.css` y `status-chips.css`. No hay CSS nuevo; solo dos estilos en línea para que los chips no se estiren dentro de `.stat`.
  1. **Principios:** ningún dato sin fuente, la IA se marca, valida una persona y solo IBM Granite.
  2. **Flujo:**
     - 5 etapas con su cifra y su chip de monitor.
     - Una tabla "Qué hace / Resultado de la corrida".
  3. **Niveles de confianza:**
     - "Verificado" dice "Todavía nada" mientras `validado` sea falso.
     - "Por validar" enumera los datos del partido y los dorsales a mano.
  4. **Límites:**
     - Velocidades ocultas. Se aclara que el 100 % del M1 significa "se pudo calcular", no "exacta".
     - Dorsales a mano.
     - Rastros partidos.
     - Clip de 36 s.
     - La narración interpreta cifras.
  5. **Gobernanza:** el modelo, las llamadas auditadas, la latencia, el costo en RU y las 4 comprobaciones reales del M3.
  6. **Lo que no afirmamos:** no es tiempo real, no hay un porcentaje global de precisión, no hay xG ni PPDA, solo se probó con planos de TV y Granite no ve el video.
- **Menú:** "Método" se añadió a `site-nav.js` (MATEO, Partido y Método) y a la barra de `index.html`.

## 2. Cifras que muestra con Costa Rica

| Cifra | Valor |
|---|---|
| Cuadros, fps | 1 080 cuadros a 29.97 fps |
| Rastros | 112 → 93 |
| Ventanas | 8 de 4,5 s |
| M3 | 8/8 llamadas, 1 588 ms de media, 0,60 RU |
| M4 | 8 audios, desfase máximo de 19,0 ms (límite de 40 ms) |
| Pipeline | 9/9 PASS en 25,9 s (última corrida) |

## 3. Verificación

- **Navegador** (preview `mateo-web`, `/pages/metodo.html`):
  - 0 errores de consola.
  - En el texto de la página no aparecen "25 fps", "1 170", "0,5287", "Brasil" ni "Alemania".
- **Móvil (375 px):** sin scroll horizontal (`scrollWidth` = 375).
- **Brasil activo** (`OMNIMORPH_PARTIDO=brasil_alemania_2014`):
  - La página carga.
  - Aparece el aviso "Otra corrida", porque `data/clean` es de Costa Rica.
  - Después se volvió a exportar con Costa Rica activo, y `partido.json` quedó igual al del commit.

## 4. Pendiente

- Cuando Fer valide los datos, `validado: true` cambia solo la fila "Verificado".
- Con `rastros_dorsales.json`, los dorsales pasan a validados.
- Al unir los rastros partidos, la cifra de 93 baja sola en la siguiente corrida.
