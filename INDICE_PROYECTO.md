# 📂 Índice y Organización del Proyecto — Omnimorph

Estructura limpia de imágenes, diagramas editables y documentación técnica listos para el despliegue en GitHub e **IBM Bob IDE**.

---

## 1. `01_diagramas_y_assets/` (Imágenes y Diagramas Activos que vamos a usar)

### 🖼️ `imagenes_listas/` (Listas para presentaciones, README de GitHub y entregas)
* **`omnimorph_flujo.png`** y **`omnimorph_flujo_v2.svg`**
  * **Qué es:** Diagrama de Arquitectura de Flujo Híbrido actualizado (`1) Percepción GPU Local` $\rightarrow$ `2) IBM Cloud: watsonx Orchestrate ADK + Motor Matemático + watsonx.ai + watsonx.governance` $\rightarrow$ `3) Dashboard Local Sincronizado`) con los **Monitores de Observabilidad (`M1`, `M2.0`–`M2.5`, `M3`, `M4`)** en cada etapa.
* **`omnimorph_flujo_operacion.png`** y **`omnimorph_flujo_operacion.svg`**
  * **Qué es:** Diagrama de Flujo de Operación dividido en 3 carriles:
    * `Fase A`: Preparación local, dataset y contención matemática (0 Bobcoins).
    * `Fase B`: Desarrollo obligatorio en **IBM Bob IDE** (40 Bobcoins) y entregable `bob_sessions/`.
    * `Fase C`: Ciclo de ejecución de punta a punta con semáforos de verificación en vivo.

### ✏️ `editables_excalidraw/` (Archivos fuente para abrir en excalidraw.com)
* **`omnimorph_flujo.excalidraw`** — Fuente editable del Diagrama de Arquitectura con Monitores.
* **`omnimorph_flujo_operacion.excalidraw`** — Fuente editable del Diagrama de Flujo de Operación.
* **`ibm-ecosistema-recursos.excalidraw`** — Fuente editable del ecosistema de cuentas, Bobcoins y recursos de IBM Cloud.

### 🎨 `logos/`
* **`omnimorph_logo_nombre_light.jpg`** y **`omnimorph_logo_nombre_light.svg`** — Logotipos oficiales de Omnimorph para el Dashboard y presentación.

---

## 2. `02_documentacion_omnimorph/` (Documentación Técnica Necesaria del Proyecto)

* **`SPEC_MOTOR_OMNIMORPH.md`** *(antes `Copia de Motor Omnimorph.md`)*
  * **Qué es:** Especificación maestra de la skill `omnimorph-engine` (Fases 1 a 5: Equipos, `P1` Homografía, `P3` Track Stitching con Algoritmo Húngaro, `P2` Savitzky-Golay y Analista Táctico de ventanas de 4 s) + código Python corregido y diccionario de **Monitores `stage_monitors` (`M2.0` a `M2.5`)** listo para empaquetarse como *Custom Python Tool* en **IBM watsonx Orchestrate ADK**.
* **`REPORTE_TECNICO_GPU.md`** *(antes `REPORTE.md`)*
  * **Qué es:** Evaluación experimental completa del pipeline de visión (`roboflow/sports`), tiempos por agente, pruebas de validación `C2 vs A` (`IoU = 1.0`) y esquemas de `objects.parquet`, `frames.parquet` y `timings.parquet`.
* **`Reporte_para_el_equipo_de_matemáticas___Giselle_y_Caroline.pdf`**
  * **Qué es:** Documento técnico de contexto de los 6 agentes de visión y definición formal de los problemas matemáticos `P1`, `P2` y `P3`.
* **`Omnimorph-Diseño_Solución.pdf`**
  * **Qué es:** Documento de Diseño de Solución (Semanas 4–5).

---

## 3. `docs_ibm/` (Guías Oficiales y Toolkits del Laboratorio IBM)

* **`Español 2H26 GuideBob_IBM SkillsBuild AI Experiential Learning Lab Spanish-MX.pdf`** — Guía oficial de **IBM Bob IDE**, presupuesto de 40 Bobcoins, reglas de seguridad de API Keys, modelos permitidos (`ibm/granite-3-8b-instruct`), **Orchestrate ADK** (págs. 37–38) y requisitos de la carpeta `bob_sessions/`.
* **`Español 2026 AI Experiential Learning Lab - Industry Challenges.pdf`** — Retos de industria.
* **`Español-Solution Design Guide for Participants.pptx`** y **Toolkits de Design Thinking (`As-Is`, `To-Be`, `Empathy Map`, `Big Idea Vignettes`, `Prioritization Grid`)**.

---

## 4. `99_archivo_versiones_previas/` (Respaldo Histórico)

* Contiene borradores y versiones anteriores (`omnimorph_flujo_primer_flujo.png`, `omnimorph_flujo_v1_backup.excalidraw`, `REPORTE_1.md`) guardados por seguridad para que no estorben en las carpetas activas.
