"""
implementacion/dashboard/app.py
================================
MATEO — Motor de Análisis Táctico y Estadístico de Operaciones futbolísticas
Dashboard Streamlit (4 paneles sincronizados) · Powered by IBM watsonx.ai

Ejecutar:
    streamlit run implementacion/dashboard/app.py

Paneles:
  Panel 1: Video local / Visor de fotograma y bounding boxes (track_id_stitched)
  Panel 2: Radar Cenital 2D (cancha 120×70 m, ARG/FRA/balón)
  Panel 3: Métricas tácticas de la ventana activa de 4.0 s
  Panel 4: Crónica táctica ibm/granite-4-h-small + Reproductor TTS

Reloj Maestro: frame 0..1799 / t 0.0..60.0 s (sincroniza todos los paneles)
Tablero de Semáforos: M1, M2.0–M2.5, M3, M4 en tiempo real
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Paths y configuración de página
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CLEAN_DIR = _ROOT / "data" / "clean"
AUDIO_DIR = _ROOT / "data" / "audio"
LOGO_PATH = _ROOT / "01_diagramas_y_assets" / "logos" / "omnimorph_logo_nombre_light.svg"

st.set_page_config(
    page_title="MATEO — Análisis Táctico de Fútbol",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# CSS personalizado
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .monitor-pass { color: #22c55e; font-weight: bold; }
    .monitor-fail { color: #ef4444; font-weight: bold; }
    .monitor-warn { color: #f59e0b; font-weight: bold; }
    .monitor-missing { color: #94a3b8; font-style: italic; }
    .semaphore-box {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        margin: 2px; font-size: 13px; font-weight: 600;
    }
    .sem-pass { background-color: #dcfce7; color: #166534; }
    .sem-fail { background-color: #fee2e2; color: #991b1b; }
    .sem-miss { background-color: #f1f5f9; color: #64748b; }
    .metric-card {
        background: #f8fafc; border: 1px solid #e2e8f0;
        border-radius: 8px; padding: 12px; margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Carga de datos (cached)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5)
def load_objects() -> pd.DataFrame | None:
    p = CLEAN_DIR / "objects_cleaned.parquet"
    if p.exists():
        return pd.read_parquet(str(p))
    return None


@st.cache_data(ttl=5)
def load_frames() -> pd.DataFrame | None:
    p = CLEAN_DIR / "frames_clean.parquet"
    if p.exists():
        return pd.read_parquet(str(p))
    # Fallback: frames de data/raw
    p2 = _ROOT / "data" / "raw" / "frames.parquet"
    if p2.exists():
        return pd.read_parquet(str(p2))
    return None


@st.cache_data(ttl=5)
def load_tactical() -> list | None:
    p = CLEAN_DIR / "tactical_summaries.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=5)
def load_narrations() -> list | None:
    p = CLEAN_DIR / "narrations.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=5)
def load_monitor(name: str) -> dict | None:
    """Carga el reporte JSON de un monitor (m1, m2, m3, m4)."""
    p = CLEAN_DIR / f"monitor_{name}.json"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Semáforo de monitores
# ---------------------------------------------------------------------------

def render_semaphores():
    """Renderiza el tablero de semáforos de observabilidad MATEO."""
    st.subheader("🚦 MATEO · Tablero de Observabilidad")

    m1 = load_monitor("m1")
    m2 = load_monitor("m2")
    m3 = load_monitor("m3")
    m4 = load_monitor("m4")

    def badge(label: str, report: dict | None) -> str:
        if report is None:
            return f'<span class="semaphore-box sem-miss">{label} —</span>'
        status = report.get("status", "?")
        cls = "sem-pass" if status == "PASS" else "sem-fail"
        icon = "✅" if status == "PASS" else "❌"
        return f'<span class="semaphore-box {cls}">{icon} {label}</span>'

    html_parts = [badge("M1", m1)]

    # M2.0–M2.5 individual
    if m2:
        checks = m2.get("checks", {})
        for mk in ["M2.0", "M2.1", "M2.2", "M2.3", "M2.4", "M2.5"]:
            chk = checks.get(mk)
            if chk:
                sub = {"status": "PASS" if chk.get("pass") else "FAIL"}
                html_parts.append(badge(mk, sub))
            else:
                html_parts.append(badge(mk, None))
    else:
        for mk in ["M2.0", "M2.1", "M2.2", "M2.3", "M2.4", "M2.5"]:
            html_parts.append(badge(mk, None))

    html_parts.append(badge("M3", m3))
    html_parts.append(badge("M4", m4))

    st.markdown(" ".join(html_parts), unsafe_allow_html=True)

    # Resumen de estados
    statuses = {
        "M1": m1.get("status") if m1 else None,
        "M2 (global)": m2.get("status") if m2 else None,
        "M3": m3.get("status") if m3 else None,
        "M4": m4.get("status") if m4 else None,
    }
    with st.expander("📋 Detalle de monitores"):
        for name, st_val in statuses.items():
            if st_val is None:
                st.caption(f"{name}: no ejecutado aún")
            elif st_val == "PASS":
                st.success(f"{name}: PASS ✅")
            else:
                st.error(f"{name}: FAIL ❌")


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

def render_logo():
    if LOGO_PATH.exists():
        with open(LOGO_PATH, encoding="utf-8") as f:
            svg = f.read()
        st.markdown(f'<div style="text-align:center;padding:8px">{svg}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="text-align:center;padding:12px 0 4px 0">'
            '<span style="font-family:monospace;font-size:2.2rem;font-weight:900;'
            'letter-spacing:6px;color:#1f2328">⚽ MATEO</span><br>'
            '<span style="font-size:0.78rem;color:#57606a;letter-spacing:2px">'
            'MOTOR DE ANÁLISIS TÁCTICO Y ESTADÍSTICO DE OPERACIONES FUTBOLÍSTICAS</span>'
            '</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Reloj Maestro
# ---------------------------------------------------------------------------

def render_master_clock(frame: int, n_frames: int = 750, fps: float = 25.0):
    t = frame / fps
    progress = frame / (n_frames - 1)
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.slider(
            "⏱️ Reloj Maestro",
            min_value=0,
            max_value=n_frames - 1,
            value=frame,
            key="master_clock",
            help="Sincroniza los 4 paneles",
        )
    with col2:
        st.metric("Frame", f"{frame:03d}")
    with col3:
        st.metric("Tiempo", f"{t:.2f} s")


# ---------------------------------------------------------------------------
# Panel 1 — Visor de fotograma y bounding boxes
# ---------------------------------------------------------------------------

def render_panel1(frame: int, df_objects: pd.DataFrame | None, fps: float = 30.0):
    st.markdown("### 📹 Panel 1 — Video con Marcas (Sin Radar) y Video Original")

    clip13_dir = _ROOT / "outputs" / "mvp_pruebas" / "mundial_2014_brasil_alemania" / "clip_13"
    post_math_video = clip13_dir / "VIDEO_OMNIMORPH_POST_MATEMATICA.mp4"
    orig_video = _ROOT / "data" / "videos" / "mundial_2014_720p_hd" / "L6sbfskaTDQ-720-13.mp4"
    unified_video = clip13_dir / "VIDEO_UNIFICADO_TODOS_JUNTOS.mp4"
    vtt_path = CLEAN_DIR / "narrations_es.vtt"
    subs_arg = str(vtt_path) if vtt_path.exists() else None

    view_mode = st.segmented_control(
        "Modo de visualización de video",
        options=[
            "🔀 En paralelo (Con Marcas + Original)",
            "✨ Con Marcas (Sin Radar + Audio TTS)",
            "📹 Original (Sin Marcas)",
            "🎬 Percepción Cruda",
        ],
        default="🔀 En paralelo (Con Marcas + Original)",
        label_visibility="collapsed",
    )

    if view_mode == "🔀 En paralelo (Con Marcas + Original)":
        vcol1, vcol2 = st.columns(2)
        with vcol1:
            st.caption("✨ **Video con Marcas MATEO (Sin Radar · Audio TTS + Subtítulos)**")
            if post_math_video.exists():
                st.video(str(post_math_video), subtitles=subs_arg)
            else:
                st.warning("VIDEO_OMNIMORPH_POST_MATEMATICA.mp4 no encontrado.")
        with vcol2:
            st.caption("📹 **Video Original de Referencia (Sin Marcas)**")
            if orig_video.exists():
                st.video(str(orig_video))
            else:
                st.warning("Video original L6sbfskaTDQ-720-13.mp4 no encontrado.")
    elif view_mode == "✨ Con Marcas (Sin Radar + Audio TTS)":
        st.caption("✨ **Video con Marcas MATEO (M2.0–M2.4 · Sin Radar · Audio TTS + Subtítulos)**")
        if post_math_video.exists():
            st.video(str(post_math_video), subtitles=subs_arg)
        else:
            st.warning("VIDEO_OMNIMORPH_POST_MATEMATICA.mp4 no encontrado.")
    elif view_mode == "📹 Original (Sin Marcas)":
        st.caption("📹 **Video Original de Referencia (Sin Marcas)**")
        if orig_video.exists():
            st.video(str(orig_video))
        else:
            st.warning("Video original L6sbfskaTDQ-720-13.mp4 no encontrado.")
    else:
        st.caption("🎬 **Video de Percepción Cruda (6 Modelos sin suavizado)**")
        if unified_video.exists():
            st.video(str(unified_video))
        else:
            st.warning("VIDEO_UNIFICADO_TODOS_JUNTOS.mp4 no encontrado.")

    if df_objects is None:
        st.warning("objects_cleaned.parquet no encontrado. Ejecuta el pipeline primero.")
        return

    with st.expander(f"🔍 Inspector de Cajas por Fotograma (Frame {frame} | t = {frame/fps:.2f} s)", expanded=False):
        df_f = df_objects[df_objects["frame"] == frame]
        max_x_global = float(df_objects["x2"].max()) if len(df_objects) > 0 and "x2" in df_objects.columns else 1280.0
        canvas_w = 1280 if max_x_global <= 1300 else 1920
        canvas_h = 720 if canvas_w == 1280 else 1080

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.patches as mpatches
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 4.5))
            ax.set_xlim(0, canvas_w)
            ax.set_ylim(canvas_h, 0)
            ax.set_facecolor("#1a1a2e")
            fig.patch.set_facecolor("#1a1a2e")
            ax.set_title(f"Frame {frame} | t = {frame/fps:.2f} s ({canvas_w}x{canvas_h})", color="white", fontsize=10)
            ax.axis("off")

            team_colors = {0: "#3b82f6", 1: "#ef4444", None: "#fbbf24"}
            label_colors = {0: "BRA", 1: "GER", None: "REF"}

            df_track = df_f[df_f["source"].isin(["track"])]

            for _, row in df_track.iterrows():
                x1, y1, x2, y2 = row["x1"], row["y1"], row["x2"], row["y2"]
                team = row.get("team")
                if team is not None and not (isinstance(team, float) and np.isnan(team)):
                    team = int(team)
                else:
                    team = None
                tid = row.get("track_id_stitched", row.get("track_id"))
                color = team_colors.get(team, "#94a3b8")

                rect = mpatches.FancyBboxPatch(
                    (x1, y1), x2 - x1, y2 - y1,
                    boxstyle="round,pad=1",
                    linewidth=1.5, edgecolor=color, facecolor="none",
                )
                ax.add_patch(rect)
                label_str = f"{label_colors.get(team, '?')}#{tid}" if tid is not None else "?"
                ax.text(
                    x1, max(y1 - 5, 0), label_str,
                    color=color, fontsize=6, weight="bold",
                    va="bottom",
                )

            df_ball_f = df_f[df_f["source"] == "ball"]
            for _, row in df_ball_f.iterrows():
                bx = (row["x1"] + row["x2"]) / 2
                by = (row["y1"] + row["y2"]) / 2
                circle = plt.Circle((bx, by), 8, color="#f97316", zorder=5)
                ax.add_patch(circle)
                ax.text(bx, by - 12, "BALL", color="#f97316", weight="bold", ha="center", fontsize=7)

            st.pyplot(fig, width="stretch")
            plt.close(fig)

        except ImportError:
            st.info(f"Frame {frame} — {len(df_f)} objetos detectados")
            st.dataframe(df_f[["source", "track_id_stitched", "class_name", "team", "x1", "y1", "x2", "y2"]].head(20))


# ---------------------------------------------------------------------------
# Panel 2 — Radar Cenital 2D
# ---------------------------------------------------------------------------

def render_panel2(frame: int, df_objects: pd.DataFrame | None):
    st.markdown("### 🗺️ Panel 2 — Radar Cenital 2D (Visual de al lado)")

    clip13_dir = _ROOT / "outputs" / "mvp_pruebas" / "mundial_2014_brasil_alemania" / "clip_13"
    radar_video = clip13_dir / "VIDEO_RADAR_POST_MATEMATICA.mp4"

    radar_mode = st.segmented_control(
        "Modo de Radar Cenital",
        options=[
            "🎬 Video Radar 2D + Fotograma Sincronizado",
            "🎬 Solo Video Radar 2D (60 s)",
            "📍 Solo Radar por Fotograma (Reloj Maestro)",
        ],
        default="🎬 Video Radar 2D + Fotograma Sincronizado",
        label_visibility="collapsed",
    )

    if radar_mode in ("🎬 Video Radar 2D + Fotograma Sincronizado", "🎬 Solo Video Radar 2D (60 s)"):
        if radar_video.exists():
            st.caption("🗺️ **Video del Radar Cenital 2D Suavizado (Savitzky-Golay M2.3 + Estelas)**")
            st.video(str(radar_video))
        else:
            st.info("Generando VIDEO_RADAR_POST_MATEMATICA.mp4...")

    if radar_mode == "🎬 Solo Video Radar 2D (60 s)":
        return

    if df_objects is None:
        st.warning("Datos no disponibles.")
        return

    with st.expander(f"📍 Radar Interactivo Sincronizado con Reloj Maestro (Frame {frame})", expanded=(radar_mode == "📍 Solo Radar por Fotograma (Reloj Maestro)")):
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(8, 4.5))
            fig.patch.set_facecolor("#0f172a")
            ax.set_facecolor("#166534")  # verde cancha
            ax.set_xlim(0, 12000)
            ax.set_ylim(0, 7000)
            ax.set_xlabel("← Portería BRA (Brasil)          Portería GER (Alemania) →", color="#94a3b8", fontsize=8)
            ax.set_title(f"Radar Cenital | Frame {frame}", color="white", fontsize=10)

            # Líneas de cancha
            ax.axvline(6000, color="white", linewidth=1, alpha=0.5)
            ax.axhline(3500, color="white", linewidth=0.5, alpha=0.3)
            center_circle = plt.Circle((6000, 3500), 915, fill=False, color="white", linewidth=1, alpha=0.5)
            ax.add_patch(center_circle)
            ax.add_patch(plt.Rectangle((0, 1500), 1650, 4000, fill=False, edgecolor="white", linewidth=1, alpha=0.5))
            ax.add_patch(plt.Rectangle((10350, 1500), 1650, 4000, fill=False, edgecolor="white", linewidth=1, alpha=0.5))

            # Filtrar objetos del frame actual y últimos N frames (trail)
            f_range = range(max(0, frame - 10), frame + 1)
            df_range = df_objects[df_objects["frame"].isin(f_range)]
            df_cur = df_objects[df_objects["frame"] == frame]

            col_arg = "#60a5fa"  # azul claro
            col_fra = "#f87171"  # rojo

            pitch_x_col = "pitch_x_smooth" if "pitch_x_smooth" in df_objects.columns else "pitch_x"
            pitch_y_col = "pitch_y_smooth" if "pitch_y_smooth" in df_objects.columns else "pitch_y"

            # Trails
            for team_id, col in [(0, col_arg), (1, col_fra)]:
                df_team = df_range[
                    (df_range["source"] == "track") &
                    (df_range["team"].notna()) &
                    (df_range["team"].astype(str).str.replace(".0", "", regex=False) == str(team_id))
                ]
                if len(df_team) > 0:
                    ax.scatter(
                        df_team[pitch_x_col], df_team[pitch_y_col],
                        c=col, alpha=0.15, s=8, zorder=1,
                    )

            # Posiciones actuales
            df_track_cur = df_cur[df_cur["source"] == "track"]
            for team_id, col, label in [(0, col_arg, "BRA"), (1, col_fra, "GER")]:
                df_t = df_track_cur[
                    df_track_cur["team"].notna() &
                    (df_track_cur["team"].astype(str).str.replace(".0", "", regex=False) == str(team_id))
                ]
                if len(df_t) > 0:
                    ax.scatter(
                        df_t[pitch_x_col], df_t[pitch_y_col],
                        c=col, s=80, zorder=3, label=label, edgecolors="white", linewidths=0.8,
                    )
                    for _, row in df_t.iterrows():
                        tid = row.get("track_id_stitched", row.get("track_id", ""))
                        ax.annotate(
                            str(tid) if tid is not None else "",
                            (row[pitch_x_col], row[pitch_y_col]),
                            fontsize=5, color="white", ha="center", va="center",
                        )

            # Balón
            df_ball_cur = df_cur[df_cur["source"] == "ball"]
            if len(df_ball_cur) > 0:
                bx = df_ball_cur["pitch_x"].iloc[0]
                by = df_ball_cur["pitch_y"].iloc[0]
                ax.scatter([bx], [by], c="#f97316", s=120, zorder=5, marker="*", label="Balón")

            ax.legend(loc="lower right", fontsize=8, framealpha=0.3, labelcolor="white")
            ax.tick_params(colors="#94a3b8", labelsize=7)
            for spine in ax.spines.values():
                spine.set_edgecolor("#475569")

            st.pyplot(fig, width="stretch")
            plt.close(fig)

        except ImportError:
            st.info(f"Frame {frame} — Radar requiere matplotlib.")
            df_cur = df_objects[df_objects["frame"] == frame]
            st.dataframe(df_cur[["source", "team", "pitch_x", "pitch_y"]].head(25))


# ---------------------------------------------------------------------------
# Panel 3 — Métricas tácticas
# ---------------------------------------------------------------------------

def render_panel3(frame: int, tactical: list | None, fps: float = 30.0):
    st.markdown("### 📊 Panel 3 — Métricas Tácticas")

    if tactical is None:
        st.warning("tactical_summaries.json no encontrado.")
        return

    # Encontrar la ventana activa
    t = frame / fps
    active_window = None
    for w in tactical:
        if w.get("frame_start", 0) <= frame <= w.get("frame_end", 0) or (w["t0"] <= t < w["t1"]):
            active_window = w
            break
    if active_window is None and tactical:
        active_window = tactical[-1]

    if active_window is None:
        st.info("Sin ventana táctica para este frame.")
        return

    w = active_window

    # Semáforo de equipo dominante
    dom = w["dominant_team"]
    if dom in ("ARG", "BRA"):
        dom_color = "#3b82f6"
        dom_label = "🔵 BRA (Brasil) domina"
    elif dom in ("FRA", "GER"):
        dom_color = "#ef4444"
        dom_label = "🔴 GER (Alemania) domina"
    else:
        dom_color = "#94a3b8"
        dom_label = "⚪ Equilibrado"

    st.markdown(
        f'<div class="metric-card" style="border-left: 4px solid {dom_color}">'
        f'<b>Ventana {w["window_id"]}</b> | {w["t0"]:.1f}s – {w["t1"]:.1f}s | {dom_label}'
        f'</div>',
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📏 Block Height", f'{w["block_height_m"]:.2f} m')
        st.metric("🔲 Compacidad", f'{w["block_compactness_m"]:.2f} m')
    with col2:
        st.metric("💨 Trans. Speed", f'{w["transition_speed_mps"]:.2f} m/s')
        st.metric("🎯 Presión", w["pressure_context"].capitalize())
    with col3:
        st.metric("👥 N BRA", w.get("n_arg", "—"))
        st.metric("👥 N GER", w.get("n_fra", "—"))

    # Centroides
    c_arg = w.get("centroid_arg_x_cm", 6000)
    c_fra = w.get("centroid_fra_x_cm", 6000)
    st.caption(
        f"Centroide BRA: {c_arg/100:.1f} m | Centroide GER: {c_fra/100:.1f} m"
    )


# ---------------------------------------------------------------------------
# Panel 4 — Crónica táctica + Audio TTS
# ---------------------------------------------------------------------------

def render_panel4(frame: int, narrations: list | None, tactical: list | None, fps: float = 30.0):
    st.markdown("### 🎙️ Panel 4 — Crónica Táctica + Audio TTS y Transcriptor")

    if narrations is None:
        st.warning("narrations.json no encontrado.")
        return

    # 1. Reproductor de Audio Maestro Continuo (60 s sincronizados)
    master_wav = AUDIO_DIR / "NARRACION_COMPLETA_60S.wav"
    if master_wav.exists():
        st.caption("🔊 **Audio Maestro Continuo (60 s — Todas las ventanas sincronizadas con el video)**")
        st.audio(str(master_wav), format="audio/wav", autoplay=False)

    t = frame / fps
    active_narr = None
    for n in narrations:
        if n.get("t0", 0) <= t < n.get("t1", 4):
            active_narr = n
            break
    if active_narr is None and narrations:
        active_narr = narrations[-1]

    if active_narr is None:
        st.info("Sin narración para este frame.")
        return

    wid = active_narr["window_id"]
    mode = active_narr.get("mode", "offline")
    t0_act = float(active_narr.get("t0", 0.0))
    t1_act = float(active_narr.get("t1", 0.0))

    st.markdown(
        f'<div class="metric-card" style="border-left: 4px solid #22c55e">'
        f'<b>🟢 Ventana Activa: {wid}</b> ({t0_act:.1f}s – {t1_act:.1f}s) '
        f'<span style="font-size:11px;color:#64748b">[{mode}]</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.info(f"**🎙️ Narración ({wid}):** {active_narr.get('narracion_es', '—')}")

    # Reproductor de audio de la ventana individual
    audio_path = None
    for ext in [".mp3", ".wav"]:
        candidate = AUDIO_DIR / f"{wid}{ext}"
        if candidate.exists():
            audio_path = candidate
            break

    if audio_path:
        mime = "audio/mp3" if audio_path.suffix == ".mp3" else "audio/wav"
        st.audio(str(audio_path), format=mime, autoplay=False)
        st.caption(f"🔊 Audio individual ({wid}): `{audio_path.name}`")
    else:
        st.caption("🔇 Audio no generado aún (ejecuta tts_service.py)")

    with st.expander(f"📋 Análisis táctico detallado ({wid})", expanded=False):
        st.write(active_narr.get("analisis_tactico", "—"))
        lat = active_narr.get("latency_ms", 0)
        tok_in = active_narr.get("tokens_in", 0)
        tok_out = active_narr.get("tokens_out", 0)
        st.caption(f"Latencia: {lat:.0f} ms | Tokens in/out: {tok_in}/{tok_out}")

    # 2. Transcriptor Sincronizado Completo (W0..W7)
    with st.expander("📝 Transcriptor Completo Sincronizado (Todas las Ventanas)", expanded=True):
        for n in narrations:
            n_wid = n.get("window_id", "?")
            n_t0 = float(n.get("t0", 0.0))
            n_t1 = float(n.get("t1", 0.0))
            n_txt = n.get("narracion_es", "—")
            is_cur = (n_wid == wid)
            bg = "#dcfce7" if is_cur else "#f8fafc"
            border = "#22c55e" if is_cur else "#cbd5e1"
            badge_str = "🟢 EN CURSO" if is_cur else "⏱️"
            st.markdown(
                f'<div style="background:{bg};border-left:4px solid {border};'
                f'padding:8px 10px;border-radius:6px;margin:4px 0;font-size:13px">'
                f'<b>{badge_str} [{n_wid}] {n_t0:05.2f}s – {n_t1:05.2f}s:</b> {n_txt}'
                f'</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar():
    with st.sidebar:
        st.markdown("## ⚽ MATEO")
        st.caption("Motor de Análisis Táctico y\nEstadístico de Operaciones Futbolísticas")
        st.markdown("---")
        st.markdown("## ⚙️ Controles")

        # Auto-play
        autoplay = st.checkbox("▶ Auto-play", value=False)
        fps_play = st.slider("FPS de reproducción", 1, 25, 5)

        st.markdown("---")
        st.markdown("### 📂 Estado de archivos")

        files_to_check = {
            "frames_clean.parquet": CLEAN_DIR / "frames_clean.parquet",
            "objects_cleaned.parquet": CLEAN_DIR / "objects_cleaned.parquet",
            "tactical_summaries.json": CLEAN_DIR / "tactical_summaries.json",
            "narrations.json": CLEAN_DIR / "narrations.json",
            "monitor_m1.json": CLEAN_DIR / "monitor_m1.json",
            "monitor_m2.json": CLEAN_DIR / "monitor_m2.json",
            "monitor_m3.json": CLEAN_DIR / "monitor_m3.json",
            "monitor_m4.json": CLEAN_DIR / "monitor_m4.json",
        }

        for name, path in files_to_check.items():
            if path.exists():
                size_kb = path.stat().st_size / 1024
                st.success(f"✅ {name} ({size_kb:.0f} KB)")
            else:
                st.error(f"❌ {name}")

        st.markdown("---")
        st.markdown("### 🔄 Recargar datos")
        if st.button("🔄 Limpiar caché"):
            st.cache_data.clear()
            st.rerun()

        return autoplay, fps_play


# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------

def main():
    # Logo
    render_logo()
    st.markdown("---")

    # Semáforos
    render_semaphores()
    st.markdown("---")

    # Sidebar
    autoplay, fps_play = render_sidebar()

    # Cargar datos
    df_objects = load_objects()
    df_frames = load_frames()
    tactical = load_tactical()
    narrations = load_narrations()

    # Reloj Maestro dinámico según frames cargados (1800 en Clip 13 @ 30 fps o 750 @ 25 fps)
    n_frames = len(df_frames) if df_frames is not None and len(df_frames) > 0 else 750
    fps = 30.0 if n_frames > 1000 else 25.0
    if "master_clock_val" not in st.session_state:
        first_track_frame = 0
        if df_objects is not None and "source" in df_objects.columns:
            tr_frames = df_objects.loc[df_objects["source"] == "track", "frame"]
            if len(tr_frames) > 0:
                first_track_frame = int(tr_frames.min())
        st.session_state["master_clock_val"] = first_track_frame

    frame = min(st.session_state["master_clock_val"], n_frames - 1)

    # Renderizar slider del reloj maestro
    st.markdown("### ⏱️ Reloj Maestro Común")
    frame = st.slider(
        "Frame",
        min_value=0,
        max_value=n_frames - 1,
        value=frame,
        key="master_clock_main",
        help="Sincroniza los 4 paneles: Panel 1 (video), Panel 2 (radar), Panel 3 (métricas), Panel 4 (narración)",
    )
    # Sincronizar el valor interno con lo que el usuario movió en el slider
    st.session_state["master_clock_val"] = frame
    t_cur = frame / fps
    st.caption(f"🕐 t = {t_cur:.2f} s / {(n_frames/fps):.1f} s | Frame {frame}/{n_frames-1} ({fps:.0f} FPS)")
    st.markdown("---")

    # 4 paneles en 2×2
    col1, col2 = st.columns(2)
    with col1:
        render_panel1(frame, df_objects, fps=fps)
    with col2:
        render_panel2(frame, df_objects)

    st.markdown("---")
    col3, col4 = st.columns(2)
    with col3:
        render_panel3(frame, tactical, fps=fps)
    with col4:
        render_panel4(frame, narrations, tactical, fps=fps)

    # Auto-play — actualiza el key interno (no el key del widget) antes de rerun
    if autoplay:
        time.sleep(1.0 / fps_play)
        st.session_state["master_clock_val"] = (frame + 1) % n_frames
        st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        '<p style="text-align:center;color:#64748b;font-size:12px">'
        'MATEO · Omnimorph AI Lab · IBM watsonx.ai · <code>ibm/granite-4-h-small</code>'
        '</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
