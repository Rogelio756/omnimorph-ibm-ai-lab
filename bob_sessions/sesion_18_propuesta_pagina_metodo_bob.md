# Sesión 18 — Propuesta de la página "Método" (IBM Bob, modo Ask)

**Fecha:** 2026-11-09
**Agente:** IBM Bob, en modo Ask (sin escribir archivos). El usuario pegó la respuesta y Claude Code la registra aquí.
**Rama:** `feat-costa-rica`
**Tipo:** análisis y propuesta, sin cambios de código

---

## 1. El encargo

Antes de presentar la demo a un club profesional, se consultó a Bob si convenía una página que explicara los principios de investigación y el flujo de trabajo. También se le pidió el texto de cada sección, un diagrama del flujo y una lista de lo que no se debe afirmar.

## 2. Lo que propuso Bob (resumen)

- **Conveniencia:** sí. Es la página que más credibilidad da ante un cuerpo técnico, porque responde "¿de dónde salen las cifras?" y "¿puedo confiar en ellas?".
- **Estructura en 6 secciones:**
  1. Principios.
  2. Flujo de extremo a extremo, con monitores.
  3. Niveles de confianza (verificado, por validar y no disponible).
  4. Límites conocidos (velocidades, dorsales y rastros partidos).
  5. Gobernanza y tecnología IBM.
  6. Navegación.
- **Diagrama:** hacerlo con las clases que ya existen (`.stat-row`, `.section-label`, `.tbl`, chips), sin herramientas externas.
- **Qué no poner:**
  - Un porcentaje global de precisión.
  - "Detectamos todos los jugadores".
  - Velocidades en tiempo real.
  - "IA que entiende el juego".
  - "Cualquier cámara".
  - "Validado por expertos".
  - "Tiempo real".
  - "Partido completo".
  - xG o PPDA.
  - Avales inventados.

## 3. Correcciones de Claude Code

Antes de construir la página, se contrastaron las cifras con `bob_sessions/sesion_12_*.md` y con `data/clean/monitor_m*.json` de la última corrida.

| Bob dijo | Real (Costa Rica, corrida del 2026-11-09) |
|---|---|
| 25 fps | 29.97 fps |
| Latencia de Granite de 1 170 ms | 1 588 ms de media (`monitor_m3.json`). 1 170 ms era de Brasil |
| Costo de 0,5287 RU | 0,5953 RU. 0,5287 era de Brasil |
| Desfase de M4 de 8,6 ms | 19,02 ms (límite de 40 ms) |
| Narraciones de ≤ 30 palabras | El M3 permite hasta 45 palabras |
| "0 menciones inventadas" | El M3 no mide eso: comprueba el equipo dominante |
| El M3 revisa que no haya cifras de velocidad | No lo revisa. Sus 4 comprobaciones son: modelo, formato JSON, largo y equipo dominante |
| "Verificado: marcador 4-0, goles, árbitros" | Nada está validado (`procedencia.validado: false`). Esos datos son "por validar" |
| Las métricas de posición "sí son fiables" | Dependen de la misma calibración: son más estables, pero aproximadas |
| Dorsales: "13 de 20" y "9 sin dorsal" | 10 jugadores identificados a mano en 13 rastros, todos por validar |
| La etiqueta "desaparece sin cambiar código" | Hace falta crear `rastros_dorsales.json` y volver a exportar |
| Orchestrate "publicado y registrado" | Se probó en la sesión 05. No se afirma que esté activo |
| Rama `feat-dashboard-mejoras` | `feat-costa-rica` |

**Lección:** en una página sobre honestidad, cualquier cifra copiada de otro partido le quita credibilidad. Por eso la implementación (sesión 19) lee todas las cifras de los monitores en lugar de escribirlas a mano.
