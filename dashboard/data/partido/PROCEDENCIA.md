# Procedencia — Brasil 1–7 Alemania (2014)

**Origen:** [FerTC8/omnimorph-brasil-alemania-2014](https://github.com/FerTC8/omnimorph-brasil-alemania-2014), commit `7dc3661`.
**Migrado y corregido:** 2026-11-04 (ver `bob_sessions/sesion_08_*`).

Los archivos de esta carpeta **no son una copia idéntica** del origen: incluyen las correcciones de abajo.
`FUENTES.md` sí es una copia sin cambios, así que donde difiera de este documento, prevalece este documento.

| Origen | Destino |
|---|---|
| `02_partido_completo/` | `partido/` |
| `01_primer_gol_muller/` | `gol_muller/` |
| `assets/` | `assets/` |

## Correcciones aplicadas

| Dato | Antes | Ahora | Por qué | Estado |
|---|---|---|---|---|
| Tiros a puerta de Alemania, 1T / 2T | 9 / 1 | 7 / 3 | Alemania marcó 2 goles en el 2T, imposible con 1 tiro a puerta. Valor derivado: goles + atajadas de cada tiempo | Derivado |
| Tiros fuera/bloqueados de Alemania, 1T / 2T | 1 / 3 | 3 / 1 | Ajuste para que el total de tiros de cada tiempo siga cuadrando (10 y 4) | Derivado |
| Posesión total, Brasil–Alemania | 47–53 | 52–48 | 47 no es compatible con 47 en el 1T y 56 en el 2T; 52–48 es el valor de FIFA según Wikipedia (ref. 29) | Fuente secundaria |
| Distancia a portería de los 8 goles | Solo eje X | Euclidiana (X e Y) | Calculada con las coordenadas del propio archivo. Antes Schürrle 79' marcaba 8.8 m y son 13.7 m | Calculado |
| Distancia del gol de Müller en `gol_muller_min11.json` y `radar_gol_muller.svg` | 9.2 m | 11.3 m | Debe coincidir con la cronología | Calculado |

Se añadió el bloque `notas_calidad_datos` a `estadisticas_partido.json`, solo en el JSON. Las demás claves se conservan.

## Verificado contra el reporte oficial FIFA (Partido 61)

Marcador 1–7 (0–5), asistencia 58.141, minutos jugados, tiros totales 18 y 14, faltas 11 y 14, y la amarilla de Brasil.

El reporte da tiros 18/13 y 14/12. Su segundo número equivale a `a puerta + bloqueados` (8+5 y 10+2), de modo que los totales 8 y 10 de este dataset **no son un error**.

## Sin verificar

Quien muestre estos datos debe indicarlo; el chatbot debe tratarlos con la misma cautela.

- **Posesión total:** depende de la fuente. FIFA vía Wikipedia 52–48, ESPN 51–49, footballcritic 47–53. No se pudo abrir la página archivada de FIFA ni el reporte técnico TSG.
- **Posesión por tiempo (47–53 y 56–44):** no se encontró fuente pública.
- **Desglose por tiempo de tiros, atajadas, pases y recuperaciones:** tampoco se encontró fuente pública.
- **xG:** estimado con modelos genéricos, no es un dato oficial.
- **Telemetría de `muestra_telemetria_muller.json`:** 21 muestras (1 de cada 10 frames de un tramo de 201). La velocidad máxima de los jugadores es 1.4 m/s en plena jugada de gol, muy baja para tracking real, por lo que debe tratarse como ilustrativa.
- **Separación de 3.4 m y velocidad de remate de 78.4 km/h:** sin fuente independiente.
