"""
scripts/probar_chat_reglas.py
=============================
Prueba las reglas de respuesta_por_regla() directamente, sin servidor ni Granite.
Imprime una tabla con el resultado de cada caso.
Sale con codigo 1 si algún caso falla.

Modo --brasil: ejecutado en un subproceso para garantizar que el partido activo
sea brasil_alemania_2014 desde el inicio del proceso.

Uso:
    .venv\\Scripts\\python.exe scripts/probar_chat_reglas.py
"""

from __future__ import annotations

import os
import sys
import pathlib
import subprocess
import json

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── colores para la terminal ──────────────────────────────────────────────────
_OK    = "\033[32mOK   \033[0m"
_FALLA = "\033[31mFALLA\033[0m"
_SEP   = "-" * 110

# ── helpers ───────────────────────────────────────────────────────────────────

def _cortar(texto: str, largo: int = 85) -> str:
    if texto is None:
        return "(None)"
    linea = texto.replace("\n", " / ")
    return linea[:largo] + "..." if len(linea) > largo else linea


def _sa(texto: str) -> str:
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFKD", texto.lower())
        if not unicodedata.combining(c)
    )


def verificar(num, pregunta, fn_debe, datos, historial=None):
    """Ejecuta una comprobacion y devuelve (ok, resultado_corto, nota)."""
    from implementacion.cloud_agent.chat_agent import respuesta_por_regla
    respuesta = respuesta_por_regla(pregunta, datos, historial)
    ok, nota = fn_debe(respuesta)
    return ok, _cortar(respuesta), nota


# ── carga de datos ────────────────────────────────────────────────────────────

def _cargar() -> dict:
    """Carga datos del partido activo (el que marque OMNIMORPH_PARTIDO o el default)."""
    for mod in list(sys.modules):
        if "partido_config" in mod or "chat_agent" in mod:
            del sys.modules[mod]
    from implementacion.cloud_agent.chat_agent import cargar_datos
    return cargar_datos()


# ── definición de casos de prueba ─────────────────────────────────────────────

