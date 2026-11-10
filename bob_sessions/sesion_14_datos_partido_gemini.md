# Sesión 14 — Llenado de plantilla de datos del partido Costa Rica vs. San Cristóbal y Nieves (Gemini)

**Fecha:** 2026-11-09  
**Agente:** Gemini (Antigravity)  
**Rama:** `feat-costa-rica`  
**Encargo de referencia:** `blueprints/encargo_gemini_datos_partido.md`  
**Archivo entregado:** `data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx`

---

## 1. Confirmación oficial del partido (Regla 10)

Se verificó en las fuentes oficiales de **Concacaf (`F1`)**, **FIFA Match Centre (`F2`, partido ID `400017351`)** y la **Federación de Fútbol de San Cristóbal y Nieves (`F3`)** que la **Segunda Ronda de las Eliminatorias de la Concacaf rumbo a la Copa Mundial de la FIFA 2026** se disputó bajo un formato de **ronda única (single round-robin)** dentro del **Grupo B** (integrado por Costa Rica, Trinidad y Tobago, Granada, San Cristóbal y Nieves y Bahamas), donde cada selección jugó únicamente 4 partidos (2 como local y 2 como visitante).

Por lo tanto, existió **un único enfrentamiento** entre ambas selecciones en esta fase clasificatoria:

| Campo | Valor confirmado | Fuente principal |
|---|---|---|
| **Competición** | Eliminatorias de la Concacaf para la Copa Mundial de la FIFA 2026 | `F1, F2` |
| **Fase / Jornada** | Segunda ronda — Grupo B, Jornada 1 | `F1, F2` |
| **Fecha local** | `2024-06-06` (jueves 6 de junio de 2024) | `F2, F5` |
| **Hora local** | `20:30` (UTC-6, hora de Costa Rica; `02:30 UTC` del `2024-06-07`) | `F2, F5` |
| **Estadio y ciudad** | Estadio Nacional de Costa Rica, San José, Costa Rica | `F2, F5` |
| **Asistencia** | `15 700` espectadores | `F8, F9` |
| **Resultado final** | **Costa Rica 4 – 0 San Cristóbal y Nieves** (descanso: `1 – 0`) | `F1, F2, F3` |
| **Cuarteta arbitral** | Julio César de Jesús Luna Guzmán (central), Jorge Ordóñez (A1), Cristian Alvarado (A2), Cristhofer Corado (4.º) — todos de Guatemala | `F2, F6` |
| **Entrenadores** | Gustavo Alfaro (Costa Rica) / Francisco Molina (San Cristóbal y Nieves) | `F2, F3, F5` |

---

## 2. Resumen de llenado por pestaña, celdas `SIN DATO` y discrepancias

Se respetaron íntegramente las 8 pestañas originales del libro (`LEEME`, `Ficha`, `Alineaciones`, `Estadisticas`, `Eventos`, `Clip_15`, `Quien_es_quien`, `Fuentes`), las validaciones de listas desplegables (`data_validations`), las filas grises de ejemplo (`fila 5`) y las columnas azules de `Validación (Fer)`. Las pestañas `LEEME`, `Clip_15` y `Quien_es_quien` permanecieron intactas.

### 2.1 Tabla resumen por pestaña

