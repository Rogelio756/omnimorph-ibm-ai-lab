# MATEO

**1. Qué es —** MATEO es el tablero para revisar el video y seguir cómo cambian las posiciones, las métricas y la crónica táctica a lo largo del clip (dashboard/pages/mateo.html).

**2. Para quién —** Cuerpo técnico que explora el juego; aficionados que quieren entender la acción; televisoras que evalúan una capa de análisis; IBM como demostración de IA gobernada.

**3. Qué muestra**
- Video con marcas y video original, con controles de reproducción y audio.
- Radar de jugadores y balón, sincronizado con el video.
- Métricas de bloque, compacidad, presencia y centroides.
- Crónica y transcripción sincronizadas.
- Rastros de jugadores con tiempo visible, mapa de calor y ficha de detalle (dashboard/pages/mateo.html).

**4. De dónde salen los datos —** El tablero carga `dashboard/data/mateo_data.json`, exportado desde los resultados del análisis del clip. Las posiciones provienen de la visión sobre el video; los datos de identificación manual se distinguen de los rastros automáticos (dashboard/pages/mateo.html, dashboard/data/mateo_data.json).

**5. Tecnología IBM —** IBM Granite genera la crónica y el chat mediante watsonx.ai; M3 revisa las llamadas. M1 y M2 cubren percepción y análisis, y M4 la sincronización de voz y tablero. La corrida publicada en Método pasó los 9 monitores (dashboard/data/metodo.json, AGENTS.md).

**6. Límites honestos —** Solo 10 de 46 jugadores tienen nombre identificado (dashboard/data/metodo.json). Un rastro automático no siempre equivale a una persona; los cortes de cámara pueden fragmentar el seguimiento (dashboard/pages/mateo.html, bob_sessions/sesion_09_visual_chat_flotante_y_fichero.md). La velocidad está en pruebas porque la calibración la infla; no debe tratarse como una cifra confiable (dashboard/components/metodo.js).

**7. Valor —** Permite pausar, volver a una jugada y conectar lo que se ve en cancha con una explicación táctica legible.

**8. Siguiente paso —** Contrastar las posiciones y la identidad de los rastros con revisión humana del clip (dashboard/components/metodo.js).
