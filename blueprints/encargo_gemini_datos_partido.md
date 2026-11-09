# Encargo para Gemini (Antigravity): datos públicos de Costa Rica vs. San Cristóbal y Nieves

**Asignado a:** Gemini en Antigravity
**Preparado por:** Claude Code, 2026-11-09
**Valida después:** Fer, del equipo de análisis

---

## 0. Antes de empezar

1. Lee `AGENTS.md` y la última bitácora, `bob_sessions/sesion_13_dashboard_web_costa_rica.md`.
2. **Trabajas en la misma carpeta y la misma rama que Claude Code, `feat-costa-rica`.** Por eso no cambies de rama, no hagas `stash`, `reset`, `git add -A` ni `git add .`. Para hacer commit, nombra tus archivos uno por uno. Comprueba la rama con `git branch --show-current`.
3. Este encargo es **solo de investigación y llenado de datos**. No toques código.

## 1. Objetivo

Llenar con datos públicos y verificables la plantilla
`data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx`
del partido **Costa Rica vs. San Cristóbal y Nieves**, Eliminatorias Concacaf al Mundial 2026, segunda ronda, jornada 1.

Con esos datos, el chatbot MATEO (IBM Granite) responderá preguntas sobre el partido. **Un dato falso es peor que un dato que falta:** MATEO lo repetiría con seguridad.

## 2. Qué llenas tú y qué no

| Pestaña | Quién | Qué |
|---|---|---|
| Ficha | **Gemini** | Datos generales: fecha, estadio, árbitros, resultado, entrenadores, esquemas, uniformes |
| Alineaciones | **Gemini** | Los dos planteles completos: dorsal, nombre, posición, titular o suplente, minuto de los cambios, capitán, club |
| Eventos | **Gemini** | Goles, tarjetas, cambios y penales con su minuto |
| Estadisticas | **Gemini** | Por tiempo y totales, **solo si una fuente las publica** |
| Fuentes | **Gemini** | Una fila por fuente: nombre, **URL exacta**, qué datos salieron de ahí y fecha de consulta |
| Columna azul «Validación (Fer)» | Fer | **No la toques** |
| Clip_15 y Quien_es_quien | Fer | **No las toques.** Requieren mirar el video |

## 3. Reglas de datos (obligatorias)

1. **Ningún dato sin fuente.** Cada fila lleva en «Fuente (ID)» un ID de la pestaña Fuentes (F1, F2…), y esa fuente lleva su URL exacta, no la portada del sitio.
2. **Orden de confianza de las fuentes:**
   1. Reporte oficial de Concacaf (concacaf.com, match report o centro de partido).
   2. FIFA (fifa.com, inside.fifa.com).
   3. Federaciones: FEDEFUTBOL (Costa Rica) y SKNFA (San Cristóbal y Nieves).
   4. Medios deportivos reconocidos (ESPN, Transfermarkt, Soccerway, FBref, medios costarricenses).
   5. Wikipedia **solo como pista** para encontrar la fuente primaria. Nunca como fuente final.
3. **Si no encuentras un dato, escribe `SIN DATO`.** No estimes, no calcules por tu cuenta y no completes con lo que "suele pasar".
4. **Si dos fuentes no coinciden,** pon el valor de la fuente de mayor confianza, anota la otra en «Nota» como `DISCREPANCIA: <fuente> dice <valor>` y cita ambas en Fuentes.
5. **Estadísticas por tiempo (1T/2T):** casi nunca se publican. Si no aparecen, deja `SIN DATO` en las filas de 1T y 2T y llena solo «Total».
6. **Nombres:** escríbelos como en la fuente oficial, con acentos. En «Nombre (como aparece en la camiseta)» va el apellido en mayúsculas, si la fuente lo muestra.
7. **Equipos:** escribe exactamente «Costa Rica» o «San Cristóbal y Nieves». Las celdas tienen lista desplegable.
8. **Porcentajes** como número, sin el signo: `52.5`.
9. **No borres** las filas grises de ejemplo, las listas desplegables ni las columnas existentes.
10. **Antes de escribir, confirma que es el partido correcto:** misma fase, jornada y rivales. Si existe más de un Costa Rica vs. San Cristóbal y Nieves en esa eliminatoria, por ejemplo ida y vuelta, **detente y anótalo en la bitácora** en lugar de elegir uno.

## 4. Cómo editar el Excel sin romperlo

- Usa Python con `openpyxl`, con el Python del sistema si el `.venv` no lo tiene. Carga con `load_workbook(ruta)`, **sin** `data_only=True`, y escribe solo en celdas amarillas.
- Guarda primero una copia en `outputs/plantilla_respaldo_<fecha>.xlsx`. Esa carpeta está fuera de Git.
- Al terminar, abre el archivo otra vez y comprueba tres cosas: que siguen las 8 pestañas, que las listas desplegables siguen (`ws.data_validations`) y que no hay celdas amarillas con texto de ejemplo.

## 5. Entregables

1. La plantilla llena, en la misma ruta.
2. **`bob_sessions/sesion_14_datos_partido_gemini.md`** con:
   - El partido confirmado: fecha, sede y resultado, con su fuente.
   - Una tabla por pestaña: filas llenas, filas con `SIN DATO` y discrepancias encontradas.
   - La lista de fuentes consultadas que **no** sirvieron, para que Fer no repita búsquedas.
   - Todo lo que te dejó dudas.
3. La fila nueva en la tabla índice de `bob_sessions/README.md`.
4. **Un solo commit**, con los tres archivos nombrados:
   ```bash
   git add data/partidos/costa_rica_skn_eliminatorias_2026/PLANTILLA_datos_partido.xlsx bob_sessions/sesion_14_datos_partido_gemini.md bob_sessions/README.md
   ```
   Mensaje: `docs(datos): llenar plantilla de Costa Rica vs. SKN con fuentes publicas`. **Sin push.**

## 6. Lo que NO debes hacer

- No toques `implementacion/`, `dashboard/`, `scripts/`, `run_pipeline.py`, `data/raw/` ni `data/clean/`.
- No inventes el minuto del partido que muestra el clip, ni quién aparece en él: eso lo hace Fer.
- No subas a Git videos, `.parquet`, `.env` ni nada de `outputs/`.
