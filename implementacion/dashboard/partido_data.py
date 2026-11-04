"""
implementacion/dashboard/partido_data.py
========================================
Carga y prepara los datos de Brasil 1-7 Alemania (data/partidos/brasil_alemania_2014/).

No depende de Streamlit: la Página 2 y el chatbot comparten este módulo.
La procedencia de cada dato y lo que sigue sin verificar está en PROCEDENCIA.md.
"""

from __future__ import annotations

import json
import pathlib

import pandas as pd

_ROOT = pathlib.Path(__file__).parent.parent.parent
PARTIDO_DIR = _ROOT / "data" / "partidos" / "brasil_alemania_2014"

EQUIPOS = {"brasil": "Brasil", "alemania": "Alemania"}
PERIODOS = {
    "primer_tiempo": "1T",
    "segundo_tiempo": "2T",
    "tiempo_completo": "Total",
}

# Clave en estadisticas_partido.json -> etiqueta en pantalla
METRICAS = {
    "posesion_pct": "Posesión (%)",
    "tiros_totales": "Tiros totales",
    "tiros_a_puerta": "Tiros a puerta",
    "tiros_dentro_area": "Tiros dentro del área",
    "tiros_fuera_area": "Tiros fuera del área",
    "xg_esperado": "xG (estimado)",
    "precision_pases_pct": "Precisión de pases (%)",
    "corners": "Córners",
    "faltas_cometidas": "Faltas cometidas",
    "fueras_de_juego": "Fueras de juego",
    "atajadas_portero": "Atajadas",
    "recuperaciones": "Recuperaciones",
}


def _leer_json(ruta_relativa: str) -> dict | list:
    with open(PARTIDO_DIR / ruta_relativa, encoding="utf-8") as f:
        return json.load(f)


def cargar_contexto() -> dict:
    return _leer_json("partido/contexto_partido.json")


def cargar_estadisticas() -> dict:
    return _leer_json("partido/estadisticas_partido.json")


def cargar_goles() -> list[dict]:
    return _leer_json("partido/cronologia_goles.json")


def cargar_gol_muller() -> dict:
    return _leer_json("gol_muller/gol_muller_min11.json")


def cargar_svg(nombre: str) -> str:
    return (PARTIDO_DIR / "assets" / nombre).read_text(encoding="utf-8")


def plantilla_df(equipo: dict) -> pd.DataFrame:
    """Plantilla de un equipo: una fila por jugador, en el orden del archivo."""
    return pd.DataFrame(
        [
            {
                "Dorsal": int(dorsal),
                "Jugador": jugador["nombre"],
                "Posición": jugador["posicion"],
                "Titular": jugador["titular"],
                "Minutos": jugador["minutos"],
                "Eventos": " · ".join(jugador["eventos"]),
            }
            for dorsal, jugador in equipo["plantilla"].items()
        ]
    )


def comparativa_df(estadisticas: dict) -> pd.DataFrame:
    """Tabla ancha: una fila por métrica y una columna por equipo y periodo."""
    resumen = estadisticas["resumen_comparativo"]
    filas = []
    for clave, etiqueta in METRICAS.items():
        fila = {"Métrica": etiqueta}
        for periodo, nombre_periodo in PERIODOS.items():
            for equipo, nombre_equipo in EQUIPOS.items():
                fila[f"{nombre_equipo} {nombre_periodo}"] = resumen[periodo][clave][equipo]
        filas.append(fila)
    return pd.DataFrame(filas)


def metrica_por_tiempo_df(estadisticas: dict, clave: str) -> pd.DataFrame:
    """Una métrica en formato largo (1T y 2T por equipo), lista para graficar."""
    resumen = estadisticas["resumen_comparativo"]
    return pd.DataFrame(
        [
            {
                "Tiempo": PERIODOS[periodo],
                "Equipo": nombre_equipo,
                "Valor": resumen[periodo][clave][equipo],
            }
            for periodo in ("primer_tiempo", "segundo_tiempo")
            for equipo, nombre_equipo in EQUIPOS.items()
        ]
    )


def goles_df(goles: list[dict]) -> pd.DataFrame:
    """Cronología de los 8 goles para la tabla de la página."""
    return pd.DataFrame(
        [
            {
                "Minuto": gol["minuto"],
                "Marcador": gol["marcador_momento"],
                "Equipo": gol["equipo_anotador"],
                "Anotador": gol["anotador"]["nombre"],
                "Asistente": gol["asistente"]["nombre"],
                "Jugada": gol["tipo_jugada"],
                "xG (estimado)": gol["xg"],
                "Distancia (m)": gol["distancia_porteria_m"],
            }
            for gol in goles
        ]
    )
