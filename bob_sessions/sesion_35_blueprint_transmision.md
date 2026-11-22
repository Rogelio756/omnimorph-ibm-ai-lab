# Sesión 35 — Cierre de la ronda 3 e idea de la página «Transmisión»

**Agente:** Claude Code (solo diseño)
**Fecha:** 2026-11-20 y 2026-11-21
**Rama:** `feat-costa-rica`

## 1. Cierre de la ronda 3 de prueba
- Se apagaron el servidor y el túnel a las 22:24 del 20/11. Detalle en `sesion_34_relanzar_prueba.md` §7.
- La bitácora se subió en `d5d96eb`.

## 2. Dos ideas de crecimiento del usuario
1. **Futbolistas amateur** que miden sus estadísticas con sus propios videos, con un ranking para
   reclutadores. Queda para un blueprint propio. Hace falta un video amateur real (con permiso) para
   probar los modelos.
2. **Venta a TV o streaming**, con una transmisión de Magenta TV / Fussball.TV como referencia. El
   usuario compartió 4 capturas: marcador y reloj, etiqueta del jugador, velocidad flotante con
   estela, mini cancha, barra de dominio y panel de velocidades máximas.

Se eligió la idea 2. Claude hizo un boceto con 7 gráficos sobre el clip de Costa Rica, con diseño
propio de Omnimorph y la voz de MATEO como diferenciador.

## 3. Revisión de páginas
- Se cargaron las 8 páginas en local: sin errores de consola ni enlaces rotos.
- **Operaciones** se ve «apagada» para quien entra por el túnel: sus APIs responden 403 fuera de la
  PC, a propósito. El usuario decidió dejarla así por ahora.

## 4. Blueprint de la página «Transmisión»
- Decisiones del usuario: nombre «Transmisión» en el menú (subtítulo «El partido como en la tele, con
  la voz de MATEO»); el clip va del **1:03 al 1:39** del partido, marcador 0-0; nombre del jugador solo
  con certeza alta o media.
- Blueprint: `blueprints/transmision-blueprint.md` (archivo único, 7 pasos, autoauditoría de Claude).
- Encargo: `blueprints/encargo_bob_transmision.md`.
- No se agregan dependencias ni llamadas a LLM. `serve.py` y `mateo_data.json` no se tocan.
- **Sin prueba de humo de los pasos:** se verificó el bloque Bootstrap y los datos de entrada, pero
  no se construyó el paso 1 en una carpeta aparte, porque en este proyecto Claude no implementa.

## Siguiente paso
Bob construye los 7 pasos. Después, revisión visual y la siguiente ronda con el equipo.
