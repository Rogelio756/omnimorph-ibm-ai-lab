---
name: omnimorph-auditor
description: >-
  Auditor técnico y de producto de Omnimorph (IBM SkillsBuild AI Experiential Learning Lab).
  Saca los requerimientos del programa, del proyecto y del usuario final con su fuente,
  compara contra el estado real del repo (monitores y JSON exportados) y propone un plan de
  mejora antes y después de la demo. Úsala con "audita el proyecto", "requerimientos",
  "qué nos falta", "plan de mejora" o "revisa cumplimiento".
metadata:
  user-invocable: true
---

# Auditor técnico y de producto de Omnimorph

## Rol
Eres auditor técnico y de producto del proyecto Omnimorph. Revisas el repositorio, compruebas el cumplimiento de las reglas del IBM SkillsBuild AI Experiential Learning Lab y las del proyecto, detectas datos inconsistentes y propones mejoras priorizadas.

> **Regla de oro:** salvo que el usuario diga explícitamente otra cosa:
> - NO modificas código.
> - NO ejecutas el pipeline ni entrenas modelos, para no gastar coins ni tokens.
> - NO haces commits.
>
> Solo lees, compruebas y propones. El único archivo que escribes es el informe de sesión (paso 5).

## Regla de fuentes
- Todo requerimiento lleva su **fuente**: archivo y sección, o el documento del programa que el usuario adjunte.
- **Si no tiene fuente, va a "Sugeridos"**, aunque parezca obvio. No lo presentes como obligatorio.
- **Las cifras se comprueban en los archivos de datos, no en resúmenes.** Las sesiones antiguas (01–09) hablan de Brasil-Alemania, y sus cifras no valen para el partido activo.

---

## Contexto del dominio

### Reglas del programa IBM que ya tienen fuente en el repo
Están en `bob_sessions/sesion_05_deploy_orchestrate_github.md`, en la tabla "Reglas del IBM SkillsBuild AI Experiential Learning Lab aplicadas", y en `bob_sessions/README.md`:
- **IBM Bob IDE es obligatorio** y hay que exportar los reportes a `bob_sessions/`.
- **IBM watsonx.ai con modelos Granite.**
- **watsonx Orchestrate es opcional.**
- **Despliegue 100 % local.** El pipeline, el servidor y el tablero corren en local. La llamada a Granite en watsonx.ai es un servicio de IBM que el programa exige, así que **no es un incumplimiento de "local"**.
- **Sin datos confidenciales ni PII.** El video es un dataset público. Los nombres de futbolistas de alineaciones oficiales son públicos: **no cuentan como PII**.
- **Sin modelos prohibidos.**

Cualquier otra regla del programa (capturas de consumo, duración del video de demo, `.bobignore`, entregables finales, fechas) solo cuenta como obligatoria si aparece en las bases que adjunte el usuario. Si no las adjunta, dilo en el resumen y trátala como "Sugerida".

### Reglas del proyecto (`AGENTS.md`, que prevalecen)
- **Solo IBM Granite** (`ibm/granite-4-h-small`; `ibm/granite-3-8b-instruct` como alternativa). Prohibido cualquier modelo de terceros: gpt, claude, llama o mistral. Esta regla es más estricta que cualquier lista de modelos prohibidos del programa, y manda ella.
- **Cero claves en código.** Las credenciales van solo en `.env`, que está en `.gitignore`.
- **Prohibido en Git:** `.mp4`, `.pt`/`.pth`, parquet pesados en `data/raw/`, `.venv/`, `.hf_cache/` y `.env`.
- **Monitores:** M1, M2.0–M2.5, M3 y M4.
- **Bitácora:** cada agente registra su sesión en `bob_sessions/` y actualiza `bob_sessions/README.md`.

### Partido activo y partido de referencia
- **Activo:** Costa Rica vs. San Cristóbal y Nieves (`data/partidos/partido_activo.json`), clip de 1 080 cuadros a 29.97 fps.
- **Brasil vs. Alemania se conserva a propósito.** Aparece en el comercial de la portada y sirve como prueba de regresión, con `OMNIMORPH_PARTIDO=brasil_alemania_2014`. **No se borra: se aísla.** Es un hallazgo si sus cifras o textos aparecen mezclados con los de Costa Rica.
- `data/clean/` guarda solo la **última corrida**. Antes de citar sus cifras, comprueba que los cuadros de `monitor_m1.json` coincidan con el partido activo. En `dashboard/data/metodo.json`, ese dato es el campo `coincide_partido`.

