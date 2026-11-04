"""
implementacion/dashboard/pages/3_Chatbot_Granite.py
====================================================
MATEO · Asistente conversacional sobre Brasil 1-7 Alemania
Modelo: ibm/granite-4-h-small vía watsonx.ai. Lógica en cloud_agent/chat_agent.py.
"""

from __future__ import annotations

import pathlib
import sys

import streamlit as st

_ROOT = pathlib.Path(__file__).parent.parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from implementacion.cloud_agent import chat_agent

MAX_PREGUNTAS_SESION = 30
PREGUNTAS_SUGERIDAS = [
    "¿Quién marcó cada gol y en qué minuto?",
    "Compara el xG de ambos equipos en cada tiempo.",
    "¿Cómo se generó el gol de Müller?",
    "¿Qué bajas tuvo Brasil?",
]

st.set_page_config(
    page_title="MATEO · Chatbot Granite",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(ttl=3600, show_spinner="Conectando con Granite…")
def cargar_modelo():
    return chat_agent.obtener_modelo()


@st.cache_data(ttl=300, show_spinner=False)
def cargar_datos() -> dict:
    return chat_agent.cargar_datos()


def texto_metricas(mensaje: dict) -> str:
    if mensaje["origen"] == "regla":
        return "Respuesta directa desde los datos, sin LLM"
    return (
        f"{chat_agent.REQUIRED_MODEL} · {mensaje['latency_ms']:.0f} ms · "
        f"tokens {mensaje['tokens_in']}/{mensaje['tokens_out']} · {mensaje['status']}"
    )


def mostrar_aviso_atribucion(hallazgos: list[str]) -> None:
    if hallazgos:
        st.warning(
            "\n".join(f"- {hallazgo}" for hallazgo in hallazgos),
            icon=":material/rule:",
            title="Revisa estas cifras: no coinciden con los datos",
        )


def mostrar_aviso_cifras(numeros: list[str]) -> None:
    if numeros:
        st.warning(
            f"Estas cifras no aparecen tal cual en los datos: {', '.join(numeros)}. "
            "Pueden ser cálculos válidos o errores del modelo.",
            icon=":material/fact_check:",
            title="Revisa la respuesta",
        )


if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

st.title("Chatbot táctico")
st.caption(
    "Responde sobre Brasil 1–7 Alemania solo con los datos del partido · "
    f"`{chat_agent.REQUIRED_MODEL}` en IBM watsonx.ai · "
    "Puede equivocarse, sobre todo en preguntas abiertas o comparaciones amplias: "
    "verifica las cifras en la página de análisis."
)

modelo = cargar_modelo()
if modelo is None:
    st.warning(
        "Revisa `IBM_CLOUD_API_KEY`, `WATSONX_URL` y `WATSONX_SPACE_ID` o "
        "`WATSONX_PROJECT_ID` en `.env`, y que el SDK `ibm-watsonx-ai` esté instalado.",
        title="Granite no está disponible",
    )

n_preguntas = sum(1 for m in st.session_state.mensajes if m["role"] == "user")
limite_alcanzado = n_preguntas >= MAX_PREGUNTAS_SESION
chat_habilitado = modelo is not None and not limite_alcanzado

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])
        if mensaje["role"] == "assistant":
            mostrar_aviso_atribucion(mensaje["atribucion_incorrecta"])
            mostrar_aviso_cifras(mensaje["numeros_sin_respaldo"])
            for aviso in chat_agent.avisos_calidad(mensaje["content"]):
                st.caption(aviso)
            st.caption(texto_metricas(mensaje))

sugerida = None
if not st.session_state.mensajes:
    sugerida = st.pills(
        "Preguntas sugeridas",
        PREGUNTAS_SUGERIDAS,
        disabled=not chat_habilitado,
        key="pregunta_sugerida",
    )
elif st.button("Nueva conversación", icon=":material/refresh:"):
    st.session_state.mensajes = []
    st.rerun()

if limite_alcanzado:
    st.info(
        f"Esta conversación llegó al límite de {MAX_PREGUNTAS_SESION} preguntas. "
        "Empieza una nueva para continuar."
    )

escrita = st.chat_input(
    "Pregunta sobre el partido",
    max_chars=chat_agent.MAX_CARACTERES_PREGUNTA,
    disabled=not chat_habilitado,
    submit_mode="disable",
)
pregunta = escrita or sugerida

if pregunta and chat_habilitado:
    datos = cargar_datos()
    contexto = chat_agent.serializar_contexto(datos)
    historial = list(st.session_state.mensajes)
    with st.chat_message("user"):
        st.markdown(pregunta)

    metricas: dict = {}
    respuesta = chat_agent.respuesta_sin_datos(pregunta, datos)
    origen = "regla" if respuesta else "granite"
    with st.chat_message("assistant"):
        if respuesta is None:
            try:
                respuesta = st.write_stream(
                    chat_agent.responder_stream(
                        modelo,
                        chat_agent.construir_mensajes(pregunta, historial, datos),
                        metricas,
                    )
                )
            except Exception as error:
                chat_agent.auditar_respuesta(
                    pregunta, None, contexto, metricas, error=str(error)
                )
                st.error(
                    "Inténtalo de nuevo en unos segundos.",
                    title="Granite no pudo responder",
                )
                st.stop()

        auditoria = chat_agent.auditar_respuesta(
            pregunta, respuesta, contexto, metricas, origen=origen, hechos=datos["hechos"]
        )

    st.session_state.mensajes += [
        {"role": "user", "content": pregunta},
        {
            "role": "assistant",
            "content": respuesta,
            "origen": origen,
            "latency_ms": auditoria["latency_ms"],
            "tokens_in": auditoria["tokens_in"],
            "tokens_out": auditoria["tokens_out"],
            "status": auditoria["status"],
            "numeros_sin_respaldo": auditoria["numeros_sin_respaldo"],
            "atribucion_incorrecta": auditoria["atribucion_incorrecta"],
        },
    ]
    st.rerun()
