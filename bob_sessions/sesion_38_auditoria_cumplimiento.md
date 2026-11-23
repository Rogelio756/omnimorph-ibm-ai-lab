# Sesión 38 — Auditoría de requerimientos y plan de mejora

**Fecha:** 2026-11-23 · **Agente:** Claude Code (auditor, solo lectura) · **Rama:** feat-costa-rica
**Documentos del programa usados:** ninguno adjunto. Las reglas del programa salen de la sesión 05 (tabla «Reglas del IBM SkillsBuild…») y de `bob_sessions/README.md`. Las páginas de GuideBob citadas por NotebookLM (27, 32, 42, 56–60) no se pudieron leer aquí: quedan como «por confirmar».

## 1. Resumen ejecutivo
Las reglas técnicas del programa y del proyecto se cumplen: solo Granite, cero llaves en el código, archivos prohibidos fuera de Git, despliegue local y 9/9 monitores en PASS con el partido activo. Faltan dos cosas de **entrega**, no de código:
1. Las **capturas de pantalla** dentro de `bob_sessions/`, que el README cita como obligatorias, y la exportación oficial de las sesiones de Bob con su consumo de Bobcoins.
2. Llevar el trabajo a la **rama principal**: `feat-costa-rica` tiene 68 commits que no están en `main`.

## 2. Requerimientos
| ID | Requerimiento | Fuente | Tipo |
|---|---|---|---|
| P1 | Desarrollar con IBM Bob IDE | sesion_05, tabla de reglas | Obligatorio del programa |
| P2 | Exportar `bob_sessions/` con reportes Markdown **y capturas de pantalla** en el repo final | bob_sessions/README.md (cita del programa) | Obligatorio del programa |
| P3 | Usar watsonx.ai con modelos Granite | sesion_05 | Obligatorio del programa |
| P4 | Despliegue 100 % local | sesion_05 | Obligatorio del programa |
| P5 | Sin datos confidenciales ni PII | sesion_05 | Obligatorio del programa |
| P6 | Sin modelos prohibidos | sesion_05 | Obligatorio del programa |
| P7 | watsonx Orchestrate (opcional) | sesion_05 | Obligatorio del programa (opcional) |
| R1 | Solo `ibm/granite-4-h-small` o `granite-3-8b-instruct`; sin openai ni anthropic | AGENTS.md §1, §7 | Regla del proyecto |
| R2 | Cero llaves en el código; credenciales en `.env` ignorado | AGENTS.md §2 | Regla del proyecto |
| R3 | Sin .mp4, .pt, .pth, parquet de raw, .venv, .hf_cache ni .env en Git | AGENTS.md §3 | Regla del proyecto |
| R4 | Monitores M1–M4 en PASS | AGENTS.md §5 | Regla del proyecto |
| R5 | Cada agente registra su sesión y actualiza el índice | AGENTS.md §8B | Regla del proyecto |
| F1 | Tablero con MATEO, Partido, Método y Transmisión | blueprints/, sesiones 13–36 | Funcional |
| F2 | Chat que responde con datos del clip | sesión 30 | Funcional |
| N1 | Trazabilidad: ningún dato sin fuente | dashboard/data/metodo.json, docs/resumen_ejecutivo | No funcional |
| U1 | Un cuerpo técnico entiende la demo sin explicación previa | sesiones 28 y 31 | Expectativa del usuario final |

### Sugeridos (sin fuente en el repo)
| ID | Sugerencia | Por qué |
|---|---|---|
| S1 | Video final de unos 3 minutos | Lo menciona NotebookLM; falta confirmarlo en las bases |
| S2 | Archivo `.bobignore` | Lo mencionan las guías de Bob; no existe en el repo |
| S3 | No desplegar en la nube durante el laboratorio | NotebookLM cita GuideBob, págs. 32 y 42; falta confirmarlo |
| S4 | Retroalimentación real de usuarios | Las tres rondas de prueba cerraron con 0 opiniones |

