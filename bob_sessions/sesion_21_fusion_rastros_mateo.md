# Sesión 21 — Unir en MATEO los rastros partidos del mismo jugador

**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`
**Origen:** mejora M-A06 de la auditoría de Bob (sesión 20), ajustada en la revisión de Claude Code.

---

## 1. Problema

El tracking le da otro número a un jugador cuando sale de cuadro. Por eso, en MATEO aparecían dos veces Madrigal (rastros 12 y 59), Ugalde (2 y 74) y Lassiter (18 y 70). El borrador de identificación manual (`rastros_dorsales_borrador.json`) ya agrupaba esos tramos, pero el exportador los trataba por separado.

## 2. Cambio

- **`scripts/export_dashboard_data.py`:**
  - `cargar_dorsales()` guarda ahora la lista `rastros` de cada jugador.
  - La función nueva `fusionar_rastros()` asigna a todos los tramos de un jugador el primer número de su lista (59→12, 74→2, 70→18). Se aplica antes de calcular la moda de equipo, el radar y la lista de jugadores. Si dos tramos coinciden en un cuadro, se queda uno: hubo 1 caso, en el cuadro 545 de 12/59.
  - Solo se unen los tramos que una persona asignó al mismo jugador. **El motor y `data/clean/` no cambian**: el M2.2 sigue reportando 112 → 93.
- **`dashboard/pages/mateo.html`:** el pie de la ficha del jugador dice "Rastros 12 y 59 unidos" cuando corresponde.
- **`dashboard/components/metodo.js`:** el límite "Rastros partidos" añade que los tramos identificados a mano ya se muestran unidos en MATEO.

## 3. Resultado (`mateo_data.json`)

| | Antes | Después |
|---|---|---|
| Jugadores en la lista | 49 | 46 |
| Identificadores en el radar | 89 | 86 |
| Madrigal | 2 filas | 1 fila, 34,1 s visible (rastros 12 y 59) |
| Ugalde | 2 filas | 1 fila, 30,7 s (rastros 2 y 74) |
| Lassiter | 2 filas | 1 fila (rastros 18 y 70) |

Las ventanas tácticas y las narraciones quedan iguales.

## 4. Verificación

- Export con `--no-media`. Se comparó el JSON antes y después: desaparecen los IDs 59, 70 y 74, y las ventanas no cambian.
- MATEO (preview `mateo-web`): 0 errores de consola. En la lista de Costa Rica, Madrigal aparece una sola vez, el primero, con el pie "Rastros 12 y 59 unidos · dorsal leído a mano, certeza alta · por validar".
- Página Método: muestra la frase nueva en "Rastros partidos".

## 5. Límite

El video con marcas ya renderizado muestra el número original del tramo (59, 74, 70). El radar y la lista usan el número unido. El pie de la ficha explica la equivalencia.
