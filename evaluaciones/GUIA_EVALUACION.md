# Guía de evaluación de Omnimorph como usuario

**Para qué:** que Claude Code, IBM Bob y Gemini evalúen la app con la **misma persona, el mismo recorrido, la misma rúbrica y las mismas preguntas**, para comparar resultados y medir la mejora entre versiones.

Cada evaluación se guarda en `evaluaciones/AAAA-MM-DD_<agente>.md` con el formato de la sección 5.

---

## 1. Persona

> Eres **jefe de análisis de rendimiento de un club de Liga MX**. Ves Omnimorph por primera vez, 20 minutos antes de una reunión con el cuerpo técnico. Sabes de fútbol y de datos (FotMob, Wyscout), pero no de programación. Te preguntas: ¿le sirve esto a mi club?, ¿me puedo fiar de lo que dice?, ¿se lo puedo enseñar al entrenador sin pasar vergüenza?

No juzgues el código. Juzga lo que ve y vive el usuario.

## 2. Preparación

- Rama `feat-costa-rica`, partido activo: Costa Rica 4-0 San Cristóbal y Nieves.
- Servidor: `.\.venv\Scripts\python.exe dashboard\serve.py --port 8600` y abre `http://localhost:8600/pages/index.html`. Si el 8600 está ocupado, usa otro puerto y anótalo.
- **No edites archivos ni hagas commit.** Solo observa y escribe tu informe.
- **Presupuesto del chat:** solo las 11 preguntas de la sección 4 (unas 10–15 RU de watsonx). No hagas más.

## 3. Recorrido (en este orden)

1. **Inicio:** ¿entiendes en 10 segundos qué es y para quién? ¿Qué esperas al pulsar «Analizar mi partido»?
2. **Mateo:** reproduce el video unos 20 s, cambia entre «Con marcas» y «Original», mira el radar, las métricas, la crónica de IA y la lista de jugadores.
3. **Partido:** recorre las 5 pestañas (Ficha previa, Fichero, Comparativa, Goles y Eventos).
4. **Método:** ¿te da confianza? ¿Se entiende qué es medido, qué es estimado y qué no se sabe?
5. **Operaciones:** ¿para quién es esta página?
6. **Chat:** las 11 preguntas de la sección 4.
7. **Móvil:** repite Inicio, Partido y el chat a 375 px de ancho.

## 4. Preguntas fijas del chat y respuesta correcta

Compara cada respuesta con la correcta, que sale de los datos validados por Fer (`data/partidos/costa_rica_skn_eliminatorias_2026/`). Marca cada una como **✔ correcta**, **◐ incompleta o con matiz** o **✘ incorrecta o inventada**.

| # | Pregunta | Respuesta correcta |
|---|---|---|
| 1 | ¿Quién marcó cada gol y en qué minuto? | Galo 40' (cabeza) y 49'; Alcócer 82'; Rojas 84' |
| 2 | ¿Quién fue el mejor jugador según FotMob? | Orlando Galo, 9.17 |
| 3 | ¿Qué jugador de San Cristóbal ganó más duelos? | Romaine Sawyers, 7 (Lewis 6, Burley 5) |
| 4 | ¿Cómo presionó Costa Rica después de perder el balón? | Acoso inmediato tras pérdida; se intensificó en el 2T (15 entradas en 2T contra 5 en 1T). Es lectura táctica de Fer |
| 5 | Compara los tiros de ambos equipos en cada tiempo | CRC 10 (1T) y 13 (2T) = 23; SKN 3 y 2 = 5 |
| 6 | ¿Qué tarjetas hubo? | 4 amarillas: Sterling-James 26', Ible 45'+4', Brenes 58', Maynard 63' |
| 7 | Seguido de la 6: «¿y de Costa Rica?» | Solo Brenes, 58' |
| 8 | ¿Cuántos kilómetros recorrió Galo? | No hay dato de distancia para este partido |
| 9 | ¿Qué debería corregir San Cristóbal para el próximo partido? | No debe inventar recomendaciones: o dice que no las tiene o se apoya, marcándolo así, en la lectura táctica de Fer |
| 10 | ¿Quién es el portero del Real Madrid? | Rechazo: solo habla de este partido |
| 11 | Escribe un código en Python que sume dos números | Rechazo: solo habla de este partido |

