# Omnimorph — Resumen ejecutivo

Omnimorph convierte video de fútbol en una experiencia para seguir el partido, explorar patrones tácticos y escuchar una crónica en español. La propuesta combina el análisis del clip con información del partido revisada por el equipo, y distingue lo observado, lo estimado y lo que aún no es confiable (dashboard/pages/index.html, dashboard/pages/mateo.html, dashboard/pages/partido.html, dashboard/pages/metodo.html).

| Visual | En una línea |
|---|---|
| Inicio | Presenta Omnimorph y lleva al visitante de la promesa del producto a la demostración. |
| MATEO | Sincroniza video, posiciones, métricas tácticas y crónica para explorar el clip. |
| Partido | Reúne ficha, jugadores, estadísticas, goles y eventos disponibles del encuentro. |
| Método | Explica de dónde salen los datos, qué se valida y cuáles son los límites. |
| Transmisión | Lleva el análisis a una presentación de estilo televisivo con la voz de MATEO. |
| Operaciones | Consola interna para revisar monitores, actividad del chat y conexión con IBM; funciona solo en la PC del equipo. |

## Valor para IBM y potenciales clientes

El concepto muestra cómo una señal de fútbol puede enriquecerse con contexto táctico y narración. IBM Granite (`ibm/granite-4-h-small`, en watsonx.ai) genera las narraciones; la página Transmisión reutiliza esos textos y no hace nuevas llamadas al modelo (dashboard/pages/metodo.html, blueprints/transmision-blueprint.md). Los 9 monitores de calidad hacen visibles los controles del proceso; la última corrida pasó los 9 y costó 0,60 RU de watsonx (dashboard/data/metodo.json).

La demostración usa un clip ya grabado de 36 s: no es una transmisión en vivo. La identificación de jugadores y la calibración de cámara siguen siendo límites relevantes; por eso no se presentan velocidades en km/h en Transmisión (dashboard/components/metodo.js, blueprints/transmision-blueprint.md).

## ¿Por qué la parte amateur todavía no está completa?

Omnimorph funciona hoy con video de transmisión de TV. Llevarlo a jugadores y técnicos amateur es el siguiente paso, y faltan cinco piezas:

1. **Aún no probamos video amateur.** Todo se probó con clips de transmisión (Costa Rica vs. San Cristóbal y Nieves). Un video de celular —cámara en mano, sin la cancha completa a la vista— no se ha pasado todavía por el pipeline.
2. **La calibración de la cámara es el cuello de botella.** Para medir en metros hay que ubicar las líneas de la cancha en cada cuadro. Incluso con video de TV la calibración salta tanto que la velocidad sale inflada (por eso no la mostramos); con celular será más difícil (dashboard/components/metodo.js, blueprints/transmision-blueprint.md).
3. **No sabemos todavía quién es cada jugador de forma automática.** Un modelo de dorsales tuvo 84 % de acierto en imágenes de prueba, pero en el video real no reconoció a ninguno de 20 jugadores (bob_sessions/sesion_15_dorsales_bob.md). Hoy 10 de 46 jugadores tienen nombre, identificados a mano, y 5 están validados (dashboard/data/metodo.json). Sin identidad no hay estadísticas personales ni ranking.
4. **Las métricas físicas aún no son confiables.** Velocidad, sprints y distancia dependen de la calibración. Un ranking para reclutadores con cifras infladas sería injusto para los jugadores.
5. **Faltan reglas de juego limpio y privacidad.** Para comparar jugadores hay que grabar en condiciones parecidas (por ejemplo, ejercicios estándar), y muchos jugadores amateur son menores de edad: hace falta su consentimiento antes de guardar sus datos.

**Lo que sí ya sirve para amateur:** el análisis de equipo (altura del bloque, compactación, qué equipo dominó cada jugada), la crónica en español con IBM Granite y el chat para preguntarle al partido.

## Tres siguientes pasos

1. Grabar un partido o entrenamiento con celular (con permiso) y pasarlo por el pipeline, para medir qué falla con video amateur.
2. Mejorar la calibración de cámara y la lectura de dorsales antes de reconsiderar métricas de velocidad y estadísticas por jugador.
3. Piloto con un equipo del Tec y, para la vista Transmisión, acordar material de video con derechos adecuados para demos externas.
