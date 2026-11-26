# Sesión 40 — Chat y textos (C4–C5)

**Fecha:** 2026-11-25 · **Agente:** Claude Code · **Rama:** feat-costa-rica

## Por qué no la hizo Bob
El encargo era para IBM Bob (`blueprints/encargo_bob_chat_y_textos.md`). Su servidor `us-east.bob.ibm.com` devolvió error 525 (SSL handshake failed) a las 13:37 y en tres comprobaciones a las 13:38. El usuario decidió seguir con Claude y Gemini. No se usaron Bobcoins ni se hicieron llamadas a Granite.

## Qué se hizo
- **Chat (C4):** nueva `respuesta_goles` en `chat_agent.py`. Marcador, minuto, anotador, asistencia y jugada salen de los datos. Acepta marcador, minuto, orden, anotador, asistente, equipo, tiempo y seguimientos («¿y el tercero?»).
- **Ventanas del clip:** con `equipos` y `territorio` pasan con nombres claros; con el formato viejo solo pasan los tiempos, porque las métricas estaban mal nombradas.
- **Pruebas:** `probar_chat_reglas.py` pasa de 34 a 62 casos. El caso 17 cambió: antes exigía que los goles fueran a Granite.
- **Textos (C5):** Inicio sin velocidad de transición y sin «Reconoce a cada jugador»; aforo igual en Partido y Transmisión; Método con Transmisión, Orchestrate y el error del radar (solo si existe el dato); Opinión con Transmisión (22 minutos); Operaciones ya no dice «probado en desarrollo».
- **Documentos:** `README.md` describe el partido actual, y los resúmenes 00 y 02 ya no citan las métricas mal nombradas.

## Verificación
- `probar_chat_reglas.py`: 62/62. `probar_transmision.py --hasta 7`: 33/33.
- Chat en el servidor local: dos preguntas de goles, origen «regla», PASS.
- Inicio, Método, Transmisión y Opinión a 375 px: sin desbordes ni errores de consola en la última página leída.

## Cambios frente al encargo
- Inicio dice «Dónde juega cada equipo y cuánto campo ocupa»: es cierto antes y después de C2.
- La lista de M3 en Método todavía no menciona las palabras prohibidas; se agrega cuando C3 exista.

## Sin verificar
El bloque «Error del radar» con datos reales (espera a C1) y las preguntas que sí van a Granite.
