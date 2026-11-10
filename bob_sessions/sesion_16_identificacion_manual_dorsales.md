# Sesión 16: revisión del experimento de Bob e identificación manual de dorsales
**Fecha:** 2026-11-09
**Agente:** Claude Code
**Rama:** `feat-costa-rica`
**Retoma:** sesión 14 (datos públicos, Gemini, commit `d2ce7cd`) y sesión 15 (dorsales, Bob, commit `e6a9d25`)

---

## 1. Revisión del experimento de Bob (sesión 15)

- **Lo que se comprobó:** commit en la rama correcta, sin claves en el código y sin cambios sueltos.
- **Cifras:** coinciden con `outputs/experimentos/dorsales/`. Son 3,158 recortes, 308 con número (9.8 %) y 0 de los 20 rastros principales con número.
- **Sesgo del modelo:** de los 308 recortes con número, 185 dicen "5". En rastros donde a simple vista se lee el dorsal (T70 "11", T69 "21", T98 "22"), el modelo responde sobre todo "5" o "17", y el número correcto casi nunca aparece entre sus tres primeras opciones.
- **Matiz a la conclusión de Bob:** el video **sí** muestra la espalda y el número en varios rastros. Lo que no funciona es el modelo. Causa probable: entrenó con recortes ajustados al número y recibe el cuerpo completo con césped.
- **Granite Vision:** no está en el catálogo de watsonx de la cuenta (us-south, 18 modelos, todos de texto, embeddings o series de tiempo). Existe en abierto en Hugging Face (Apache 2.0), pero no se probó.

## 2. Identificación manual

El usuario pidió que la hiciera Claude Code, que Fer la validara después y que se mostrara en el tablero como "por validar".

**Método:**
- Hojas con 10 recortes ampliados por rastro, sacados del video original, para los 20 rastros con más tiempo visible.
- Un dorsal se asigna solo si se lee y existe entre los **titulares** de ese color. El clip es el minuto 1–2 del partido, así que solo juegan titulares.

**Resultado:** `data/partidos/costa_rica_skn_eliminatorias_2026/rastros_dorsales_borrador.json`. 13 rastros asignados a 10 jugadores:

| Certeza | Jugadores |
|---|---|
| Alta | Galo #14 (T6), Madrigal #17 (T12+T59), Ugalde #9 (T2+T74), Zamora #21 (T69), Lassiter #11 (T70, T18 por confirmar) |
| Media | Cascante #6 (T33), Brenes #13 (T28), Rogers #11 SKN (T1), Lewis #15 SKN (T36), Sterling-James #22 SKN (T98) |

**Hallazgos:**
- **Jugadores partidos en dos rastros:** T12→T59, T2→T74 y T18→T70 no se solapan en el tiempo. La costura del engine no los unió.
- **T29 cambia de persona:** es de SKN hasta ~cuadro 700 y después sigue a un jugador de CRC.
- **Sin dorsal:** 9 de los 20 rastros principales. Sobre todo de SKN, que suele estar de frente a la cámara, defendiendo.
- **Hojas para que Fer revise:** `outputs/experimentos/dorsales/revision_manual/rastros_1.jpg` a `rastros_4.jpg`, fuera de Git.

## 3. Tablero

- **`scripts/export_dashboard_data.py`:** añade `dorsal`, `jugador`, `certeza` y `validado` a cada jugador de `mateo_data.json`. Usa `rastros_dorsales.json` (validado) si existe; si no, el borrador marcado como no validado. Al pasar el archivo validado, la etiqueta desaparece sola.
- **`mateo.html`:**
  - La lista muestra "#14 Galo" con la etiqueta naranja **POR VALIDAR**; los rastros sin identificar siguen como "Rastro N".
  - La tarjeta indica el número de rastro, la certeza y que está por validar.
  - Los nombres se insertan escapados.
- **Verificado en el navegador:** CRC (#13 Brenes, #14 Galo, #17 Madrigal, #9 Ugalde) y SKN (#15 Lewis, #11 Rogers), sin errores en consola.

## 4. Pendiente

- **Fer:** validar el borrador en `Quien_es_quien` y las alineaciones de Gemini. Después, crear `rastros_dorsales.json` con lo confirmado.
- **Rastros partidos:** unirlos en el tablero o en el engine para que cada jugador aparezca una sola vez.
- **Siguiente experimento de dorsales:** Granite Vision local o reentrenar con recortes propios etiquetados por Fer.
- **Plantilla de Gemini (sesión 14):** revisarla antes de mandarla a Fer.
