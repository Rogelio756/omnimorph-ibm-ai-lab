"""
implementacion/dashboard/pages/2_Analisis_Brasil_Alemania.py
=============================================================
MATEO · Centro de partido Brasil 1-7 Alemania (semifinal, Mundial 2014)
Ficha previa, comparativa 1T/2T, los 8 goles y el detalle del gol de Müller.
"""

from __future__ import annotations

import pathlib
import sys

import altair as alt
import streamlit as st

_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.dashboard import partido_data as datos

COLORES_EQUIPO = alt.Scale(
    domain=["Brasil", "Alemania"],
    range=["#2563eb", "#dc2626"],
)

st.set_page_config(
    page_title="MATEO · Brasil 1-7 Alemania",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(ttl=300)
def cargar_todo() -> tuple[dict, dict, list, dict]:
    return (
        datos.cargar_contexto(),
        datos.cargar_estadisticas(),
        datos.cargar_goles(),
        datos.cargar_gol_muller(),
    )


@st.cache_data(ttl=300)
def cargar_svg(nombre: str) -> str:
    return datos.cargar_svg(nombre)


try:
    contexto, estadisticas, goles, gol_muller = cargar_todo()
except FileNotFoundError as error:
    st.error(
        f"Falta un archivo en `data/partidos/brasil_alemania_2014/`: {error.filename}",
        title="Datos del partido no disponibles",
    )
    st.stop()

info = contexto["partido_info"]
equipos = contexto["equipos"]

# ---------------------------------------------------------------------------
# Encabezado
# ---------------------------------------------------------------------------
st.title("Brasil 1–7 Alemania")
st.caption(
    f"{info['fase']} · {info['competicion']} · {info['fecha']} · "
    f"{info['estadio']}, {info['ciudad']}"
)
st.info(
    "Los desgloses por tiempo y la posesión total no tienen confirmación oficial, "
    "y el xG es estimado. Los tiros a puerta de Alemania por tiempo son derivados. "
    "El detalle está en `PROCEDENCIA.md`.",
    icon=":material/info:",
    title="Calidad de los datos",
)

tab_ficha, tab_stats, tab_goles, tab_muller = st.tabs(
    ["Ficha previa", "Comparativa 1T / 2T", "Los 8 goles", "Gol de Müller"]
)

# ---------------------------------------------------------------------------
# Ficha previa
# ---------------------------------------------------------------------------
with tab_ficha:
    arbitro = info["arbitro"]
    clima = info["condiciones_climaticas"]
    fila = st.columns(4)
    fila[0].metric("Marcador final", info["resultado"]["marcador_final"])
    fila[1].metric("Descanso", info["resultado"]["primer_tiempo"])
    fila[2].metric("Asistencia", f"{info['asistencia']:,}".replace(",", "."))
    fila[3].metric("Temperatura", f"{clima['temperatura_c']} °C")
    st.caption(
        f"Árbitro: {arbitro['principal']} ({arbitro['pais']}) · "
        f"Asistentes: {arbitro['asistente_1']} y {arbitro['asistente_2']} · "
        f"Cuarto árbitro: {arbitro['cuarto_arbitro']}"
    )

    configuracion_plantilla = {
        "Dorsal": st.column_config.NumberColumn(width="small", format="%d"),
        "Minutos": st.column_config.NumberColumn(width="small", format="%d"),
    }
    for columna, clave in zip(st.columns(2), datos.EQUIPOS):
        equipo = equipos[clave]
        plantilla = datos.plantilla_df(equipo)
        with columna:
            st.subheader(equipo["pais"])
            st.caption(
                f"Entrenador: {equipo['entrenador']} · "
                f"Esquema: {equipo['esquema_inicial']} · "
                f"Capitán: {equipo['capitan']}"
            )
            for baja in equipo["bajas_previas"]:
                st.warning(baja["motivo"], title=f"Baja: {baja['nombre']}")
            st.markdown("**Titulares**")
            st.dataframe(
                plantilla[plantilla["Titular"]].drop(columns="Titular"),
                hide_index=True,
                column_config=configuracion_plantilla,
                alt=f"Once titular de {equipo['pais']}",
            )
            st.markdown("**Suplentes**")
            st.dataframe(
                plantilla[~plantilla["Titular"]].drop(columns="Titular"),
                hide_index=True,
                column_config=configuracion_plantilla,
                alt=f"Suplentes de {equipo['pais']}",
            )

# ---------------------------------------------------------------------------
# Comparativa 1T / 2T
# ---------------------------------------------------------------------------
with tab_stats:
    etiqueta = st.selectbox("Métrica", list(datos.METRICAS.values()), index=1)
    clave_metrica = next(k for k, v in datos.METRICAS.items() if v == etiqueta)
    serie = datos.metrica_por_tiempo_df(estadisticas, clave_metrica)

    base = alt.Chart(serie).encode(
        x=alt.X("Tiempo:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Equipo:N", sort=list(datos.EQUIPOS.values())),
        y=alt.Y("Valor:Q", title=etiqueta, scale=alt.Scale(zero=True)),
    )
    barras = base.mark_bar(
        cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=56
    ).encode(
        color=alt.Color(
            "Equipo:N",
            scale=COLORES_EQUIPO,
            legend=alt.Legend(title=None, orient="top"),
        ),
        tooltip=["Tiempo", "Equipo", alt.Tooltip("Valor:Q", title=etiqueta)],
    )
    color_texto = "#ffffff" if st.context.theme.type == "dark" else "#111111"
    valores = base.mark_text(dy=-8, color=color_texto).encode(text=alt.Text("Valor:Q"))
    st.altair_chart(
        barras + valores,
        height=320,
        alt=f"{etiqueta} de Brasil y Alemania en cada tiempo",
    )

    st.subheader("Todas las métricas")
    st.dataframe(
        datos.comparativa_df(estadisticas),
        hide_index=True,
        height="content",
        alt="Estadísticas de Brasil y Alemania por tiempo y en total",
    )

# ---------------------------------------------------------------------------
# Los 8 goles
# ---------------------------------------------------------------------------
with tab_goles:
    st.image(
        cargar_svg("mapa_8_goles.svg"),
        width="stretch",
        alt="Mapa de la cancha con la posición de remate de los 8 goles",
    )
    st.caption(
        "El tamaño de cada punto indica el xG estimado del remate. Las coordenadas están "
        "normalizadas: Alemania siempre ataca hacia la izquierda, también en el 2T."
    )
    st.dataframe(
        datos.goles_df(goles),
        hide_index=True,
        column_config={
            "xG (estimado)": st.column_config.NumberColumn(format="%.2f"),
            "Distancia (m)": st.column_config.NumberColumn(format="%.1f"),
        },
        alt="Cronología de los 8 goles del partido",
    )

    gol = st.selectbox(
        "Detalle del gol",
        goles,
        format_func=lambda g: f"{g['minuto']}' · {g['anotador']['nombre']} ({g['marcador_momento']})",
    )
    with st.container(border=True):
        st.markdown(f"**Análisis táctico.** {gol['nota_tactica']}")
        st.markdown(f"**Relato.** {gol['narracion']}")

# ---------------------------------------------------------------------------
# Gol de Müller
# ---------------------------------------------------------------------------
with tab_muller:
    jugada = gol_muller["metadatos_jugada"]
    ventana_gol = gol_muller["ventanas_tacticas"][-1]
    metricas = ventana_gol["metricas"]
    acumulado = gol_muller["estadisticas_acumuladas_minuto_11"]

    st.subheader(f"{jugada['minuto_oficial']}' · {jugada['anotador']['nombre']}")
    st.caption(f"{jugada['tipo_jugada']} · Reloj {jugada['reloj_partido']}")

    st.image(
        cargar_svg("radar_gol_muller.svg"),
        width="stretch",
        alt="Radar cenital de la pantalla de Klose y Höwedes y el remate de Müller",
    )
    fila = st.columns(4)
    fila[0].metric("Distancia", f"{metricas['distancia_remate_m']} m")
    fila[1].metric("xG (estimado)", f"{metricas['xg']:.2f}")
    fila[2].metric("Separación", f"{metricas['separacion_marca_radio_m']} m")
    fila[3].metric("Velocidad", f"{metricas['velocidad_remate_kmh']} km/h")
    st.caption("Separación y velocidad no tienen fuente independiente.")
    st.markdown(f"**Hasta el gol.** {acumulado['resumen_tramo_inicial']}")

    for ventana in gol_muller["ventanas_tacticas"]:
        with st.expander(
            f"Ventana {ventana['ventana_id']} · {ventana['t0']:.0f}–{ventana['t1']:.0f} s · {ventana['fase']}"
        ):
            st.markdown(ventana["texto_tactico"])
            st.caption(ventana["texto_narracion"])

st.divider()
st.caption("MATEO · Omnimorph AI Lab · Datos en `data/partidos/brasil_alemania_2014/`")
