# Método

**1. Qué es —** Método explica cómo Omnimorph pasa del video a las métricas y la narración, y separa los datos observados de los validados o pendientes (dashboard/pages/metodo.html, dashboard/components/metodo.js).

**2. Para quién —** Cuerpo técnico y analistas que revisan la evidencia; televisoras que evalúan la propuesta; IBM y clientes que necesitan entender gobernanza y límites.

**3. Qué muestra**
- Ficha técnica y diagrama del flujo desde video hasta tablero.
- Estado de los monitores de la última corrida.
- Niveles de confianza y límites conocidos.
- Tecnología IBM y controles de gobernanza.
- Lo que el sistema no afirma ni calcula (dashboard/components/metodo.js).

**4. De dónde salen los datos —** `dashboard/data/metodo.json` reúne los resultados de la corrida y sus monitores. El análisis parte del video; los datos del partido se apoyan en fuentes públicas y validación humana (dashboard/components/metodo.js, dashboard/data/metodo.json).

**5. Tecnología IBM —** IBM Granite en watsonx.ai redacta narraciones; M3 revisa modelo autorizado, formato, extensión y coherencia con los datos. M1 cubre percepción, M2 el procesamiento táctico y M4 la sincronización. La corrida costó 0,60 RU (dashboard/components/metodo.js, dashboard/data/metodo.json, AGENTS.md).

**6. Límites honestos —** La corrida pasó los 9 monitores, pero eso no demuestra una precisión global. Solo 10 de 46 jugadores tienen nombre identificado y 5 están validados (dashboard/data/metodo.json). Las velocidades están ocultas porque la calibración de cámara las infla; además, la narración interpreta cifras y requiere criterio de analista (dashboard/components/metodo.js).

**7. Valor —** Permite evaluar la demo con contexto: qué se midió, qué revisó IBM Granite y qué conviene no usar todavía para tomar decisiones.

**8. Siguiente paso —** Crear una referencia etiquetada por personas para medir la precisión del análisis, una necesidad que la propia página reconoce (dashboard/components/metodo.js).
