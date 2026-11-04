"""
implementacion/dashboard/pages/1_Observabilidad.py
===================================================
MATEO · Página de Observabilidad del Pipeline
Muestra el estado detallado de los 9 monitores (M1, M2.0–M2.5, M3, M4)
con métricas completas, timeline de ejecución y auditoría de gobernanza IBM.

Se abre automáticamente en la barra lateral de Streamlit como segunda página.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

CLEAN_DIR = _ROOT / "data" / "clean"

st.set_page_config(
    page_title="MATEO · Observabilidad",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .pass-chip  { display:inline-block; background:#dcfce7; color:#166534;
                  padding:3px 10px; border-radius:12px; font-weight:700;
                  font-size:13px; margin:2px; }
    .fail-chip  { display:inline-block; background:#fee2e2; color:#991b1b;
                  padding:3px 10px; border-radius:12px; font-weight:700;
                  font-size:13px; margin:2px; }
    .miss-chip  { display:inline-block; background:#f1f5f9; color:#64748b;
                  padding:3px 10px; border-radius:12px; font-style:italic;
                  font-size:13px; margin:2px; }
    .monitor-header { font-size:1.05rem; font-weight:800; margin-bottom:2px; }
    .kv-row { border-bottom:1px solid #e5e7eb; padding:4px 0;
              display:flex; justify-content:space-between; }
    .kv-key { color:#57606a; font-size:13px; }
    .kv-val { font-weight:600; font-size:13px; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_data(ttl=10)
def load_json(path: pathlib.Path) -> dict | None:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


@st.cache_data(ttl=10)
def load_pipeline_summary() -> dict | None:
    return load_json(CLEAN_DIR / "pipeline_summary.json")


@st.cache_data(ttl=10)
def load_governance_audit() -> list[dict]:
    p = CLEAN_DIR / "governance_audit.jsonl"
    if not p.exists():
        return []
    rows = []
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def chip(label: str, passed: bool | None) -> str:
    if passed is None:
        return f'<span class="miss-chip">— {label}</span>'
    cls = "pass-chip" if passed else "fail-chip"
    icon = "✅" if passed else "❌"
    return f'<span class="{cls}">{icon} {label}</span>'


def kv(key: str, val) -> str:
    return (
        f'<div class="kv-row">'
        f'<span class="kv-key">{key}</span>'
        f'<span class="kv-val">{val}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    '<h2 style="margin-bottom:0">🚦 MATEO · Observabilidad del Pipeline</h2>'
    '<p style="color:#57606a;margin-top:4px;font-size:14px">'
    'Estado en tiempo real de los 9 monitores de verificación · '
    'IBM watsonx.ai · <code>ibm/granite-4-h-small</code></p>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ---------------------------------------------------------------------------
# Resumen global
# ---------------------------------------------------------------------------

summary = load_pipeline_summary()

if summary:
    all_pass = summary.get("all_pass", False)
    elapsed  = summary.get("elapsed_s", 0)
    ts       = summary.get("timestamp", "—")
    mon_res  = summary.get("monitor_results", {})

    col_s, col_e, col_t = st.columns(3)
    with col_s:
        if all_pass:
            st.success("### ✅ PIPELINE: 9/9 PASS")
        else:
            failed = [k for k, v in mon_res.items() if v != "PASS"]
            st.error(f"### ❌ FALLOS: {', '.join(failed)}")
    with col_e:
        st.metric("⏱ Tiempo total", f"{elapsed:.1f} s")
    with col_t:
        st.metric("🕐 Última ejecución", ts[:19].replace("T", " ") if len(ts) > 10 else ts)

    # Chips de todos los monitores
    chips_html = " ".join(
        chip(k, v == "PASS") for k, v in mon_res.items()
    )
    st.markdown(chips_html, unsafe_allow_html=True)
else:
    st.warning("pipeline_summary.json no encontrado. Ejecuta `run_pipeline.py --use-real` primero.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Monitores individuales en tabs
# ---------------------------------------------------------------------------

tab_m1, tab_m2, tab_m3, tab_m4 = st.tabs(
    ["📡 M1 · Percepción", "⚙️ M2.0–M2.5 · Engine", "🤖 M3 · Gobernanza IBM", "🔊 M4 · TTS & Sync"]
)

# ── M1 ──────────────────────────────────────────────────────────────────────
with tab_m1:
    m1 = load_json(CLEAN_DIR / "monitor_m1.json")
    if m1 is None:
        st.info("monitor_m1.json no disponible.")
    else:
        st.markdown(
            f'<p class="monitor-header">M1 · {m1["name"]} '
            f'{chip("PASS" if m1["status"]=="PASS" else "FAIL", m1["status"]=="PASS")}</p>',
            unsafe_allow_html=True,
        )
        checks = m1.get("checks", {})
        col_a, col_b = st.columns(2)
        with col_a:
            fc = checks.get("frames_total", {})
            st.metric("Frames procesados", fc.get("observed", "—"), delta=f"≥ {fc.get('expected', 750)} req.")
            sc = checks.get("source_track_present", {})
            st.metric("Tracks detectados", sc.get("observed_count", "—"))
        with col_b:
            hc = checks.get("homography_valid_rate", {})
            rate = hc.get("observed_rate", 0)
            st.metric("Homografía cruda válida", f"{rate*100:.1f}%")
            bc = checks.get("source_ball_present", {})
            st.metric("Detecciones de balón", bc.get("observed_count", "—"))

        st.caption(f"Elapsed: {m1.get('elapsed_ms', 0):.1f} ms · {m1.get('timestamp','')[:19]}")

# ── M2 ──────────────────────────────────────────────────────────────────────
with tab_m2:
    m2 = load_json(CLEAN_DIR / "monitor_m2.json")
    if m2 is None:
        st.info("monitor_m2.json no disponible.")
    else:
        checks = m2.get("checks", {})
        passed = m2.get("summary", {}).get("passed", 0)
        total  = m2.get("summary", {}).get("total", 6)
        st.markdown(
            f'<p class="monitor-header">M2 · Stage Monitors '
            f'{chip(f"{passed}/{total} PASS", passed == total)}</p>',
            unsafe_allow_html=True,
        )

        monitor_defs = {
            "M2.0": "Separación track/ball y moda de equipo",
            "M2.1": "Homografía EMA normalizada",
            "M2.2": "Track Stitching (Algoritmo Húngaro)",
            "M2.3": "Cinemática Savitzky-Golay",
            "M2.4": "Ventanas Tácticas (4.0 s)",
            "M2.5": "Integridad del pipeline completo",
        }

        for mk, mname in monitor_defs.items():
            chk = checks.get(mk, {})
            passed_chk = chk.get("pass", None)
            details    = chk.get("details", {})

            with st.expander(
                f"{chip(mk, passed_chk)} {mname}", expanded=False
            ):
                html_rows = ""
                for k, v in details.items():
                    if isinstance(v, float):
                        v = f"{v:.4f}"
                    elif isinstance(v, list):
                        v = f"{len(v)} items"
                    html_rows += kv(k, v)
                if html_rows:
                    st.markdown(html_rows, unsafe_allow_html=True)
                else:
                    st.caption("Sin detalles disponibles.")

# ── M3 ──────────────────────────────────────────────────────────────────────
with tab_m3:
    m3 = load_json(CLEAN_DIR / "monitor_m3.json")
    if m3 is None:
        st.info("monitor_m3.json no disponible.")
    else:
        s = m3.get("summary", {})
        st.markdown(
            f'<p class="monitor-header">M3 · {m3["name"]} '
            f'{chip("PASS" if m3["status"]=="PASS" else "FAIL", m3["status"]=="PASS")}</p>',
            unsafe_allow_html=True,
        )

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Modelo", s.get("model_used", "—").split("/")[-1])
        with col_b:
            st.metric("Llamadas validadas", f'{s.get("passed_calls",0)}/{s.get("total_calls",0)}')
        with col_c:
            st.metric("Latencia media", f'{s.get("latency_ms_mean", 0):.0f} ms')
        with col_d:
            st.metric("RU consumidas (est.)", f'{s.get("total_cost_ru_est", 0):.4f}')

        st.markdown(
            kv("Tokens in (media)", f'{s.get("tokens_in_mean", 0):.1f}') +
            kv("Tokens out (media)", f'{s.get("tokens_out_mean", 0):.1f}') +
            kv("Latencia máxima", f'{s.get("latency_ms_max", 0):.0f} ms') +
            kv("Timestamp", m3.get("timestamp", "—")[:19]),
            unsafe_allow_html=True,
        )

        # Audit log de gobernanza
        st.markdown("#### 📋 Registro de Gobernanza (governance_audit.jsonl)")
        audit_rows = load_governance_audit()
        if audit_rows:
            df_audit = pd.DataFrame(audit_rows)
            # Mostrar columnas relevantes si existen
            cols_show = [c for c in ["window_id", "model_id", "status", "latency_ms",
                                      "tokens_in", "tokens_out", "timestamp"] if c in df_audit.columns]
            st.dataframe(df_audit[cols_show] if cols_show else df_audit,
                         height=280)
        else:
            st.caption("governance_audit.jsonl vacío o no encontrado.")

# ── M4 ──────────────────────────────────────────────────────────────────────
with tab_m4:
    m4 = load_json(CLEAN_DIR / "monitor_m4.json")
    if m4 is None:
        st.info("monitor_m4.json no disponible.")
    else:
        sm = m4.get("summary", {})
        chks = m4.get("checks", {})
        st.markdown(
            f'<p class="monitor-header">M4 · {m4["name"]} '
            f'{chip("PASS" if m4["status"]=="PASS" else "FAIL", m4["status"]=="PASS")}</p>',
            unsafe_allow_html=True,
        )

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Clips TTS generados", f'{sm.get("n_generated",0)}/{sm.get("n_expected",0)}')
        with col_b:
            st.metric("Duración media", f'{sm.get("mean_duration_s", 0):.2f} s')
        with col_c:
            st.metric("Desfase máx. reloj", f'{chks.get("clock_offset",{}).get("max_observed_ms",0):.1f} ms')

        # Tabla por ventana
        dur_per = chks.get("duration_within_limit", {}).get("per_window", {})
        off_per = chks.get("clock_offset", {}).get("per_window", {})
        if dur_per:
            rows_tts = []
            for wid in sorted(dur_per.keys()):
                audio_path = _ROOT / "data" / "audio" / f"{wid}.wav"
                rows_tts.append({
                    "Ventana": wid,
                    "Duración (s)": dur_per.get(wid, "—"),
                    "Desfase (ms)": off_per.get(wid, "—"),
                    "Archivo": "✅" if audio_path.exists() else "❌",
                })
            df_tts = pd.DataFrame(rows_tts)
            st.dataframe(df_tts, hide_index=True)

            # Reproductor rápido de audios
            st.markdown("#### 🔊 Reproducir clips TTS")
            audio_cols = st.columns(4)
            for i, wid in enumerate(sorted(dur_per.keys())):
                ap = _ROOT / "data" / "audio" / f"{wid}.wav"
                with audio_cols[i % 4]:
                    if ap.exists():
                        st.caption(wid)
                        st.audio(str(ap))
                    else:
                        st.caption(f"{wid} — ❌")

        st.caption(f"Motor TTS: {m4.get('engine_used','—')} · {m4.get('timestamp','')[:19]}")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    '<p style="text-align:center;color:#64748b;font-size:12px">'
    'MATEO · Omnimorph AI Lab · IBM watsonx.ai · <code>ibm/granite-4-h-small</code>'
    '</p>',
    unsafe_allow_html=True,
)
