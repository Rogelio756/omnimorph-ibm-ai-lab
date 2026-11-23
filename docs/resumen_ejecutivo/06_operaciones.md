# Operaciones

**1. Qué es —** Operaciones es una consola interna para revisar el estado del pipeline, el uso del chat y la conexión con servicios IBM (dashboard/pages/operaciones.html).

**2. Para quién —** Exclusivamente el equipo de Omnimorph; no es una pantalla para aficionados, cuerpo técnico ni clientes.

**3. Qué muestra**
- Estado de los servicios locales y comprobaciones de IBM.
- Monitores de la última corrida y sus resultados.
- Actividad y consumo del chat.
- Resumen del narrador de la corrida (dashboard/pages/operaciones.html, dashboard/components/operaciones.js).

**4. De dónde salen los datos —** Los monitores y el resumen del narrador se cargan desde `dashboard/data/metodo.json`; la actividad del chat y la comprobación de IBM dependen de rutas del servidor local (dashboard/components/operaciones.js).

**5. Tecnología IBM —** Permite revisar el estado de watsonx.ai y la disponibilidad de Granite sin generar texto (0 RU). M3 gobierna el uso del modelo; el estado de la corrida resume los controles M1–M4 (dashboard/components/operaciones.js, dashboard/data/metodo.json, AGENTS.md).

**6. Límites honestos —** Solo funciona en la PC del equipo: sus APIs no se exponen por internet a propósito, así que por el enlace público se ve como «servidor apagado» (bob_sessions/sesion_35_blueprint_transmision.md).

**7. Valor —** Da al equipo una vista de diagnóstico y trazabilidad sin exponerla como parte de la experiencia comercial.

**8. Siguiente paso —** Mantener Operaciones fuera de las demos externas y usarla solo para preparar y diagnosticar la corrida.
