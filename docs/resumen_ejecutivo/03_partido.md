# Partido

**1. Qué es —** La página Partido reúne el contexto del encuentro y sus datos disponibles en secciones fáciles de recorrer (dashboard/pages/partido.html).

**2. Para quién —** Aficionados que quieren repasar el encuentro; cuerpos técnicos y televisoras que necesitan contexto; IBM como ejemplo de datos con procedencia explícita.

**3. Qué muestra**
- Ficha previa del partido y avisos sobre calidad de datos.
- Fichero de jugadores.
- Comparativa de estadísticas por tiempo cuando hay datos disponibles.
- Goles y, si existen, eventos asociados (dashboard/pages/partido.html, dashboard/components/partido.js).

**4. De dónde salen los datos —** La página carga `dashboard/data/partido/partido.json`. La ficha y las estadísticas se documentan con sus fuentes y notas de procedencia, y fueron validadas por una persona del equipo (dashboard/components/partido.js, dashboard/data/metodo.json).

**5. Tecnología IBM —** Granite no reemplaza las fuentes del partido ni la validación humana. M3 gobierna las llamadas del narrador; M1, M2 y M4 corresponden a percepción, procesamiento táctico y sincronización (dashboard/data/metodo.json, AGENTS.md).

**6. Límites honestos —** La página marca el xG como estimado y advierte que los desgloses por tiempo y la posesión total no tienen confirmación oficial (dashboard/components/partido.js).

**7. Valor —** Da contexto de partido que el video por sí solo no ofrece y ayuda a convertir la revisión de una jugada en una historia más completa.

**8. Siguiente paso —** Mantener visibles la procedencia y las advertencias cada vez que se actualicen los datos (dashboard/components/partido.js).