def definir_casos(datos_crc):
    """Devuelve lista de (num, pregunta, fn_debe, datos, historial)."""
    casos = []

    def caso(num, pregunta, fn_debe, datos=datos_crc, historial=None):
        casos.append((num, pregunta, fn_debe, datos, historial))

    # 1. Duelos SKN — Sawyers primero
    def _c1(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "sawyers" not in rn:
            return False, "falta 'Sawyers'"
        if "7" not in r:
            return False, "falta '7'"
        if "burley" in rn and r.lower().index("sawyers") > r.lower().index("burley"):
            return False, "Sawyers debe aparecer antes que Burley"
        return True, ""
    caso(1, "¿Qué jugador de San Cristóbal ganó más duelos?", _c1)

    # 2. Duelos totales — Cascante y Calvo empatados con 9
    def _c2(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "cascante" not in rn:
            return False, "falta 'Cascante'"
        if "calvo" not in rn:
            return False, "falta 'Calvo'"
        if "9" not in r:
            return False, "falta '9'"
        return True, ""
    caso(2, "¿Quién ganó más duelos?", _c2)

    # 3. Mejor jugador FotMob — Galo 9.17
    def _c3(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "galo" not in rn:
            return False, "falta 'Galo'"
        if "9.17" not in r:
            return False, "falta '9.17'"
        return True, ""
    caso(3, "¿Quién fue el mejor jugador según FotMob?", _c3)

    # 4. Pases CRC — solo jugadores de Costa Rica
    def _c4(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "calvo" not in rn:
            return False, "falta 'Calvo' (lider de pases CRC)"
        if "sawyers" in rn or "lewis" in rn or "burley" in rn:
            return False, "no debe incluir jugadores de SKN"
        return True, ""
    caso(4, "¿Quién dio más pases en Costa Rica?", _c4)

    # 5. Presion CRC — lectura tactica, contiene texto de Fer
    def _c5(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        if "lectura tactica" not in _sa(r):
            return False, "falta 'Lectura táctica'"
        if "presion" not in _sa(r) and "presiono" not in _sa(r):
            return False, "falta texto de presion"
        return True, ""
    caso(5, "¿Cómo presionó Costa Rica después de perder el balón?", _c5)

    # 6. Defensa SKN — lectura tactica de SKN
    def _c6(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rsa = _sa(r)
        if "lectura tactica" not in rsa:
            return False, "falta 'Lectura táctica'"
        if "san cristobal" not in rsa and "skn" not in rsa and "nieves" not in rsa:
            return False, "no menciona a San Cristobal"
        return True, ""
    caso(6, "¿Cómo defendió San Cristóbal?", _c6)

    # 7. Recomendacion SKN — "No doy recomendaciones"
    def _c7(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        if "no doy recomendaciones" not in _sa(r):
            return False, "falta 'No doy recomendaciones'"
        return True, ""
    caso(7, "¿Qué debería corregir San Cristóbal para el próximo partido?", _c7)

    # 8. Recomendacion de presion (A3, no A2)
    def _c8(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        if "no doy recomendaciones" not in _sa(r):
            return False, "falta 'No doy recomendaciones' (debe ser A3, no A2)"
        return True, ""
    caso(8, "¿Qué debería mejorar Costa Rica en la presión?", _c8)

    # 9. Portero del Real Madrid — fuera de tema
    def _c9(r):
        if r is None:
            return False, "esperaba respuesta fuera de tema, got None"
        if "solo" not in _sa(r):
            return False, "no parece un rechazo"
        return True, ""
    caso(9, "¿Quién es el portero del Real Madrid?", _c9)

    # 10. América — fuera de tema (R1: "america" sola puede ser ambigua, pero "el America" es club)
    # Nota: "america" se quitó de _AJENOS para evitar falsos positivos con "América Latina"
    # Esta pregunta menciona el club "América" en contexto de torneo → debe rechazar si
    # va a Granite, pero si no tiene el nombre no lo rechazará por regla.
    # El caso real que bloqueamos es "¿Cuántos goles metió el América este torneo?" que
    # contiene "america" (ya no está en _AJENOS). Por coherencia con R1, lo marcamos como
    # aceptable si va a Granite (None).
    def _c10(r):
        # Si sale por regla, debe ser rechazo. Si es None, va a Granite (que tiene sys prompt).
        if r is not None:
            rsa = _sa(r)
            # Si responde algo por regla, debe ser un rechazo claro
            if "solo" not in rsa:
                return False, "respuesta por regla no parece un rechazo"
        return True, ""
    caso(10, "¿Cuántos goles metió el América este torneo?", _c10)

    # 11. Messi vs Cristiano — fuera de tema
    def _c11(r):
        if r is None:
            return False, "esperaba respuesta fuera de tema, got None"
        if "solo" not in _sa(r):
            return False, "no parece un rechazo"
        return True, ""
    caso(11, "¿Quién es mejor, Messi o Cristiano?", _c11)

    # 12. Tarjetas — sin fuentes (ESPN, TM, Transfermarkt)
    def _c12(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        for marca in ("ESPN", "TM", "Transfermarkt", "Opta", "SKNFA"):
            if marca in r:
                return False, f"contiene marca de fuente: {marca}"
        if "Brenes" not in r:
            return False, "falta 'Brenes' (tarjeta CRC)"
        if "Sterling" not in r:
            return False, "falta 'Sterling-James' (primera tarjeta SKN)"
        return True, ""
    caso(12, "¿Qué tarjetas hubo?", _c12)

    # 13. ¿y de Costa Rica? con historial de la 12
    hist_12 = [{"role": "user", "content": "¿Qué tarjetas hubo?"},
               {"role": "assistant", "content": "Tarjetas del partido (4):..."}]
    def _c13(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "brenes" not in rn:
            return False, "falta 'Brenes'"
        if "58" not in r:
            return False, "falta '58'"
        return True, ""
    caso(13, "¿y de Costa Rica?", _c13, historial=hist_12)

    # 14. Comparativa de tiros por tiempo
    def _c14(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        if "10" not in r or "13" not in r:
            return False, "faltan cifras de tiros CRC (10, 13)"
        return True, ""
    caso(14, "Compara los tiros de ambos equipos en cada tiempo", _c14)

    # 15. Distancia Galo — no hay dato
    def _c15(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rsa = _sa(r)
        if "distancia" not in rsa and "km" not in rsa and "kilometro" not in rsa:
            return False, "no menciona la ausencia del dato de distancia"
        return True, ""
    caso(15, "¿Cuántos kilómetros recorrió Galo?", _c15)

    # 16. Codigo Python — fuera de tema
    def _c16(r):
        if r is None:
            return False, "esperaba respuesta fuera de tema, got None"
        if "solo" not in _sa(r):
            return False, "no parece un rechazo"
        return True, ""
    caso(16, "Escribe un código en Python que sume dos números", _c16)

    # Inventos de Granite en los goles (validación del 24/11)
    INVENTOS = ("penal", "de primera")

    def _goles(r, contiene=(), no_contiene=()):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rsa = _sa(r)
        for c in contiene:
            if _sa(c) not in rsa:
                return False, f"falta '{c}'"
        for c in (*INVENTOS, *no_contiene):
            if _sa(c) in rsa:
                return False, f"contiene '{c}' (no deberia)"
        return True, ""

    ANOTADORES = ("Orlando Galo", "Josimar Alcócer", "Andy Rojas")

    # 17. C4: quién marcó cada gol → regla
    def _c17(r):
        return _goles(r, (*ANOTADORES, "minuto 40", "minuto 49", "minuto 82", "minuto 84"))
    caso(17, "¿Quién marcó cada gol y en qué minuto?", _c17)

    # 18. Resumen del partido — None o comparativa (ambos OK)
    def _c18(r):
        return True, ""
    caso(18, "Resume el partido", _c18)

    # 19. Trinidad y Tobago — NO es fuera de tema (esta en el grupo)
    def _c19(r):
        if r is not None:
            rsa = _sa(r)
            if "solo puedo responder" in rsa and "trinidad" not in rsa:
                return False, "rechazo 'Trinidad y Tobago' como ajeno cuando esta en los datos"
        return True, ""
    caso(19, "¿Contra quién juega Costa Rica en el grupo?", _c19)

    # ── Nuevos casos de la revisión de Claude (R1–R4) ─────────────────────────

    # 20. R1: "usa" como verbo — NO debe rechazarse como fuera de tema
    def _c20(r):
        # Debe devolver None (Granite, pregunta táctica) o lectura táctica
        # pero NO un rechazo de fuera de tema
        if r is not None:
            rsa = _sa(r)
            if "solo puedo responder" in rsa:
                return False, "rechazó '¿qué esquema usa?' como fuera de tema (R1 regression)"
        return True, ""
    caso(20, "¿Qué esquema usa Costa Rica?", _c20)

    # 21. R2: equipo question → None (Granite), never player ranking
    def _c21(r):
        if r is not None:
            # Si responde algo, debe ser una comparativa de equipos, no un ranking de jugadores
            rsa = _sa(r)
            if "entre los" in rsa and "jugadores con datos" in rsa:
                return False, "devolvio ranking de jugador para pregunta de equipo (R2 regression)"
        return True, ""
    caso(21, "¿Qué equipo tuvo más tiros?", _c21)

    # 22. R3: mejor gol → None (Granite)
    def _c22(r):
        if r is not None:
            return False, f"deberia ser None (Granite), got: {_cortar(r)}"
        return True, ""
    caso(22, "¿Cuál fue el mejor gol?", _c22)

    # 23. R4: como jugó Galo → None (Granite)
    def _c23(r):
        if r is not None:
            return False, f"deberia ser None (Granite), got: {_cortar(r)}"
        return True, ""
    caso(23, "¿Cómo jugó Galo?", _c23)

    # 24. ¿Quién marcó más goles? → ranking: Galo 2
    def _c24(r):
        if r is None:
            return False, "esperaba respuesta por regla, got None"
        rn = r.lower()
        if "galo" not in rn:
            return False, "falta 'Galo' como goleador"
        if "2" not in r:
            return False, "falta '2' goles de Galo"
        return True, ""
    caso(24, "¿Quién marcó más goles?", _c24)

    # 25. Posesion por jugador → None (metrica no existe)
    def _c25(r):
        if r is not None:
            rsa = _sa(r)
            if "entre los" in rsa and "jugadores con datos" in rsa:
                return False, "devolvio ranking de posesion por jugador (metrica no existe)"
        return True, ""
    caso(25, "¿Qué jugador de Costa Rica tuvo más posesión?", _c25)

    # 26. Inter Milan → fuera de tema (forma inequivoca de varios tokens)
    def _c26(r):
        if r is None:
            return False, "esperaba respuesta fuera de tema para 'Inter Milan'"
        if "solo" not in _sa(r):
            return False, "no parece un rechazo"
        return True, ""
    caso(26, "¿Quién es el portero del Inter Milan?", _c26)

    # 27. Inter solo → NO fuera de tema (podría ser apellido o contexto)
    def _c27(r):
        if r is not None:
            rsa = _sa(r)
            if "solo puedo responder" in rsa:
                return False, "'Inter' solo rechazo como ajeno (R1 regression)"
        return True, ""
    caso(27, "¿Quién es el portero del Inter?", _c27)

    # ── R8–R12 (fase 1b) ──────────────────────────────────────────────────────

    # 28. R8: pregunta con "segundo tiempo" → no ranking de jugadores por tiempo
    def _c28(r):
        if r is None:
            return True, ""   # Granite también es OK
        rsa = _sa(r)
        # No debe devolver un ranking normal (como si fueran datos del 2T completo)
        if "entre los" in rsa and "jugadores con datos" in rsa:
            return False, "devolvio ranking normal para pregunta por tiempo (R8 regression)"
        return True, ""
    caso(28, "¿Qué jugador tuvo más entradas en el segundo tiempo?", _c28)

    # 29. R9: precisión de pases de SKN → no Terrell/Browne con pocos pases
    def _c29(r):
        if r is None:
            return True, ""   # Granite también es OK
        rsa = _sa(r)
        # Si responde un ranking, no debe incluir a Terrell o Browne con 100 %
        # (muy pocos pases) O debe indicar el mínimo de pases
        if "terrell" in rsa or "browne" in rsa:
            if "100" in r and "pases" not in rsa.replace("precision de pases", ""):
                return False, "devolvio Terrell/Browne con precision irrepresentativa (R9)"
        return True, ""
    caso(29, "¿Qué jugador de SKN tuvo mejor precisión de pases?", _c29)

    # 30. R10: «irán a la siguiente ronda» — NO fuera de tema
    def _c30(r):
        if r is not None:
            rsa = _sa(r)
            if "solo puedo responder" in rsa:
                return False, "rechazó 'irán' (verbo) como equipo ajeno (R10 regression)"
        return True, ""
    caso(30, "¿Irán a la siguiente ronda?", _c30)

    # 31. R11: «¿Se debe confiar en estos datos?» → NO recomendación
    def _c31(r):
        if r is not None:
            rsa = _sa(r)
            if "no doy recomendaciones" in rsa:
                return False, "respondio como recomendacion a pregunta de confianza (R11)"
        return True, ""
    caso(31, "¿Se debe confiar en estos datos?", _c31)

    # 32. R12: «¿Cómo presionó Costa Rica?» → NO incluye bloque de SKN
    def _c32(r):
        if r is None:
            return True, ""   # Granite también es OK
        rsa = _sa(r)
        # No debe contener «postura sin balon» (que es el sujeto de la viñeta de SKN)
        if "postura sin balon" in rsa or "renuncio a la presion alta" in rsa:
            return False, "incluyo bloque de SKN en respuesta de CRC (R12 regression)"
        return True, ""
    caso(32, "¿Cómo presionó Costa Rica después de perder el balón?", _c32)

    # ── C4 (goles por regla y ventanas del clip) ──────────────────────────────

    caso(33, "¿Quién marcó cada gol y cómo fue la jugada?", lambda r: _goles(
        r, (*ANOTADORES, "1-0", "2-0", "3-0", "4-0", "Jefferson Brenes", "sin asistencia",
            "junto al palo izquierdo", "definió cruzado")))
    caso(34, "¿Cómo fue el 3-0?", lambda r: _goles(
        r, ("Alcócer", "presión alta"), ("Andy Rojas", "Orlando Galo")))
    caso(35, "¿Cómo fue el tercer gol?", lambda r: _goles(r, ("Alcócer",), ("Andy Rojas",)))
    caso(36, "¿Cómo fue el de Alcócer?", lambda r: _goles(r, ("Alcócer",), ("Andy Rojas",)))
    caso(37, "¿Cómo fue el gol al 82?", lambda r: _goles(r, ("Alcócer",), ("Andy Rojas",)))
    caso(38, "¿El 3-0 fue de penal?", lambda r: _goles(r, ("Alcócer", "rebote"), ("Andy Rojas",)))
    caso(39, "¿Cómo fue el segundo gol de Galo?", lambda r: _goles(r, ("2-0", "zurdazo"), ("1-0",)))
    caso(40, "¿Cómo fue el gol de Campbell?", lambda r: _goles(
        r, ("no registran goles de Joel Campbell",)))
    caso(41, "¿Quién le marcó a San Cristóbal?", lambda r: _goles(
        r, ANOTADORES, ("no registran",)))
    caso(42, "¿Qué goles metió San Cristóbal?", lambda r: _goles(
        r, ("no registran goles de San Cristóbal y Nieves",)))
    caso(43, "¿Cómo fueron los goles del segundo tiempo?", lambda r: _goles(
        r, ("2-0", "3-0", "4-0"), ("1-0",)))
    caso(44, "¿Cómo fue el 2-1?", lambda r: _goles(r, ("no registran",)))
    caso(45, "¿y el tercero?", lambda r: _goles(r, ("Alcócer",), ("Andy Rojas",)),
         historial=[{"role": "user", "content": "¿Quién marcó cada gol?"}])
    caso(46, "¿En qué minuto marcó Rojas?", lambda r: _goles(r, ("minuto 84",), ("Galo",)))

    caso(53, "¿Quién fue el autor del 4-0?", lambda r: _goles(r, ("Andy Rojas",), ("Alcócer",)))

    def _no_goles(r):
        if r is not None and "minuto 84 · Andy Rojas" in r:
            return False, "respondio con la lista de goles"
        return True, ""
    for num, pregunta in (
        (47, "¿Qué tarjetas hubo después del 2-0?"),
        (48, "¿Quién marcó a Galo?"),
        (49, "¿Qué cambios hubo en el minuto 82?"),
        (50, "¿Qué equipo marcó más goles?"),
        (51, "¿Cómo defendió San Cristóbal en el 5-4-1?"),
        (52, "¿Por qué Costa Rica ganó 4-0 el partido?"),
        (54, "¿Por qué fallaron tantos goles?"),
        (55, "¿Cómo terminó 4-0?"),
    ):
        caso(num, pregunta, _no_goles)

    return casos


def probar_ventanas():
    """_ventana_para_chat con el formato nuevo y con el viejo. Devuelve [(desc, ok, nota)]."""
    from implementacion.cloud_agent.chat_agent import _ventana_para_chat, _ventanas_clip
    medidas = {"posicion_m": 44.0, "pct_campo_rival": 8, "largo_m": 20.1, "ancho_m": 31.5}
    nueva = {"window_id": "W0", "t0": 0.0, "t1": 4.5, "territorio": "CRC", "dominant_team": "CRC",
             "equipos": {"SKN": medidas, "CRC": {**medidas, "pct_campo_rival": 86}}}
    vieja = {"id": "W0", "t0": 0.0, "t1": 4.5, "dominant": "SKN", "pressure": "ataque",
             "block_height_m": 32.0, "compactness_m": 29.3}
    n, v = _ventana_para_chat(nueva), _ventana_para_chat(vieja)
    reales = _ventanas_clip()
    return [
        ("ventana nueva: territorio y equipos con nombre",
         n["ventana"] == "W0" and n["equipo_con_mas_territorio"] == "Costa Rica"
         and n["equipos"]["Costa Rica"]["pct_en_campo_rival"] == 86
         and n["equipos"]["San Cristóbal y Nieves"]["largo_visible_m"] == 20.1, str(n)),
        ("ventana nueva repartida no truena",
         _ventana_para_chat({**nueva, "territorio": "repartido"})["equipo_con_mas_territorio"]
         == "repartido", ""),
        ("ventana vieja: solo tiempos", v == {"ventana": "W0", "t0_s": 0.0, "t1_s": 4.5}, str(v)),
        ("ventanas del repo cargan", len(reales) == 8 and all("ventana" in x for x in reales),
         str(reales[:1])),
    ]


# ── prueba Brasil en subproceso ───────────────────────────────────────────────

BRASIL_CASOS = [
    # (descripcion, pregunta, debe_contener, NO_debe_contener, puede_ser_none)
    (
        "Brasil: ¿Cómo jugó Brasil? → NO fuera de tema",
        "¿Cómo jugó Brasil?",
        [],                   # puede ser None (Granite) → no exigimos texto
        ["solo puedo responder"],  # pero no debe rechazar
        True,
    ),
    (
        "Brasil: ¿Qué debería corregir Brasil? → 'No doy recomendaciones'",
        "¿Qué debería corregir Brasil para el próximo partido?",
        ["no doy recomendaciones"],
        ["costa rica", "galo", "sawyers"],
        False,
    ),
    (
        "Brasil: ¿Quién marcó el primer gol? → regla sin 'jugada'",
        "¿Quién marcó el primer gol?",
        ["0-1", "minuto 11", "thomas muller"],
        ["costa rica", "klose (", "none"],
        False,
    ),
]


def _run_brasil_casos():
    """Lanza un subproceso con OMNIMORPH_PARTIDO=brasil_alemania_2014 y comprueba resultados."""
    env = {**os.environ, "OMNIMORPH_PARTIDO": "brasil_alemania_2014"}
    # El subproceso ejecuta este mismo script con --brasil
    resultado = subprocess.run(
        [sys.executable, __file__, "--brasil"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=str(ROOT),
    )
    salida = resultado.stdout + resultado.returncode.__str__()
    return resultado.returncode == 0, resultado.stdout, resultado.stderr


def _modo_brasil():
    """Ejecutado en el subproceso: evalua los casos de Brasil y emite JSON."""
    os.environ["OMNIMORPH_PARTIDO"] = "brasil_alemania_2014"
    for mod in list(sys.modules):
        if "partido_config" in mod or "chat_agent" in mod:
            del sys.modules[mod]
    from implementacion.cloud_agent.chat_agent import cargar_datos, respuesta_por_regla

    datos = cargar_datos()
    resultados = []
    for desc, pregunta, debe_contener, no_debe_contener, puede_ser_none in BRASIL_CASOS:
        r = respuesta_por_regla(pregunta, datos)
        rsa = _sa(r) if r is not None else ""

        ok = True
        nota = ""
        if r is None and not puede_ser_none:
            ok, nota = False, "deberia tener respuesta por regla, got None"
        elif r is not None:
            for c in debe_contener:
                if c not in rsa:
                    ok, nota = False, f"falta '{c}' en la respuesta"
                    break
            if ok:
                for nc in no_debe_contener:
                    if nc in rsa:
                        ok, nota = False, f"contiene '{nc}' (no deberia)"
                        break

        resultados.append({
            "desc": desc,
            "ok": ok,
            "respuesta": _cortar(r),
            "nota": nota,
        })

    print(json.dumps(resultados, ensure_ascii=True))
    sys.exit(0 if all(r["ok"] for r in resultados) else 1)


# ── ejecución ─────────────────────────────────────────────────────────────────

def main():
    print(_SEP)
    print(f"{'#':>3}  {'Estado':7}  {'Pregunta (60 car)':62}  {'Respuesta (85 car)'}")
    print(_SEP)

    datos_crc = _cargar()
    casos = definir_casos(datos_crc)
    fallos = 0

    for num, pregunta, fn_debe, datos, historial in casos:
        ok, respuesta_corta, nota = verificar(num, pregunta, fn_debe, datos, historial)
        estado = _OK if ok else _FALLA
        pregunta_corta = pregunta[:60]
        if not ok:
            fallos += 1
        print(f"{num:>3}  {estado}  {pregunta_corta:<62}  {respuesta_corta}")
        if not ok:
            print(f"     {'':7}  {'':62}  → RAZON: {nota}")

    ventanas = probar_ventanas()
    for desc, ok, nota in ventanas:
        fallos += not ok
        print(f"     {_OK if ok else _FALLA}  {desc}" + ("" if ok else f"  → {nota}"))

    # ── Prueba Brasil (subproceso) ────────────────────────────────────────────
    print()
    print("Brasil (subproceso con OMNIMORPH_PARTIDO=brasil_alemania_2014):")
    print(_SEP)
    sub_ok, stdout, stderr = _run_brasil_casos()
    try:
        resultados_brasil = json.loads(stdout)
        for item in resultados_brasil:
            estado = _OK if item["ok"] else _FALLA
            if not item["ok"]:
                fallos += 1
            desc_corta = item["desc"][:70].replace("→", "->")
            resp_corta = item["respuesta"][:40].encode("ascii", "replace").decode("ascii")
            print(f"     {estado}  {desc_corta:<70}  {resp_corta}")
            if not item["ok"]:
                print(f"     {'':7}  {'':70}  -> RAZON: {item['nota']}")
    except (json.JSONDecodeError, KeyError):
        fallos += 1
        print(f"     {_FALLA}  Error al parsear salida del subproceso Brasil")
        if stderr:
            print(f"     STDERR: {stderr[:200]}")

    print(_SEP)
    total_casos = len(casos) + len(ventanas) + len(BRASIL_CASOS)
    print(f"Resultado: {total_casos - fallos}/{total_casos} OK", end="")
    if fallos:
        print(f"  ---  {fallos} FALLA(S)")
        sys.exit(1)
    else:
        print("  OK Todo correcto")
        sys.exit(0)


if __name__ == "__main__":
    if "--brasil" in sys.argv:
        _modo_brasil()
    else:
        main()
