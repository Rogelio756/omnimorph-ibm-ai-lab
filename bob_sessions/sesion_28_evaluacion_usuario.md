# Sesión 28 — Evaluación de la app como usuario

**Fecha:** 2026-11-14 · **Agente:** Claude Code · **Rama:** feat-costa-rica · **Commit evaluado:** `8d60ee5`

## Qué se pidió
Recorrer la app como un usuario o líder de un club, dar retroalimentación para medir el desempeño y preparar el mismo ejercicio para IBM Bob y Gemini.

## Qué se hizo
- `evaluaciones/GUIA_EVALUACION.md`:
  - persona (jefe de análisis de un club de Liga MX), recorrido, 11 preguntas fijas del chat con su respuesta correcta y rúbrica A–H de 1 a 5;
  - formato del informe y prompts para Gemini y Bob.
- `evaluaciones/2026-11-14_claude.md`: la evaluación de Claude Code. Media **3.1/5**; chat 8 de 11 correctas.
- Recorrido en el navegador (puerto 8601): las 5 páginas, el video, las pestañas de Partido, el chat, el móvil a 375 px y los tiempos de carga. Unas 8 llamadas a Granite.

## Hallazgos principales
1. **CRÍTICO:**
   - El chat dio cifras falsas con PASS (Burley «5 duelos», cuando el líder es Sawyers con 7; «14 recuperaciones», que son intercepciones de SKN).
   - Inventó recomendaciones y contradijo el análisis de Fer sobre la presión.
   - La crónica del clip habla de «posesión».
2. **IMPORTANTE:**
   - «Analizar mi partido» lleva a una demo fija.
   - Jerga técnica en Inicio y Mateo, y el top 5 de jugadores empieza con «Rastro 25/29/8».
   - Incoherencias: 4 s contra 4,5 s, 2026 contra 2024, 120 × 70 m, enlace «Equipo» a `#`, «(ESPN/TM)» en las respuestas del chat.
   - Las preguntas abiertas cuestan ≈1,7 RU.
3. **MENOR:** Operaciones expone las preguntas de prueba; hay que limpiar `chat_audit.jsonl` antes de la demo.

## Siguiente paso
Que Gemini y Bob hagan su evaluación con la guía (sin leer antes este informe) y luego armar una lista única de mejoras. Sin cambios de código en esta sesión. Sin commit.