| Pestaña | Filas trabajadas | Filas con datos completos | Filas con `SIN DATO` | Observaciones principales |
|---|---:|---:|---:|---|
| **`Ficha`** | 25 (`filas 6–30`) | 22 | 3 (`filas 27, 28, 29`) | `Fila 29` (Clima) en `SIN DATO`. En `filas 27–28` (Uniformes de portero) se registraron los nombres y dorsales (`Patrick Sequeira (23)` y `Julani Archibald (18)`) indicando `SIN DATO de color en crónica escrita` para validación visual de Fer. |
| **`Alineaciones`** | 46 (`filas 6–51`) | 46 | 0 | Planteles completos de 23 convocados por selección (dorsales `1` al `23` en ambos equipos): 11 titulares, 5 suplentes que ingresaron y 7 suplentes en banca sin minutos por equipo. Posiciones estrictamente dentro de la lista desplegable. |
| **`Estadisticas`** | 57 (`filas 6–62`) | 20 | 37 (`filas 7–24`, `26–43` y `61`) | Por Regla 5, en `Primer tiempo` y `Segundo tiempo` solo se llenó `Goles` (`1–0` en 1T y `3–0` en 2T); las otras 18 métricas por mitad quedaron en `SIN DATO`. En `Total` se llenaron 18 de 19 métricas y solo `Recuperaciones` (`fila 61`) quedó en `SIN DATO`. |
| **`Eventos`** | 18 (`filas 6–23`) | 18 | 18 (en columna `Reloj mm:ss`) | 18 eventos cronológicos verificados: 4 goles, 4 tarjetas amarillas y 10 sustituciones (5 por equipo). La columna `Reloj (mm:ss)` tiene `SIN DATO` en las 18 filas porque las actas públicas solo reportan el minuto entero, y `Jugador 2 / Dorsal 2` llevan `SIN DATO` en tarjetas y en el gol sin asistencia (`82'`). |
| **`Fuentes`** | 15 (`filas 6–20`) | 15 | 0 | `F1` a `F15` con URLs canónicas exactas de partidos/artículos (Concacaf, FIFA, SKNFA, Everardo Herrera, ESPN, Transfermarkt, FotMob, Sofascore, Tico Times, La Nación, Radio Columbia, Teletica y Futbol24). Cero enlaces a Wikipedia. |

### 2.2 Discrepancias documentadas en la columna `Nota`

Siguiendo la Regla 2.3, cuando dos fuentes serias discreparon en un valor se eligió la de mayor jerarquía y se dejó constancia explícita en la columna `Nota`:

1. **Fecha del partido (`Ficha`, fila 8):** FIFA (`F2`) y la prensa costarricense (`F5, F13`) registran `2024-06-06` (20:30 hora local UTC-6), mientras que portales europeos o en horario UTC (`F9`, `F11`) muestran `2024-06-07` (`02:30 UTC`). Se colocó `2024-06-06`.
2. **Formación de Costa Rica (`Ficha`, fila 21):** ESPN (`F7`) y FotMob (`F9`) reportan `3-4-2-1`, mientras que Transfermarkt (`F8`) la clasifica como variante `5-2-3 / 3-4-3` por la altura de los carrileros Haxzel Quirós y Ariel Lassiter.
3. **Tiros totales (`Estadisticas`, fila 46):** FotMob/Opta (`F9`) registra `15` tiros totales de Costa Rica (`7` a puerta, `8` fuera, incluyendo `1` bloqueado en el desglose; `10` dentro del área y `5` fuera del área) y `4` de San Cristóbal y Nieves (`1` a puerta, `3` fuera). En cambio, Sofascore (`F10`) contabiliza `23` tiros totales para Costa Rica y `5` para San Cristóbal y Nieves (aunque coincide exactamente en `7–1` en tiros a puerta).
4. **Minuto del segundo gol de Orlando Galo (`Eventos`, fila 9):** FIFA (`F2`), SKNFA (`F3`), FotMob (`F9`) y Sofascore (`F10`) registran el minuto `49'`, mientras que crónicas locales como Everardo Herrera (`F5`) y Tico Times (`F11`) redondean al minuto `50'`.
5. **Minuto del tercer gol de Josimar Alcócer (`Eventos`, fila 21):** FIFA (`F2`), Everardo Herrera (`F5`) y Sofascore (`F10`) indican el minuto `82'`, mientras que la nota oficial de la SKNFA (`F3`) menciona el minuto `83'`.
6. **Minutos de sustituciones (`Alineaciones` y `Eventos`):**
   - Doble cambio de Costa Rica (Aguilera por Brenes y Alcócer por Madrigal): `65'` en prensa oficial local (`F5, F13`) vs. `64'` en FotMob (`F9`).
   - Triple cambio de San Cristóbal y Nieves (Mitchum por Terrell, Edwards por Sawyers, Amory por Shade): `77'` en `F9, F13, F15` vs. `76'` en algunas notas de prensa. Además, el resumen de Radio Columbia (`F13`) omitió por error tipográfico el quinto cambio visitante (`Gvaune Amory #7` por `Tyrese Shade #10`), el cual sí consta en FotMob (`F9`) y Futbol24 (`F15`).
   - Doble cambio de Costa Rica (Taylor por Quirós y Rojas por Zamora): `78'` en `F5, F13` vs. `77'` en Teletica/TUDN (`F14`).
   - Cambio de Joel Campbell por Manfred Ugalde: `81'` en `F5, F13` vs. `82'` en Tico Times (`F11`).

