# Encargo para Gemini (Antigravity): percepción sobre Costa Rica vs. San Cristóbal y Nieves

**Asignado a:** Gemini en Antigravity
**Preparado por:** Claude Code, 2026-11-09
**Fecha límite:** antes de la presentación en línea con Gallos Blancos (esta semana)

---

## 0. Antes de empezar

1. Lee `AGENTS.md` completo, sobre todo §1 (solo IBM Granite), §2 (credenciales) y §3 (qué no se sube a Git).
2. Lee la última sesión: `bob_sessions/sesion_09_visual_chat_flotante_y_fichero.md`.
3. Trabajas en la **misma carpeta y la misma rama que Claude Code: `feat-costa-rica`**. Por eso:
   - **No cambies de rama** (`git switch` / `checkout`), no hagas `stash`, `reset` ni `git add -A` / `git add .`. Moverías el trabajo sin commit de Claude.
   - Haz commit solo nombrando tus archivos: `git add scripts/run_mvp_perception.py scripts/finalize_mvp_perception.py`.
   - Comprueba que estás en la rama correcta con `git branch --show-current`. Debe decir `feat-costa-rica`.
4. Usa siempre el entorno del proyecto: `.\.venv\Scripts\python.exe`. Antes de correr cualquier script, en PowerShell:
   ```powershell
   $env:PYTHONIOENCODING = "utf-8"
   ```
   Sin esto, la consola de Windows falla al imprimir acentos y flechas.

## 1. Objetivo

Correr los 6 modelos de percepción sobre el clip nuevo y entregar telemetría limpia y medida. Reemplaza a Brasil vs. Alemania como partido principal de la demo. Brasil queda solo como video de entrada.

## 2. Insumo

| Dato | Valor |
|---|---|
| Archivo | `data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4` (ya descargado) |
| Partido | Costa Rica vs. San Cristóbal y Nieves, Eliminatorias Concacaf 2026, 2ª ronda, jornada 1 |
| Video | 1280×720, 29.97 fps, 1799 frames (60 s) |
| **Ventana a procesar** | **segundos 0 a 36 = frames 0 a 1079 → `--max-frames 1080`** |
| Por qué esa ventana | Es un solo plano táctico continuo (36 s, mediana de 15 jugadores visibles). Después vienen una falta y una repetición en primer plano que arruinan la homografía. |
| Uniformes | Costa Rica: guinda/rojo oscuro. San Cristóbal y Nieves: verde. Árbitro: amarillo. |

Si el archivo no está, descárgalo así:
```powershell
.\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'implementacion/dataset'); import dataset_manager as d; d.download_hf_soccer_videos(filenames=['HP3zxNuoWXE-720-15.mp4'], match_prefix='HP3zxNuoWXE', resolution='720', dest_dir='data/videos/candidatos_720p')"
```

## 3. Pasos

### Paso 1: quitar las etiquetas fijas de Brasil en los scripts de percepción

`scripts/run_mvp_perception.py` y `scripts/finalize_mvp_perception.py` escriben a mano "Brasil (Eq 0)", "Mundial FIFA Brasil 2014" y "Brasil vs. Alemania (1-7)" (líneas ~748, ~849-850 y ~216, ~387-388). Agrega argumentos opcionales, con los valores actuales como default para no romper Brasil:

- `--team0-label`, `--team1-label`
- `--match-label`, `--project-label`

**Criterio:** si corres el script sin los argumentos nuevos, la salida es igual a la de antes.

### Paso 2: correr la percepción

```powershell
.\.venv\Scripts\python.exe scripts/run_mvp_perception.py `
  --source data/videos/candidatos_720p/HP3zxNuoWXE-720-15.mp4 `
  --outdir outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15 `
  --max-frames 1080 --device cuda `
  --team0-label "<según lo que salga en el paso 3>" --team1-label "<…>" `
  --match-label "Costa Rica vs. San Cristóbal y Nieves — Eliminatorias Concacaf 2026" `
  --project-label "Omnimorph MVP — Eliminatorias Concacaf 2026"
```