## 3. Cumplimiento
| ID | Requerimiento | Estado | Evidencia | Qué falta |
|---|---|---|---|---|
| P1 | Bob IDE | Cumple | Sesiones de Bob 01–06, 36 y 37; tags step-01…07 | — |
| P2 | bob_sessions con capturas | **Parcial** | 39 .md en Git, índice con 38 filas; **0 imágenes** en `bob_sessions/` | Exportar las sesiones desde Bob (GuideBob, págs. 56–60) y agregar capturas de uso y de Bobcoins en `bob_sessions/capturas/` |
| P3 | Granite en watsonx.ai | Cumple | monitor_m3.json PASS | — |
| P4 | Local | Cumple | `dashboard/serve.py` en localhost:8600; el túnel solo expone la PC local | Confirmar S3 antes de migrar a IBM Cloud |
| P5 | Sin PII | Cumple | Video público; nombres de alineaciones oficiales; correo de la cuenta de Bob retirado de la sesión 37 (9fc497a) | — |
| P6 / R1 | Sin modelos prohibidos | Cumple | `git grep` sin imports de openai o anthropic ni nombres gpt-, claude-, llama- o mistral- en .py | — |
| P7 | Orchestrate | Cumple (opcional) | sesion_05: OpenAPI listo | — |
| R2 | Cero llaves | Cumple | `git grep` sin llaves literales; `.env` ignorado (.gitignore:4) | Repetir el escaneo sobre las exportaciones de Bob antes de subirlas |
| R3 | Archivos prohibidos | Cumple | `git check-ignore` cubre los 7 patrones; `git ls-files` sin coincidencias | — |
| R4 | Monitores | Cumple | pipeline_summary.json all_pass=True (2026-11-09); metodo.json coincide_partido=true | — |
| R5 | Bitácora | Cumple | sesiones 34–38 con su fila en el README | — |
| F1 | Tablero | Cumple | Las 6 páginas responden 200 por el túnel (23/11) | Pequeño salto de altura en el celular (Transmisión) |
| F2 | Chat | Parcial | Solo clip; reglas y luego Granite | Datos completos cuando se validen |
| N1 | Trazabilidad | Cumple | `docs/resumen_ejecutivo/` cita archivo por dato (1772f2f) | — |
| U1 | Demo entendible | No verificable | 0 opiniones en 3 rondas | Retroalimentación de la reunión con IBM o del club |

## 4. Plan de mejora
### Antes de la entrega
- **[P2] Exportar sesiones de Bob y capturas:** `bob_sessions/bob_export_*.md`, `bob_sessions/capturas/` · 1 h · riesgo: exponer llaves → escanear antes de subir · verificación: `find bob_sessions -name "*.png"` y escaneo sin hallazgos · asignado a: usuario (exporta) y Claude (revisa).
- **[P2] Agregar al índice una sección de capturas y consumo** (~196 Bobcoins) · 15 min · bajo · asignado a: Claude.
- **[Entrega] PR `feat-costa-rica` → `main`** con revisión · 1 h · riesgo medio (68 commits) · verificación: el tablero corre desde `main` · asignado a: Claude prepara y el usuario aprueba.
- **[S1/S3] Confirmar en GuideBob** el video final y la regla de la nube · 15 min · asignado a: usuario.

### Después de la entrega
- **[F2] Chat con datos completos** cuando el equipo valide el partido · asignado a: persona del equipo y Bob.
- **Calibración de la homografía** para recuperar velocidades · alto riesgo · asignado a: Bob.
- **Migración a IBM Cloud Code Engine**, solo si S3 lo permite · asignado a: blueprint de Claude, construcción de Bob.
- **Blueprint amateur** con video de celular real · asignado a: Claude.

## 5. Riesgos
| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| El jurado revisa `main` y no ve Transmisión ni las últimas sesiones | Alta | Alto | PR a `main` |
| Llave expuesta en una exportación de Bob | Media | Muy alto (suspensión) | Escaneo antes de cada commit |
| Se cae el túnel en una demo | Alta | Medio | Plan B: `localhost:8600` compartiendo pantalla |
| Bobcoins agotados (~24 hasta el 2/12) | Media | Medio | Reservarlos para la exportación y ajustes pequeños |
