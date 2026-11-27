# Guion de la reunión con IBM (Fernando Maciel), 27/11/2026

Formato: en línea, compartiendo pantalla. Objetivos: mostrar los avances desde el 23/11 y resolver dudas del lab.
Reemplaza al guion del 23/11, que tenía cifras ya corregidas (0.60 RU, «9/9 PASS»).

## Antes de conectarte (5 minutos)
1. La app corre en tu computadora: `http://localhost:8600/pages/index.html`. Si se cayó, levántala con:
   `.venv\Scripts\python.exe dashboard\serve.py --port 8600`
2. Abre estas pestañas en este orden: **Inicio → Transmisión → MATEO → Método**.
3. Espera a que el chat diga que está listo (tarda unos segundos al arrancar). Ya se comprobó que responde «¿Cómo fue el 3-0?».
4. Ten a mano el video `outputs\animacion\recreacion_tv.mp4` (la recreación con datos).
5. Al compartir pantalla, comparte **solo la ventana del navegador**, no la terminal ni el `.env`.

## Demo (10 minutos)
| Min | Pantalla | Qué decir |
|---|---|---|
| 0–1 | **Inicio** | Dos entradas: «Prueba MATEO» para analizar y «Disfruta el partido» para la vista estilo TV. |
| 1–3 | **Transmisión** | Marcador, radar abajo al centro y paneles laterales con datos curiosos que escribió Granite. Todo sale de un clip de 36 s ya grabado. |
| 3–6 | **MATEO** | Botón «Con marcas»: detecta jugadores, separa equipos y ubica a cada uno en la cancha. La crónica de 8 tramos: **Granite escribió 5 y 3 son plantilla**, porque ahí el monitor rechazó lo que contradecía los datos. Una persona revisó los 8 contra el video. |
| 6–7 | **Chat** | Preguntar «¿Cómo fue el 3-0?» y «¿Cuántos kilómetros recorrió Galo?» (responde que no hay ese dato). Las preguntas de datos se responden con reglas; las tácticas abiertas van a Granite. |
| 7–9 | **Método** | 9 comprobaciones automáticas, radar con error mediano de 2.4 m, límites dichos en claro (no es tiempo real, 93 identificadores para unas 25 personas). Costo de la corrida: **0.0013 USD**, unos 14 mil tokens. |
| 9–10 | **Animación** | La jugada recreada solo con nuestros datos y el ángulo de la cámara de TV, sin un píxel de la transmisión. Sirve para el video si no podemos usar la imagen del partido. |

## Avances desde el 23/11 (para decirlo en 1 minuto)
- **Radar recalibrado** con las líneas de la cancha: el error mediano bajó a **2.4 m** (90 % de los puntos a 3.2 m o menos).
- **Monitor M3 reforzado**: exige nombrar al equipo que tiene el territorio, revisa «mitad rival / su mitad» contra el % y rechaza redacciones engañosas.
- **Crónica nueva con Granite**: 5 de 8 tramos; 3 con corrección humana de redacción, registrada en la auditoría.
- **Chat**: los datos del partido se responden por regla (62 de 62 preguntas de prueba); ya no inventa jugadas.
- **Transmisión** con paneles laterales y portada nueva.
- **Costo en dólares** con el precio público de IBM, en vez de RU estimados.
- **Animación** de la jugada a partir de los datos.
- **Entregables** 2, 3 y 4 preparados (problema y solución, tecnología, exportaciones y capturas de Bob).
- **Prueba abierta de 12 h** (26 al 27/11): unas pocas visitas, **0 preguntas al chat y 0 opiniones**. Decirlo tal cual si pregunta.

## Dudas para resolver con Maciel
1. **Video del partido en YouTube.** ¿Podemos mostrar unos segundos de la transmisión en el video de entrega, o mejor solo la animación? Riesgo: reclamo de Content ID o retiro.
2. **Despliegue.** ¿Confirma que durante el lab la app debe correr local y no en IBM Cloud? (GuideBob, págs. 32 y 42, según la libreta del programa).
3. **watsonx Orchestrate.** La herramienta quedó preparada (OpenAPI) pero no está en el flujo. ¿Es obligatorio usarlo o basta con Granite en watsonx.ai?
4. **Otros asistentes.** Además de IBM Bob usamos Claude Code y Gemini, y está registrado en la bitácora. ¿Lo mencionamos en el video o solo Bob?
5. **Entregables.** Fecha límite, si el video va público o no listado, qué rama revisan (hoy el trabajo está en `feat-costa-rica`, falta pasarlo a `main`) y si los títulos del deck deben ir en inglés.
6. **Costo.** ¿Les interesa ver el costo en el pitch? Tenemos 0.0013 USD por corrida medido con tokens reales.

## Preguntas difíciles y respuesta corta
- **¿Funciona en vivo?** No. Se analiza un clip ya grabado; la corrida tarda unos 30 s.
- **¿Con video de celular?** Todavía no se ha probado; solo planos amplios de TV. Es el siguiente paso.
- **¿Por qué Granite solo escribió 5 de 8?** En 3 tramos contradecía los datos y el monitor lo rechazó; ahí entra la plantilla. Preferimos eso a publicar algo falso.
- **¿Por qué no hay velocidad?** No es confiable con la calibración actual; está oculta y lo decimos.
- **¿Qué es propio?** La detección parte de código abierto (`roboflow/sports`). Lo propio: la calibración por líneas, el motor táctico, la crónica con Granite y su monitor, el chat con datos y la web.
- **¿Cuánto cuesta un partido completo?** Proyección, no medido: unos 150 clips, unos 0.20 USD de Granite, sin contar la computadora que procesa el video.

## No decir
«verificado», «tiempo real», «agéntico», «reconoce a cada jugador», velocidad, posesión del clip, «0.60 RU» ni «1.84 RU».