---

## 3. Fuentes consultadas que NO sirvieron (para evitar búsquedas repetidas)

- **Wikipedia (`en.wikipedia.org / es.wikipedia.org`):** Consultada únicamente como pista inicial y descartada como fuente en la pestaña `Fuentes` conforme a la Regla 2.5.
- **Sitio oficial de la FCRF (`fcrf.cr`):** Las notas públicas del sitio web de la Federación Costarricense de Fútbol sobre la fecha eliminatoria de junio de 2024 son comunicados narrativos generales y no exponen una ficha técnica estructurada con desglose de tiros, pases, tarjetas ni minutos exactos de cambios.
- **Resúmenes automatizados sin ID de partido en buscadores:** En una primera consulta genérica sobre FotMob, el resumen indexado mezcló dorsales de otra convocatoria (asignando erróneamente `#1` a Patrick Sequeira y `#9` a Álvaro Zamora). Se descartó de inmediato y se verificó jugador por jugador contra las crónicas costarricenses en estadio (`Everardo Herrera F5`, `Radio Columbia F13`) y el archivo de plantilla `F15`, confirmando los dorsales reales (`Sequeira #23`, `Chamorro #1`, `Cruz #18`, `Ugalde #9`, `Zamora #21`).
- **Desglose estadístico por tiempo (1T / 2T) en Concacaf, FIFA, ESPN y FotMob:** Ninguno de los portales públicos expone en abierto las estadísticas separadas del primer y segundo tiempo para este partido (únicamente el acumulado de 90 minutos), razón por la cual se aplicó `SIN DATO` en las filas `7–24` y `26–43` de `Estadisticas`.

---

## 4. Puntos que dejaron duda (para revisión de Fer)

1. **Color exacto del uniforme de ambos porteros (`Ficha`, filas 27 y 28):** Las crónicas escritas confirman que Costa Rica vistió su tradicional uniforme rojo con pantaloneta azul y San Cristóbal y Nieves jugó totalmente de verde (`F3, F12`), pero ninguna detalla por escrito el color de la indumentaria de los guardametas Patrick Sequeira (`#23`) y Julani Archibald (`#18`). Queda señalado para que Fer lo valide directamente sobre el video.
2. **Dorsales de los 7 suplentes de San Cristóbal y Nieves que no ingresaron al campo (`Alineaciones`, filas 45–51):** Mientras que los dorsales de los 11 titulares y los 5 suplentes que entraron están triplemente confirmados en crónicas (`F5, F13`) y bases de datos (`F9, F15`), los números de camiseta de los 7 jugadores visitantes que permanecieron en la banca (`#1 Trotman`, `#23 Stephens`, `#2 Roberts`, `#13 Myers`, `#16 Saunders`, `#12 Davis`, `#17 Vanterpool`) provienen de los registros de convocatoria/archivo (`F4, F15`) y conviene contrastarlos si se cuenta con la planilla impresa de comisario.
3. **Reloj exacto `mm:ss` en `Eventos` (`filas 6–23`) y `Recuperaciones` totales en `Estadisticas` (`fila 61`):** Ninguna fuente pública escrita publica los segundos exactos de cada evento ni el total agregado de recuperaciones por selección.