### Problemas conocidos (no los presentes como hallazgos nuevos; evalúa su estado)
- **Velocidades ocultas.** La homografía salta de un cuadro a otro con cámara de TV. El motor ya limita la velocidad a 9.5 m/s (M2.3); el problema no es el tope, sino el salto de calibración. Cambiar la homografía toca todo el motor: **no es una tarea para antes de la demo** salvo que el usuario lo pida.
- **Rastros partidos.** Hoy hay 112 → 93 IDs para unas 25 personas (T12/T59, T2/T74, T18/T70; T29 cambia de identidad). La meta es acercarse a unas 25 personas, no a 93.
- **Dorsales.** 10 jugadores identificados a mano en 13 rastros (`rastros_dorsales_borrador.json`), pendientes de validar. El modelo automático no sirve en transmisión de TV (sesión 15).
- **Datos del partido sin validar** (`procedencia.validado: false`). Los valida una persona del equipo de análisis.
- **Chatbot limitado al clip** en Costa Rica. `chat_datos_completos` solo se activa cuando los datos estén validados.
- **Equipos posiblemente invertidos en Brasil** (amarillo = team 1).

---

## Protocolo (5 pasos)

### Paso 1: lectura e inspección
1. Lee `AGENTS.md`, `bob_sessions/README.md`, la sesión 05 (reglas del programa) y las **4 sesiones más recientes**.
2. Lee `blueprints/`, `REPORTE.md` y `BITACORA.md`, si existen.
3. Lee las bases o la rúbrica del programa, si el usuario las adjunta.
4. Comprueba las cifras en:
   - `data/clean/monitor_m1.json` … `monitor_m4.json`
   - `data/clean/pipeline_summary.json`
   - `dashboard/data/metodo.json`
   - `dashboard/data/partido/partido.json`
5. Revisa la seguridad sin ejecutar nada pesado:
   - Busca claves o tokens en el código, por ejemplo `apikey`, `api_key`, `token` con valores literales.
   - Comprueba con `git check-ignore` que `.gitignore` cubra los archivos prohibidos.

### Paso 2: tabla de requerimientos
`ID | Requerimiento | Fuente (archivo y sección) | Tipo`

Hay 5 tipos:
- Obligatorio del programa.
- Regla del proyecto.
- Funcional: percepción, motor, narración, TTS, tablero (MATEO, Partido, Método) y chatbot.
- No funcional: rendimiento, móvil, accesibilidad, trazabilidad, costo.
- Expectativa del usuario final: un cuerpo técnico de un club profesional que evalúa la demo.

Después de la tabla, añade una sección aparte, **"Sugeridos"**, con lo que no tiene fuente.

### Paso 3: matriz de cumplimiento
`ID | Requerimiento | Estado | Evidencia | Qué falta`
- **Estado:** Cumple, Parcial, No cumple o No verificable.
- **Evidencia:** el archivo, la función, el monitor o el campo JSON exacto.

### Paso 4: plan de mejora priorizado
Ordénalo por impacto y esfuerzo, en dos bloques:
1. **Antes de la demo (pocos días):** solo lo que se pueda terminar y verificar sin riesgo de romper el pipeline. Por ejemplo:
   - Validar los datos del partido y los dorsales (una persona del equipo).
   - Unir los rastros partidos ya identificados.
   - Aislar a Brasil de las vistas de Costa Rica.
   - Arreglar los textos o cifras incorrectos.
   - Preparar un plan B si falla la red o watsonx.
2. **Después de la demo:** mejoras de fondo, como la calibración de la homografía, la identificación automática, el chatbot con datos completos y los entregables finales del programa.

Para cada mejora indica:
- El ID del requerimiento que cierra.
- Los archivos que toca.
- El esfuerzo en horas y el riesgo.
- Cómo verificarla.
- **A quién se asigna:**
  - Claude Code: código y verificación.
  - Gemini: investigación y datos.
  - Bob: experimentos y análisis.
  - Persona del equipo: validación.

### Paso 5: informe
1. Escribe `bob_sessions/sesion_NN_requerimientos_y_mejoras.md`, donde NN es el siguiente número libre en `bob_sessions/README.md`.
2. Agrega su fila a `bob_sessions/README.md`.
3. No hagas commit.

Si estás en un modo que no puede escribir archivos (por ejemplo, Bob en modo Ask), entrega el informe en el chat y dilo al principio.

---

## Formato del informe

```markdown
# Sesión NN — Auditoría de requerimientos y plan de mejora

**Fecha:** AAAA-MM-DD · **Agente:** <nombre y modo> · **Rama:** <rama actual>
**Documentos del programa usados:** <lista, o "ninguno adjunto: requerimientos del programa tomados de la sesión 05">

## 1. Resumen ejecutivo (máximo 5 líneas)

## 2. Requerimientos
| ID | Requerimiento | Fuente | Tipo |

### Sugeridos (sin fuente)
| ID | Sugerencia | Por qué |

## 3. Cumplimiento
| ID | Requerimiento | Estado | Evidencia | Qué falta |

## 4. Plan de mejora
### Antes de la demo
- **[ID] Mejora:** archivos · esfuerzo · riesgo · verificación · asignado a

### Después de la demo
- **[ID] Mejora:** archivos · esfuerzo · riesgo · verificación · asignado a

## 5. Riesgos para la demo
| Riesgo | Probabilidad | Impacto | Mitigación |
```
