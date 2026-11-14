# Encargo para IBM Bob: mostrar en la página Partido toda la información de Fer

**Asignado a:** IBM Bob IDE
**Preparado por:** Claude Code, 2026-11-13
**Presupuesto:** máximo ~40 Bob coins. Si te acercas, detente y reporta lo que llevas.
**Resultado esperado:** la página Partido (`dashboard/pages/partido.html`) muestra las jugadas, los colores reales de los equipos, los eventos, las estadísticas por jugador y los diagramas que entregó Fer. Sin commit: el usuario revisa antes.

---

## 0. Antes de empezar

1. Lee `AGENTS.md`, `bob_sessions/README.md` y la última bitácora (`bob_sessions/sesion_25_validacion_fer.md`).
2. **Misma carpeta y misma rama que Claude Code: `feat-costa-rica`.** No cambies de rama ni hagas `stash`, `reset`, `checkout --`, `git add -A` o `git add .`. **No hagas commit ni push**: el usuario aprueba cada commit.
3. Python: `.\.venv\Scripts\python.exe` con `$env:PYTHONIOENCODING = "utf-8"`.
4. **No toques** `implementacion/cloud_agent/chat_agent.py`, `chat_verificador.py` ni `scripts/importar_datos_fer.py` (chat e importador, de Claude Code). Los datos de `data/partidos/costa_rica_skn_eliminatorias_2026/partido/` ya están validados: léelos, no los edites a mano.
5. El tablero objetivo es el frontend web de `dashboard/` (HTML + JS sin framework), **no** Streamlit.

## 1. Qué datos ya existen y dónde

Fuente validada: repo de Fer `FerTC8/omnimorph-costa-rica-skn-2024`, commit `8010944`. Copia local en `data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/` (CSV, JSON, `ANALISIS_PARTIDO.md`, `FUENTES.md` y los 3 SVG en `assets/`).

Ya integrado en `data/partidos/costa_rica_skn_eliminatorias_2026/partido/`:

| Archivo | Campos nuevos que la página todavía NO muestra |
|---|---|
| `contexto_partido.json` | `partido_info.contexto_competitivo`, `partido_info.discrepancias_resueltas`, `partido_info.datos_no_disponibles`, `partido_info.identificadores_externos`. Por equipo: `esquema_nota`, `uniforme_detalle` (camiseta, pantaloneta, medias, portero), `entrenador_nacionalidad`. Por jugador de `plantilla`: `rol_tactico` |
| `cronologia_goles.json` | Por gol: `jugada` (relato de la jugada según Fer), `zona_remate`, `pie_remate`, `segundo_oficial`, `coordenadas_fifa` {x, y} |
| `estadisticas_partido.json` | `rendimiento_individual_destacado` (32 jugadores: calificación FotMob, toques, pases, tiros, duelos, recuperaciones; porteros: atajadas y goles recibidos) y `metricas_adicionales` (22 métricas de equipo por tiempo: postes, grandes ocasiones, duelos, regates, despejes, centros…) |
| `eventos_partido.json` | 30 eventos: inicio, tarjetas, atajadas, postes, cambios, ocasión clara, atención médica, descanso y final, con `minuto`, `tipo`, `equipo`, `jugador`, `jugador_secundario`, `hora_utc` y `descripcion` |

Cómo llega al navegador: `scripts/export_dashboard_data.py` (función que escribe `dashboard/data/partido/partido.json`) junta `partido_info`, `equipos`, `estadisticas` y `goles`. **Hoy no exporta `eventos_partido.json`**: hay que añadirlo (clave `eventos`) y, si usas los SVG de Fer, copiarlos a `dashboard/data/partido/` igual que los `opcionales` existentes. Después corre:

```powershell
.\.venv\Scripts\python.exe scripts\export_dashboard_data.py
```

La página la dibujan `dashboard/components/partido.js` (pestañas Ficha, Comparativa, Goles) y `dashboard/components/fichero.js` (pestaña Fichero).

## 2. Qué hay que construir

