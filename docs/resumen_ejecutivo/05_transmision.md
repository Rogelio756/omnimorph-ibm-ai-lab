# Transmisión

**1. Qué es —** Transmisión presenta el análisis como una señal televisiva enriquecida con gráficos y la voz de MATEO (dashboard/pages/transmision.html, blueprints/transmision-blueprint.md).

**2. Para quién —** Aficionados que consumen fútbol en pantalla; televisoras y plataformas de streaming que evalúan una experiencia de transmisión; IBM como demostración de narración con IA.

**3. Qué muestra**
- Video con marcador y reloj (01:03 a 01:39 del partido, CRC 0-0 SKN).
- Etiqueta y marca visual del protagonista de cada jugada, con su estela.
- Mini radar y panel de alineaciones, que se turnan.
- Franja de texto de MATEO, con audio que se puede apagar y controles para pausar o repetir.
- En celular, la franja y las alineaciones pasan debajo del video (dashboard/pages/transmision.html).

**4. De dónde salen los datos —** `dashboard/data/transmision.json` se genera con `scripts/export_transmision.py` desde los datos del clip, las posiciones en pantalla y las jugadas; reutiliza las narraciones de `dashboard/data/mateo_data.json`. Las alineaciones salen de los datos del partido validados (blueprints/transmision-blueprint.md).

**5. Tecnología IBM —** IBM Granite en watsonx.ai produjo las narraciones reutilizadas; Transmisión no hace nuevas llamadas al modelo. M3 gobernó la generación original. La sincronía entre video y voz tiene su propio ajuste: se corrige si el desfase pasa de 0,3 s (blueprints/transmision-blueprint.md).

**6. Límites honestos —** La velocidad de los jugadores está en pruebas: la calibración de la cámara la infla, por eso la página no muestra km/h y lo dice debajo del video. Solo 10 de 46 jugadores tienen nombre identificado. El protagonista es el más cercano al balón, no necesariamente quien lo tiene. Es una demo de un clip grabado, no una transmisión en vivo, y el video es de una transmisión con derechos de terceros (dashboard/pages/transmision.html, blueprints/transmision-blueprint.md).

**7. Valor —** Traduce el análisis en una experiencia que un aficionado puede seguir y que un cliente de TV puede evaluar sin explicación técnica.

**8. Siguiente paso —** Probarla con el equipo y conseguir un clip con derechos de uso (o de un socio de medios) para demos externas. La revisión visual en escritorio y celular ya se hizo el 22/11/2026 (bob_sessions/sesion_35_blueprint_transmision.md).
