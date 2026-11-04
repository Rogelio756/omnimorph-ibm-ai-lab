# Sesión 07 — Continuidad de Agentes (IBM Bob, Claude Code, Gemini Antigravity)
## Arquitectura Híbrida, Integración de Brasil-Alemania y "The Architect"
**Fecha:** 2026-11-04  
**Proyecto:** Omnimorph — Análisis Táctico de Fútbol con IA (MATEO)  
**Equipo:** Rogelio Leonardo Méndez Macías  
**Herramientas y Entornos:** IBM Bob IDE + Gemini (Antigravity) + Claude Code + GitHub  
**Rama activa de trabajo:** `feat-dashboard-mejoras` (respaldo base en `pre-mejoras`)  

---

## 1. Objetivos de la sesión

1. Analizar la propuesta técnica enviada por Fernando Maciel (IBM) sobre arquitecturas híbridas (CV + LLM).
2. Evaluar y auditar el repositorio de datos creado por el equipo: [`omnimorph-brasil-alemania-2014`](https://github.com/FerTC8/omnimorph-brasil-alemania-2014.git).
3. Asegurar y respaldar el código actual en GitHub mediante ramas de seguridad (`pre-mejoras` y `feat-dashboard-mejoras`).
4. Instalar y desacoplar la herramienta meta-arquitectónica **The Architect** en una carpeta apartada (`tools/the-architect/`) para garantizar continuidad total e interoperabilidad entre agentes (Bob, Gemini y Claude).
5. Diseñar los planos visuales de la aplicación completa (funciones existentes vs. nuevas adiciones) y el wireframe de la interfaz de 4 paneles/páginas.
6. Dejar preparado el prompt de traspaso para continuar el análisis y desarrollo en Claude Code.

---

## 2. Puntos Clave Analizados

### A. Feedback de Fernando Maciel (IBM) — Arquitectura Híbrida
- **Validación del Enfoque Omnimorph:** Confirmación de que procesar video crudo directamente en un LLM multimodal satura la VRAM y produce alucinaciones espaciales. La práctica estándar industrial es la arquitectura híbrida:
  1. *Capa CV:* Detección (YOLO/ByteTrack) + Homografía 2D a la cancha (OpenCV/SciPy).
  2. *Capa LLM:* Inferencia estadística sobre datos tabulares o JSON estructurados (IBM Granite).
- **Consumo Eficiente de Tokens:** Segmentación en ventanas tácticas (4.0 s) reduciendo drásticamente la latencia.
- **Benchmark y Generalización:** Uso futuro de **SoccerNet** y posible Fine-Tuning de Granite en watsonx.ai Tuning Studio.

### B. Análisis del Repositorio `omnimorph-brasil-alemania-2014`
- **Homologación de Cancha:** Sistema de coordenadas respetado al 100% ($12000 \times 7000\text{ cm}$).
- **Datos Estructurados Validados:**
  - `01_primer_gol_muller/`: Telemetría frame a frame (25 fps, 201 frames) y contrato de 2 ventanas tácticas de 4 segundos del córner del minuto 11.
  - `02_partido_completo/`: Contexto de partido (estadio Mineirão, clima, árbitro Marco Rodríguez MEX, bajas de Neymar y Thiago Silva, plantillas completas de 23 jugadores), estadísticas por periodos (1T 0-5, 2T 1-2, Total 1-7) y cronología de los 8 goles.
  - `assets/`: Diagramas vectoriales `mapa_8_goles.svg` y `radar_gol_muller.svg` listos para el dashboard.
  - `scripts/validate_data.py`: Script de validación aprobado con éxito.

---

## 3. Seguridad y Control de Versiones (Git)

Para blindar el repositorio antes de implementar las nuevas características:

1. **Commit de Respaldo Local:** Guardado de cambios de logos y hero (`6d0c6eb`).
2. **Rama `pre-mejoras` (Checkpoint):** Congela el estado funcional previo a cualquier cambio nuevo.
3. **Rama `feat-dashboard-mejoras` (Desarrollo Activo):** Rama de trabajo donde se implementará la nueva página y el chatbot.
4. **Sincronización Remota:** Ambas ramas y `master` fueron subidas exitosamente a GitHub:
   ```bash
   git push origin master pre-mejoras feat-dashboard-mejoras
   # Resultado: To https://github.com/Rogelio756/omnimorph-ibm-ai-lab.git [OK]
   ```

---

## 4. Instalación de "The Architect" para Interoperabilidad de Agentes

Para permitir que el desarrollador pueda alternar sin perder el contexto de trabajo entre **IBM Bob IDE**, **Gemini (Antigravity)** y **Claude Code**:

1. **Carpeta Central Independiente:**
   - Ubicación: `tools/the-architect/` (clon limpio desacoplado).
   - Contiene la máquina de estados, plantillas de Blueprints, fases de preguntas y modo Brownfield (`commands/architect-brownfield.md`).
2. **Puentes de Descubrimiento (Skills):**
   - Enlace para Gemini / Bob: `.agents/skills/the-architect/`
   - Enlace para Claude Code: `.claude/skills/the-architect/`
   - Comandos slash para Claude Code: `.claude/commands/` (`/architect`, `/architect-brownfield`, `/architect-quick`).
3. **Regla de Continuidad en `AGENTS.md` (§8):**
   - Se formalizó en `AGENTS.md` que cualquier agente que ingrese al repositorio debe:
     - Consultar `tools/the-architect/` para planear cambios en proyectos existentes.
     - Leer la última sesión en `bob_sessions/` para retomar el hilo de desarrollo.
     - Generar el reporte correspondiente al concluir cada sesión de trabajo.

---

## 5. Planos Visuales y Wireframe de la Solución Completa

### A. Arquitectura Unificada (End-to-End)
```
FUENTES (Video + Datos FIFA Brasil 1-7)
   │
   ├──> PERCEPCIÓN MATEMÁTICA LOCAL (YOLO + Homografía EMA + Savitzky-Golay)
   │       │
   │       └──> Ventanas 4.0s (JSON)
   │               │
   ├──> CEREBRO COGNITIVO IBM watsonx.ai
   │       │   • Modelo: ibm/granite-4-h-small
   │       │   • Narrador de Audio (TTS pyttsx3)
   │       │   • Asistente Conversacional (Chatbot)
   │       │   • Auditoría watsonx.governance (Monitor M3)
   │       │
   └──> STREAMLIT MULTI-PAGE DASHBOARD (MATEO)
           ├── Página 1: Operaciones en Vivo (Video, Radar 2D, Métricas, Relato)
           ├── Página 2: Centro de Partido Brasil 1-7 (Pre-Match, Stats, 8 Goles SVG)
           ├── Página 3: Chatbot Asistente Granite (Conversacional, Chips, RAG ligero)
           └── Página 4: Observabilidad (9 Monitores PASS M1 a M4)
```

### B. Wireframe de Navegación del Usuario
- **Barra Lateral:** Menú de 4 páginas + Semáforos en tiempo real M1–M4.
- **Página 1 (Operaciones en Vivo):** 4 paneles sincronizados por el Reloj Maestro (0..60s).
- **Página 2 (Centro de Partido Brasil 1-7):** 4 pestañas interactivas:
  - Tab 1: Ficha Pre-Match (Estadio Mineirão, clima, bajas de Neymar y Thiago Silva, 23 jugadores).
  - Tab 2: Evolución Estadística (1T 0-5 vs 2T 1-2 vs Total 1-7, xG, posesión, pases).
  - Tab 3: Mapa de los 8 Goles (`mapa_8_goles.svg` con escala de tamaño según xG).
  - Tab 4: Zoom al Gol de Müller en min 11 (`radar_gol_muller.svg` y pantallas de Klose/Höwedes).
- **Página 3 (Chatbot Asistente con IBM Granite):**
  - Componente de chat con `st.chat_message()` y `st.chat_input()`.
  - Preguntas sugeridas en chips rápidos.
  - Respuestas analíticas fundamentadas en los datos oficiales con telemetría de tokens y latencia.
- **Página 4 (Observabilidad):** Estado detallado de los 9 monitores del pipeline.

---

## 6. Próximos Pasos (Roadmap de Implementación)

1. **Paso 1:** Copiar el dataset validado a `data/partidos/brasil_alemania_2014/`.
2. **Paso 2:** Crear `implementacion/dashboard/pages/2_Analisis_Brasil_Alemania.py`.
3. **Paso 3:** Implementar el Chatbot conversacional con `ibm/granite-4-h-small`.
