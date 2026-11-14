# Sesión 29 — Comparativa de las tres evaluaciones

**Fecha:** 2026-11-14 · **Agente:** Claude Code · **Rama:** feat-costa-rica · **Commit evaluado:** 8d60ee5

## Objetivo
Comparar las evaluaciones de Claude Code, Gemini e IBM Bob (sesión 28) y armar una lista única de mejoras.

## Qué se hizo
- `evaluaciones/2026-11-14_comparativa.md`: puntuaciones lado a lado (3.1 / 3.25 / 3.9), las 11 preguntas del chat por agente, hallazgos verificados y lista única de mejoras priorizada.
- Verificación en el navegador a 375×812: Partido no se desborda (`scrollWidth = 375`). Se descarta el hallazgo móvil de Gemini.
- Se descarta que la pestaña Eventos esté oculta (Bob): `partido.js` la muestra cuando hay eventos.
- La caída del servidor que vio Gemini no se reprodujo.

## Conclusión
Los tres coinciden en que la app se puede enseñar con avisos (H = 3). El problema común es el chat con Granite: las preguntas 3 y 4 fallan en las tres pruebas, la 9 en dos, y todas salen como PASS. Las reglas aciertan 6 de 6.

## Siguiente paso
Mejoras 1–3 de la lista (rankings, táctica/recomendaciones y rechazo por regla) antes de la demo con el club. Sin cambios de código en esta sesión. Sin commit.

## Experiencia de usuario (UX) según los tres informes

Sin contar si los datos son correctos, la experiencia se resume en: **contenido de nivel club, presentación todavía de laboratorio.**

### Lo que funciona
- **Partido** es la mejor pantalla para los tres: 5 pestañas que cubren un informe de partido (ficha, fichero, comparativa 1T/2T, goles con mini cancha y 30 eventos).
- **Mateo**: video, radar, métricas y crónica sincronizados sin tirones. El aviso «Toma cerrada · última foto táctica» transmite honestidad.
- **Honestidad visible**: «Datos no disponibles», «Discrepancias resueltas» y «Lo que no afirmamos» generan confianza.
- **Chat por regla**: instantáneo, con preguntas sugeridas y seguimiento («¿y de Costa Rica?»).
- **Móvil**: verificado a 375 px sin desbordamiento; el menú de móvil funciona.

### Problemas de UX, de más a menos grave
| # | Problema | Lo vio | Sugerencia |
|---|---|---|---|
| 1 | La promesa no coincide: «Analizar mi partido» lleva a una demo fija | Claude, Gemini | «Ver partido de muestra» + una línea: «Para analizar el tuyo, contáctanos» |
| 2 | Jerga de ingeniería a la vista (Savitzky-Golay, Block height, W0–W7, Frame, M2.x, POST-MATH, tokens/ms en el chat) | Claude, Gemini | Lenguaje de fútbol en Inicio y Mateo; trazabilidad del chat detrás de un icono «i» |
| 3 | Operaciones en el menú principal (RU, tokens, preguntas de prueba) | Gemini, Claude | Sacarla del menú: enlace en el pie o dentro de Método |
| 4 | El chat no avisa de que una respuesta de IA puede equivocarse: todo sale con el mismo sello PASS | los tres | Distinguir a la vista «Dato verificado» (regla) de «Lectura de la IA, contrástala» (Granite) |
| 5 | Lista de jugadores de Mateo empieza con «Rastro 25/29/8» | Claude, Gemini | Identificados primero; el resto como «Jugador de SKN sin identificar» |
| 6 | Incoherencias pequeñas: 4 s vs. 4,5 s, 2024 vs. 2026, 3-4-2-1 vs. 3-4-3, enlace «Equipo» a `#` | Claude, Gemini | Unificar; en el esquema, mostrar la nota de fuentes |
| 7 | Pantalla de carga (cubo) ~1 s en cada cambio de página | Gemini | Quitarla o mostrarla solo si tarda más de 300 ms |
| 8 | Eventos (30) sin filtros | Gemini | Filtros rápidos: Goles · Tarjetas · Cambios · Remates |
| 9 | Cuadro del chat con barra de desplazamiento y placeholder cortado | Gemini | Una línea, placeholder corto, `overflow-y: hidden` |
| 10 | Diagramas de Fer pequeños en el móvil | Claude | Ya se abren en grande; añadir la pista «toca para ampliar» |
| 11 | Titular «¡Que no te lo cuente tu cuñado!» | divide (Gemini en contra) | Decisión del equipo: mantenerlo en la versión pública y usar un subtítulo serio en la demo con el club |

### Recorrido sugerido para la demo con el club
Inicio (10 s) → Partido (Ficha → Goles → Comparativa) → Mateo (video con marcas y radar) → Método («lo que no afirmamos») → chat solo con preguntas de datos (goles, tarjetas, tiros). Evitar Operaciones y las preguntas abiertas de táctica hasta corregir el chat.

## Plan de mejoras
`evaluaciones/PLAN_MEJORAS_2026-11-14.md` reúne todo para decidir la implementación: resumen, puntuaciones, chat, hallazgos verificados, diagnóstico de por qué el verificador da PASS a respuestas falsas (no comprueba superlativos ni opiniones), catálogo de mejoras por bloques A–F con archivos, esfuerzo y cómo comprobar cada una, 4 fases con un commit por fase y 6 decisiones pendientes (D1–D6). Pendiente de que el usuario y el equipo decidan.

## Organización de la implementación (decidido con el usuario)
- **Claude Code es el cerebro: no implementa.** Escribe los encargos, revisa los cambios contra los criterios de aceptación y corre las comprobaciones. El usuario aprueba cada commit.
- **Fase 1 (chat confiable): IBM Bob.** Fase 2 (primera impresión): Gemini. El reparto completo está en la sección 5.1 del plan.
- La opinión del equipo llega en dos momentos: hoy sobre el plan (D1–D7) y en una nueva fase 3.5, probando la app corregida en un servicio (D7: túnel o IBM Cloud Code Engine).
- Encargo de la fase 1 para Bob: `blueprints/fase1_chat_confiable.md` (A1 rankings, A2 táctica con la lectura de Fer, A3 recomendaciones, A4 otros equipos y A6 tarjetas sin marcas; comprobación sin gasto `scripts/probar_chat_reglas.py` con 20 casos).
- Dato verificado al preparar el encargo: en duelos ganados empatan Cascante y Calvo con 9; Sawyers (7) es el máximo de SKN.
