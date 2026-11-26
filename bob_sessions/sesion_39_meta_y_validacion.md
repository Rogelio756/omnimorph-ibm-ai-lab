# Sesión 39 — Meta, funciones y validación de la web

**Fecha:** 2026-11-24 · **Agente:** Claude Code (diseño y revisión) · **Rama:** feat-costa-rica

## Qué se hizo
- Recorrido de las 7 páginas en local y prueba de MATEO, Partido, Transmisión y chat (4 preguntas llegaron a Granite).
- Comparación del radar con el video y prueba de una calibración corregida, fuera del repo.
- Documento `docs/meta_y_funciones.md`: meta fundamental, funciones y correcciones C1–C5.
- Lista de capturas pendientes: `bob_sessions/capturas/README.md`.

## Hallazgos
1. La calibración usa puntos de baja confianza. Con punto excluido, el error mediano es 9.7 m; con filtro de confianza baja a 1.9 m.
2. La crónica de los tramos 1, 6 y 7 contradice el video, y la del 4 afirma posesión sin medirla.
3. «Altura del bloque», «compacidad» y «velocidad de transición» no miden lo que dicen.
4. El chat dijo que el 3-0 fue de penal; los datos no lo dicen. La revisión automática lo marcó PASS.
5. Los monitores comprueban que los datos existen, no que sean correctos.

**Corrige a la sesión 38:** F1, F2, N1 y R4 figuraban como «Cumple» o «Parcial» sin haber contrastado el análisis con el video.

## Pendiente
Compartir la meta con el equipo, implementación por Bob o Gemini y capturas de Bobcoins. Sin cambios de código.

## Pitch
Se revisaron el guion de video (3:00) y el deck de 6 láminas del equipo: `docs/video_demo/pitch_unificado.md`.

## Encargos
`blueprints/encargo_gemini_radar_metricas_cronica.md` (C1–C3) y `blueprints/encargo_bob_chat_y_textos.md` (C4–C5). El 25/11 el usuario compartió con el equipo las funciones, las herramientas y la proyección hasta el viernes 27.