`team_id` 0 y 1 los asigna KMeans, así que no sabes de antemano cuál es cuál. Corre una vez, mira `TEAM_CLASSIFICATION.mp4` y, si hace falta, ajusta las etiquetas con `scripts/finalize_mvp_perception.py`. Ese script no vuelve a usar la GPU.

### Paso 3: verificar y medir

Reporta cada punto con números. Una frase como "se ve bien" no cuenta.

| # | Comprobación | Cómo | Esperado |
|---|---|---|---|
| 1 | Salidas completas | Listar `outdir` | 6 JSON en `json_por_modelo/`, 6 MP4 en `videos_por_modelo/`, `TELEMETRIA_UNIFICADA_COMPLETA.json`, `VIDEO_UNIFICADO_TODOS_JUNTOS.mp4`, `frames.parquet`, `objects.parquet` |
| 2 | Cuadros procesados | `len(pd.read_parquet(frames.parquet))` | 1080 |
| 3 | Equipos | Qué `team_id` es Costa Rica (guinda) y cuál SKN (verde). Revisa capturas en s 5, 18 y 30 | Mismo equipo, mismo color en las 3. Reporta los jugadores mal asignados que veas |
| 4 | Porteros y árbitro | ¿Al árbitro (amarillo) lo meten en un equipo? ¿Y a los porteros? | Árbitro fuera de los dos equipos |
| 5 | Homografía | % de cuadros con matriz H válida (≥4 puntos de cancha) | ≥ 90 % |
| 6 | Radar | En `RADAR.mp4`, ¿los jugadores quedan dentro de la cancha y sin saltos? | Sin jugadores fuera de 0–12 000 × 0–7 000 cm, salvo en bandas |
| 7 | Tracking | Número de `track_id` distintos y cambios de ID que observes | Idealmente < 40 para unas 22 personas |
| 8 | Balón | % de cuadros con balón detectado | Reportar el valor |
| 9 | Costo | Tiempo total y VRAM pico | Reportar el valor |

Guarda capturas de las comprobaciones 3, 4 y 6 en `outputs/mvp_pruebas/eliminatorias_2026_costa_rica_skn/clip_15/capturas/`.

## 4. Lo que NO debes tocar

Estas carpetas las está cambiando Claude Code en paralelo. Si las tocas, habrá conflictos:

- `implementacion/` (engine, narrador, chatbot, monitores, dashboard Streamlit)
- `run_pipeline.py`
- `dashboard/`
- `data/raw/`: **no copies ahí los parquets nuevos.** Claude los integra con respaldo previo.
- `data/partidos/`

Tampoco subas a Git `.mp4`, `.pt`, `.parquet`, `.env` ni nada de `outputs/`. Si encuentras un bug fuera de `scripts/`, anótalo en la bitácora y no lo arregles.

## 5. Entregables

1. Commits en `feat-costa-rica` solo con los cambios a `scripts/run_mvp_perception.py` y `scripts/finalize_mvp_perception.py`. Mensaje en español, con el formato `tipo(ámbito): descripción`, igual que el historial.
2. `bob_sessions/sesion_10_percepcion_costa_rica_gemini.md` con:
   - El comando exacto que corriste
   - La tabla de la sección 3 con tus números
   - El mapeo `team_id 0 = …`, `team_id 1 = …`
   - Los problemas que viste y lo que no pudiste verificar
3. La fila nueva en la tabla índice de `bob_sessions/README.md`.
4. **No hagas push ni merge.** El usuario revisa y aprueba cada commit.

## 6. Si algo falla

- **Falta VRAM:** baja a `--max-frames 540` (18 s) para probar y reporta el error.
- **La homografía falla en muchos cuadros:** reporta en qué segundos. No cambies la ventana por tu cuenta.
- **La clasificación de equipos mezcla los colores:** reporta en qué segundos y con qué jugadores. No reentrenes nada.