1. **Los 4 goles con su jugada.** En la pestaña Goles hoy la columna «Jugada» sale «—» (lee `tipo_jugada`, que está vacío) y el detalle muestra la `narracion` corta antigua. Muestra `jugada`, `zona_remate`, `pie_remate` y el minuto con segundo oficial (`segundo_oficial` son segundos desde el inicio del partido). Si es razonable, dibuja una mini cancha con `coordenadas_fifa` (escala 0–100; **confirma en `fer_validacion/README.md` o `FUENTES.md` hacia qué portería crece x** antes de dibujar).
2. **Colores reales de los equipos.** Hoy la página usa `color_ui` de `partido.config.json`: San Cristóbal `#FF1493` (rosa) y Costa Rica `#00BFFF` (celeste). Esos colores salen del clasificador de equipos del pipeline y están **dibujados dentro de los videos ya renderizados y del radar de la página Mateo**. Los uniformes reales son Costa Rica rojo (`#c8102e`, con azul marino `#102a56`) y San Cristóbal verde (`#009739` / `#166534`), según `fer_validacion/assets/uniformes_y_zonas.svg` y `uniforme_detalle`.
   - **Propón primero, antes de implementar**, cómo resolverlo. Opción sugerida: un campo nuevo `color_uniforme` por equipo en `partido.config.json` que use solo la página Partido, sin tocar `color_ui` (que deben seguir usando Mateo y los videos), y una leyenda que explique la diferencia. Cuida el contraste en modo claro y oscuro, y que rojo y verde se distingan también por texto o forma (daltonismo).
3. **Línea de tiempo de eventos.** Una vista cronológica de los 30 eventos (por ejemplo, una pestaña «Eventos» o una franja en Ficha), con icono o etiqueta por tipo, color del equipo y descripción. Puedes usar `fer_validacion/assets/timeline_partido.svg` como referencia o mostrarlo tal cual, pero los datos deben salir de `eventos_partido.json`.
4. **Fichero con datos por jugador.** En cada jugador: `rol_tactico` y, si tiene fila en `rendimiento_individual_destacado`, su calificación FotMob, pases (completados/intentados), toques, tiros, duelos y recuperaciones (y atajadas/goles recibidos para porteros). En cada equipo: `esquema_nota` y el uniforme detallado.
5. **Comparativa con las métricas adicionales.** Añade `metricas_adicionales` a la tabla «Todas las métricas» (o una segunda tabla), con 1T, 2T y total.
6. **Ficha.** Contexto del grupo (`contexto_competitivo`), «Datos no disponibles» (`datos_no_disponibles`: xG, distancia, velocidad, mapas de calor… para que el club vea qué NO se inventa) y las discrepancias entre fuentes ya resueltas, junto a la lista de fuentes que ya existe.
7. **Diagramas de Fer** (`esquemas_tacticos.svg`, `uniformes_y_zonas.svg`, `timeline_partido.svg`): muéstralos donde aporten, con crédito «Diagrama: equipo de análisis (Fer)». Los revisó Claude Code: no traen scripts ni enlaces externos. Cárgalos con `<img>`, no incrustados en línea.

## 3. Reglas de calidad

- **Sin dato, «—»**: no completes ni estimes. Lo marcado como `estimacion_tactica` por Fer se muestra como lectura táctica, no como dato medido.
- **Brasil no se rompe.** El partido Brasil-Alemania (`data/partidos/brasil_alemania_2014/`) no tiene ninguno de estos campos: cada bloque nuevo debe ocultarse si su dato falta. No re-exportes Brasil para probar (sobrescribe `dashboard/data/`); revisa que el código compruebe cada campo antes de usarlo.
- Sigue el estilo existente de `partido.js` (`el()`, `stat()`, `seccion`), las fuentes y variables CSS del tablero, y que funcione en móvil (375 px) sin scroll horizontal.
- Textos en español, frases cortas, sin jerga de programación en pantalla.

## 4. Cómo verificar

1. Re-exporta (`scripts\export_dashboard_data.py`) y arranca `.\.venv\Scripts\python.exe dashboard\serve.py --port 8600`.
2. Abre `http://localhost:8600/pages/partido.html`, recarga sin caché (Ctrl+F5) y revisa cada pestaña: sin errores en la consola, en escritorio y a 375 px.
3. Comprueba a mano 4 datos contra `fer_validacion/`: la jugada del 2-0 (49', Galo, pie izquierdo), las 4 amarillas (26', 45'+4', 58', 63'), la calificación de Galo (9.17) y los tiros al poste de Costa Rica (2).
4. Revisa que `git status` solo muestre archivos que tocaste a propósito.

## 5. Al terminar

- Escribe `bob_sessions/sesion_26_pagina_partido_fer.md` (qué se pidió, qué hiciste, archivos, cómo verificaste, qué quedó pendiente, coins usados) y añade su fila en `bob_sessions/README.md`.
- No hagas commit. Deja la lista de archivos tocados para que el usuario los revise y apruebe el commit.