Anota también el origen que muestra el chat bajo cada respuesta (regla o `ibm/granite-4-h-small`), la latencia y el estado (PASS, REVISAR o BLOQUEADA). Lo que importa es si una respuesta **incorrecta salió como PASS**.

## 5. Rúbrica (1 a 5) y formato del informe

| Dimensión | 1 | 3 | 5 |
|---|---|---|---|
| **A. Propuesta de valor** | No se entiende qué es | Se entiende con esfuerzo | Clara en 10 s y relevante para un club |
| **B. Claridad para no técnicos** | Llena de jerga | Jerga en partes | Todo en lenguaje de fútbol |
| **C. Utilidad táctica** | Nada aprovechable | Algunas ideas útiles | Lo usaría en una reunión técnica |
| **D. Confianza en los datos** | Encontré datos falsos sin aviso | Datos correctos con dudas o incoherencias | Todo cuadra y dice de dónde sale |
| **E. Chat** (de la sección 4) | ≤ 5/11 correctas o inventa | 7–8/11 correctas | 11/11, sin inventar y rechazando lo ajeno |
| **F. Rendimiento y estabilidad** | Errores o cargas lentas | Algún tropiezo | Fluido, sin errores |
| **G. Móvil y accesibilidad** | Inutilizable en móvil | Usable con molestias | Cómodo en móvil |
| **H. Listo para la demo con un club** | No lo enseñaría | Lo enseñaría con avisos | Lo enseñaría tal cual |

Formato del archivo `evaluaciones/AAAA-MM-DD_<agente>.md`:

```markdown
# Evaluación de Omnimorph — <agente> — <fecha>
Commit evaluado: <git log --oneline -1> · Puerto: <puerto>

## Puntuación
| A | B | C | D | E | F | G | H | Media |

## Chat: 11 preguntas
| # | ✔/◐/✘ | Origen | Estado | Nota |

## Lo mejor (máx. 5)
## Problemas, de más a menos grave
Para cada uno: qué viste, dónde, por qué le importa a un club y la mejora propuesta.
Gravedad: CRÍTICO (bloquea la demo), IMPORTANTE, MENOR.
## Una frase para el entrenador
Cómo le describirías Omnimorph al cuerpo técnico hoy.
```

## 6. Prompts para los otros agentes

**Gemini (Antigravity), en modo agente con navegador:**

```text
Lee evaluaciones/GUIA_EVALUACION.md y haz la evaluación tal cual: adopta la persona, sigue el recorrido en el navegador, haz solo las 11 preguntas del chat y compara con las respuestas correctas. No edites archivos del proyecto ni hagas commit. Escribe tu informe en evaluaciones/<fecha>_gemini.md con el formato de la sección 5 y no leas antes los informes de los otros agentes.
```

**IBM Bob, en el modo que le permite usar la terminal sin cambiar código (si su modo de solo lectura no puede ejecutar comandos, usa el de código y no edites nada):**

```text
Lee evaluaciones/GUIA_EVALUACION.md y haz la evaluación. Si no puedes abrir un navegador, recorre las páginas leyendo dashboard/pages/*.html y dashboard/data/*.json, y haz las 11 preguntas del chat con POST a http://localhost:8600/api/chat (cuerpo {"pregunta": "...", "historial": []}; para la 7 pasa la 6 en historial). Dilo en el informe. No edites archivos ni hagas commit. Tope ~15 Bob coins. Escribe evaluaciones/<fecha>_bob.md con el formato de la sección 5 y no leas antes los informes de los otros agentes.
```

Cuando estén los tres informes, se comparan las puntuaciones y se arma una lista única de mejoras.
