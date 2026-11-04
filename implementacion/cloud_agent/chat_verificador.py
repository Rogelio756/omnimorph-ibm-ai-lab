"""
implementacion/cloud_agent/chat_verificador.py
==============================================
Verifica a quién atribuye Granite cada cifra de una respuesta.

Comprobar que una cifra exista en los datos no basta: el modelo puede decir que
Alemania hizo 16 tiros en el 2T, y 16 existe, pero es de Brasil. Este módulo busca
en cada segmento de frase el equipo o jugador, la métrica y el tiempo de cada
cifra, y la compara con los datos. Es una comprobación por reglas, sin LLM: puede
equivocarse con redacciones complejas y solo evalúa las cifras en las que reconoce
una métrica, así que un hallazgo pide revisar y su ausencia no demuestra que la
respuesta sea correcta.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

PERIODOS = ("1T", "2T", "Total")
TOLERANCIA = 0.051

# Términos (sin acentos) -> métrica. Los más largos se buscan primero.
TERMINOS_METRICA = {
    "goles recibidos": "goles_recibidos",
    "tiros a puerta": "tiros_a_puerta",
    "tiros a porteria": "tiros_a_puerta",
    "disparos a puerta": "tiros_a_puerta",
    "a puerta": "tiros_a_puerta",
    "tiros dentro del area": "tiros_dentro_area",
    "tiros fuera del area": "tiros_fuera_area",
    "fueras de juego": "fueras_de_juego",
    "fuera de juego": "fueras_de_juego",
    "posesion": "posesion_pct",
    "precision en pases": "precision_pases_pct",
    "precision de pases": "precision_pases_pct",
    "precision": "precision_pases_pct",
    "tiros": "tiros_totales",
    "disparos": "tiros_totales",
    "disparo": "tiros_totales",
    "remates": "tiros_totales",
    "xg": "xg_esperado",
    "valor estimado de gol": "xg_esperado",
    "goles esperados": "xg_esperado",
    "corners": "corners",
    "faltas": "faltas_cometidas",
    "atajadas": "atajadas",
    "recuperaciones": "recuperaciones",
    "balones recuperados": "recuperaciones",
    "pases": "pases",
    "asistencias": "asistencias",
    "asistencia": "asistencias",
    "goles": "goles",
    "gol": "goles",
    "kilometros": "distancia",
    "km": "distancia",
}
# Solo existen para los jugadores destacados: si falta, es una cifra sin respaldo
METRICAS_INDIVIDUALES = {"distancia", "pases", "tiros_a_puerta", "recuperaciones"}

ETIQUETAS_METRICA = {
    "posesion_pct": "posesión (%)",
    "tiros_totales": "tiros totales",
    "tiros_a_puerta": "tiros a puerta",
    "tiros_dentro_area": "tiros dentro del área",
    "tiros_fuera_area": "tiros fuera del área",
    "xg_esperado": "xG estimado",
    "precision_pases_pct": "precisión de pases (%)",
    "faltas_cometidas": "faltas cometidas",
    "fueras_de_juego": "fueras de juego",
    "goles_recibidos": "goles recibidos",
    "distancia": "distancia (km)",
}

TERMINOS_PERIODO = {
    "1t": "1T", "1er tiempo": "1T", "primer tiempo": "1T", "primera parte": "1T",
    "2t": "2T", "2do tiempo": "2T", "segundo tiempo": "2T", "segunda parte": "2T",
    "en el primero": "1T", "en el segundo": "2T",
    "total": "Total", "todo el partido": "Total", "partido completo": "Total",
}
NUMEROS_EN_LETRAS = {
    "dos": "2", "tres": "3", "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
}


def sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def _alternativas(terminos) -> str:
    return "|".join(re.escape(t) for t in sorted(terminos, key=len, reverse=True))


# (?!/) evita tomar km/h como distancia
RE_METRICA = re.compile(rf"\b(?:{_alternativas(TERMINOS_METRICA)})\b(?!/)")
RE_PERIODO = re.compile(rf"\b(?:{_alternativas(TERMINOS_PERIODO)})\b")
RE_NUMERO = re.compile(r"(?<![\w.,])\d+(?:[.,]\d+)?(?![\w])")
RE_MINUTOS = re.compile(
    r"\bminutos?\s+\d+(?:\s*(?:,|y)\s*\d+)*|\b\d+\s+minutos?\b|\b\d+'|\ben el \d+(?![\w.,%])"
)
RE_MARCADOR = re.compile(r"\b(\d+)\s*-\s*(\d+)\b")
RE_SEGMENTO = re.compile(r"(,\s+|\s+y\s+|\s+vs\.?\s+|\s+contra\s+|\s+frente a\s+)")
# Tras estos separadores, una cifra sin equipo explícito es del rival: no se puede atribuir
RE_RIVAL = re.compile(r"vs|contra|frente")
RE_DIFERENCIA = re.compile(
    r"\b(?:mas|menos)\b|\bde\s+[\d.,]+%?\s+a\b|\bdel\s+[\d.,]+%?\s+al\b|→"
)


def construir_hechos(
    estadisticas: dict,
    goles: list[dict],
    equipos: dict,
    metricas: dict,
    nombres_equipo: dict,
) -> dict:
    """Prepara los valores contra los que se comparan las respuestas."""
    resumen = estadisticas["resumen_comparativo"]
    periodos = zip(("primer_tiempo", "segundo_tiempo", "tiempo_completo"), PERIODOS)
    periodos = list(periodos)
    por_equipo: dict = {}

    for clave_equipo, nombre in nombres_equipo.items():
        valores: dict = {}
        for clave in metricas:
            destino = "atajadas" if clave == "atajadas_portero" else clave
            valores[destino] = {
                etiqueta: float(resumen[periodo][clave][clave_equipo])
                for periodo, etiqueta in periodos
            }
        # 182/228 -> se aceptan completados e intentados
        valores["pases"] = {
            etiqueta: [
                float(x)
                for x in resumen[periodo]["pases_completados_intentados"][clave_equipo].split("/")
            ]
            for periodo, etiqueta in periodos
        }
        propios = [g for g in goles if g["equipo_anotador"] == nombre]
        en_1t = sum(1 for g in propios if g["minuto"] <= 45)
        valores["goles"] = {
            "1T": float(en_1t),
            "2T": float(len(propios) - en_1t),
            "Total": float(len(propios)),
        }
        por_equipo[sin_acentos(nombre)] = {"nombre": nombre, "valores": valores}

    por_jugador: dict = {}
    for equipo in equipos.values():
        for jugador in equipo["plantilla"].values():
            por_jugador[jugador["nombre"]] = {}
    for gol in goles:
        nombre = gol["anotador"]["nombre"]
        por_jugador[nombre]["goles"] = por_jugador[nombre].get("goles", 0.0) + 1.0
        asistente = gol["asistente"]["nombre"]
        por_jugador[asistente]["asistencias"] = por_jugador[asistente].get("asistencias", 0.0) + 1.0
    for fila in estadisticas["rendimiento_individual_destacado"]:
        valores = por_jugador[fila["jugador"]]
        for origen, destino in (
            ("distancia_recorrida_km", "distancia"),
            ("tiros_a_puerta", "tiros_a_puerta"),
            ("precision_pases_pct", "precision_pases_pct"),
            ("recuperaciones", "recuperaciones"),
            ("atajadas", "atajadas"),
            ("goles_recibidos", "goles_recibidos"),
        ):
            if origen in fila:
                valores[destino] = float(fila[origen])
        pases = [float(fila[k]) for k in ("pases_completados", "pases_totales") if k in fila]
        if pases:
            valores["pases"] = pases

    # Alias: nombre completo y, si no se repite, su última palabra
    ultimas = [sin_acentos(n).split()[-1] for n in por_jugador]
    alias = {}
    for nombre in por_jugador:
        normalizado = sin_acentos(nombre)
        alias[normalizado] = nombre
        ultima = normalizado.split()[-1]
        if ultimas.count(ultima) == 1 and len(ultima) > 2:
            alias[ultima] = nombre

    marcadores = {g["marcador_momento"] for g in goles} | {
        resumen[periodo]["marcador"] for periodo, _ in periodos
    }
    return {
        "equipos": por_equipo,
        "jugadores": por_jugador,
        "alias_jugadores": alias,
        "marcadores": marcadores,
    }


def _cercano(numero: re.Match, encontrados: list[tuple[int, int, str]]) -> Optional[str]:
    """Término más cercano a la cifra, midiendo entre sus bordes."""
    if not encontrados:
        return None

    def distancia(termino: tuple[int, int, str]) -> int:
        inicio, fin, _ = termino
        return max(inicio - numero.end(), numero.start() - fin, 0)

    return min(encontrados, key=distancia)[2]


def _etiqueta(metrica: str) -> str:
    return ETIQUETAS_METRICA.get(metrica, metrica)


def _coincide(cifra: float, esperados: list[float]) -> bool:
    return any(abs(cifra - valor) <= TOLERANCIA for valor in esperados)


def _plano(valor) -> list[float]:
    return list(valor) if isinstance(valor, list) else [valor]


def _revisar_equipo(cifra, equipo, metrica, periodo) -> Optional[str]:
    por_periodo = equipo["valores"].get(metrica)
    if por_periodo is None:
        return None
    if periodo:
        esperados = _plano(por_periodo[periodo])
        descripcion = f"{periodo} {'/'.join(f'{v:g}' for v in esperados)}"
    else:
        esperados = [v for p in PERIODOS for v in _plano(por_periodo[p])]
        # Se admite la diferencia entre tiempos ("6 tiros menos")
        primero, segundo = _plano(por_periodo["1T"])[0], _plano(por_periodo["2T"])[0]
        esperados.append(abs(primero - segundo))
        descripcion = ", ".join(
            f"{p} {'/'.join(f'{v:g}' for v in _plano(por_periodo[p]))}" for p in PERIODOS
        )
    if _coincide(cifra, esperados):
        return None
    return f"{equipo['nombre']}: {cifra:g} en {_etiqueta(metrica)}; los datos dicen {descripcion}"


def _revisar_jugador(cifra, nombre, metrica, hechos) -> Optional[str]:
    valor = hechos["jugadores"][nombre].get(metrica)
    if valor is None:
        if metrica in METRICAS_INDIVIDUALES:
            return f"{nombre}: {cifra:g} no tiene respaldo, no hay datos de {_etiqueta(metrica)}"
        if metrica not in ("goles", "asistencias"):
            return None
        valor = 0.0  # La cronología registra todos los goles y asistencias
    if _coincide(cifra, _plano(valor)):
        return None
    esperado = "/".join(f"{v:g}" for v in _plano(valor))
    return f"{nombre}: {cifra:g} en {_etiqueta(metrica)}; los datos dicen {esperado}"


def _preparar_frase(frase: str, hechos: dict) -> str:
    """Quita lo que no es una estadística: minutos y marcadores conocidos."""
    frase = RE_MINUTOS.sub(" ", frase)

    def quitar_marcador(coincidencia: re.Match) -> str:
        a, b = coincidencia.group(1), coincidencia.group(2)
        conocido = {f"{a}-{b}", f"{b}-{a}"} & hechos["marcadores"]
        return " " if conocido else f"{a} {b}"

    frase = RE_MARCADOR.sub(quitar_marcador, frase)
    for palabra, digito in NUMEROS_EN_LETRAS.items():
        frase = re.sub(rf"\b{palabra}\b", digito, frase)
    return frase


def _periodo_de(numero: re.Match, periodos: list, segmento: str) -> Optional[str]:
    """
    Tiempo al que pertenece la cifra. Solo cuenta si no hay otra cifra ni un paréntesis
    entre ambos: en "18 (1T 2, 2T 16)" el 18 es el total, no el dato del 1T.
    """
    validos = []
    for inicio, fin, periodo in periodos:
        tramo = segmento[fin:numero.start()] if fin <= numero.start() else segmento[numero.end():inicio]
        if not re.search(r"[()]", tramo) and not RE_NUMERO.search(tramo):
            validos.append((inicio, fin, periodo))
    return _cercano(numero, validos)


def verificar_atribucion(respuesta: str, hechos: dict) -> list[str]:
    """
    Devuelve una descripción por cada cifra que no coincide con los datos.

    Cada oración se divide en segmentos. Una cifra se compara con el equipo o
    jugador, la métrica y el tiempo de su segmento. La métrica y la entidad que falten
    se heredan del segmento anterior, como en "53% en el 1T y 44% en el 2T", y la
    siguiente oración hereda el sujeto, es decir, la entidad con la que abre la oración.
    """
    patron_entidad = re.compile(
        rf"\b(?:{_alternativas([*hechos['equipos'], *hechos['alias_jugadores']])})\b"
    )
    hallazgos: list[str] = []
    sujeto = None

    for oracion in re.split(r"\n+|\.\s+|;\s+", sin_acentos(respuesta)):
        entidad_previa = sujeto
        metrica_previa = None
        trozos = RE_SEGMENTO.split(_preparar_frase(oracion, hechos))
        separadores = ["", *trozos[1::2]]
        for indice, segmento in enumerate(trozos[0::2]):
            entidades = [(m.start(), m.end(), m.group()) for m in patron_entidad.finditer(segmento)]
            metricas = [
                (m.start(), m.end(), TERMINOS_METRICA[m.group()])
                for m in RE_METRICA.finditer(segmento)
            ]
            periodos = [
                (m.start(), m.end(), TERMINOS_PERIODO[m.group()])
                for m in RE_PERIODO.finditer(segmento)
            ]
            # Evoluciones y diferencias no son el valor de un solo tiempo
            sin_periodo = RE_DIFERENCIA.search(segmento) is not None
            cifra_del_rival = not entidades and RE_RIVAL.search(separadores[indice])

            for numero in [] if cifra_del_rival else RE_NUMERO.finditer(segmento):
                metrica = _cercano(numero, metricas) or metrica_previa
                # En "Toni Kroos (Alemania) con 2 asistencias" la cifra es del jugador
                jugadores = [e for e in entidades if e[2] not in hechos["equipos"]]
                entidad = _cercano(numero, jugadores or entidades) or entidad_previa
                if metrica is None or entidad is None:
                    continue
                cifra = float(numero.group().replace(",", "."))
                if metrica == "pases" and segmento[numero.end():].startswith("%"):
                    metrica = "precision_pases_pct"
                if entidad in hechos["equipos"]:
                    periodo = None if sin_periodo else _periodo_de(numero, periodos, segmento)
                    hallazgo = _revisar_equipo(cifra, hechos["equipos"][entidad], metrica, periodo)
                else:
                    hallazgo = _revisar_jugador(
                        cifra, hechos["alias_jugadores"][entidad], metrica, hechos
                    )
                if hallazgo and hallazgo not in hallazgos:
                    hallazgos.append(hallazgo)

            if entidades:
                entidad_previa = entidades[-1][2]
                # Solo es sujeto si abre la oración (tras una viñeta): en "Destacaron
                # Kroos y Müller", Kroos no es el sujeto de la oración siguiente
                if indice == 0 and entidades[0][0] <= 2:
                    sujeto = entidades[0][2]
            if metricas:
                metrica_previa = metricas[-1][2]
    return hallazgos
