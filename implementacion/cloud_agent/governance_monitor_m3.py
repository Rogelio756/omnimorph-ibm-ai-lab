"""
implementacion/cloud_agent/governance_monitor_m3.py
====================================================
MONITOR M3 — Auditoría LLM y watsonx.governance

Verifica por cada ventana táctica:
  ✓ El modelo usado es un IBM Granite autorizado (bloquea cualquier otro).
    Las ventanas sin LLM (modo offline) se registran como tales.
  ✓ La salida JSON tiene los campos requeridos: {window_id, t0, t1, analisis_tactico, narracion_es}
  ✓ narracion_es tiene <= 18 palabras (la voz dura ~3.9 s).
  ✓ Palabras prohibidas (sin acentos ni mayúsculas, por raíz y con límite de palabra):
    posesion, presi(on|ona*), domin*, control*, luch*, disput*.
  ✓ Coherencia de territorio por oración:
    - Si territorio es un equipo, falla si dice que el otro está adelantado, ocupa más
      campo rival o tiene más territorio.
    - Si territorio es "repartido", falla si lo afirma de cualquiera.
    - Si territorio es un equipo, la narración debe nombrarlo y no puede decir que está repartido.
    - «mitad rival / campo rival» exige que ese equipo tenga >= 50 % en campo rival;
      «su mitad / su campo» exige <= 50 %.
  ✓ Redacción de la métrica: el % en campo rival no es «% del territorio» ni «un espacio de N%»,
    y «en mitad» sin «su» o «la» no se acepta.
  ✓ Verificación de números por oración:
    - Todo número del texto debe estar en los datos de ESA ventana (entero o con un decimal)
      y pertenecer al equipo que se nombra en la oración.

Registra cada intento en governance_audit.jsonl.
finalize_report() juzga el ÚLTIMO intento de cada ventana y cuenta los anteriores aparte (retries).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import statistics
import unicodedata
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
REQUIRED_MODEL = "ibm/granite-4-h-small"
AUTHORIZED_MODELS = {"ibm/granite-4-h-small", "ibm/granite-3-8b-instruct"}
MAX_NARRATION_WORDS = 18
REQUIRED_FIELDS = {"window_id", "t0", "t1", "analisis_tactico", "narracion_es"}

CLEAN_DIR = pathlib.Path("data/clean")
AUDIT_LOG = CLEAN_DIR / "governance_audit.jsonl"
REPORT_PATH = CLEAN_DIR / "monitor_m3.json"

# Costo estimado watsonx.ai en Resource Units (aproximación)
RU_PER_TOKEN_IN = 0.0001
RU_PER_TOKEN_OUT = 0.0003

# Palabras prohibidas (sobre texto en minúsculas y sin acentos):
# posesion(es), presion/presiona* (pero NO presencia ni presidente),
# domin*, control*, luch*, disput*, busc*, intent*, quier*/quer*, pretend*,
# atac*/ataqu*, gol*, marcador*, velocidad*, repli*/replieg*, retroced*/retroces*,
# empuj*, arrincon*, acorral*, encierr*/encerr*, avanz*/avanc*.
RE_PALABRAS_PROHIBIDAS = re.compile(
    r"\b(?:"
    r"posesion(?:es)?|"
    r"presion\w*|"
    r"presiona\w*|"
    r"presione\w*|"
    r"presiono\w*|"
    r"domin\w*|"
    r"control\w*|"
    r"luch\w*|"
    r"disput\w*|"
    r"busc\w*|"
    r"busqu\w*|"
    r"intent\w*|"
    r"quier\w*|"
    r"quer\w*|"
    r"pretend\w*|"
    r"atac\w*|"
    r"ataqu\w*|"
    r"gol\w*|"
    r"marcador\w*|"
    r"velocidad\w*|"
    r"repli\w*|"
    r"replieg\w*|"
    r"retroced\w*|"
    r"retroces\w*|"
    r"empuj\w*|"
    r"arrincon\w*|"
    r"acorral\w*|"
    r"encierr\w*|"
    r"encerr\w*|"
    r"avanz\w*|"
    r"avanc\w*|"
    r"retras\w*|"
    r"sube\s+(?:sus\s+)?lineas|"
    r"suben\s+(?:sus\s+)?lineas"
    r")\b"
)

# Afirmaciones de ubicación por mitades (sobre texto sin acentos)
RE_EN_MITAD_RIVAL = re.compile(
    r"\b(?:mitad|campo|terreno|zona|cancha)\s+(?:rival|contrari[oa]|ajen[oa]|del\s+rival|de\s+su\s+(?:rival|adversario))\b"
)
RE_EN_SU_MITAD = re.compile(
    r"\b(?:su\s+(?:propia\s+)?(?:mitad|campo|terreno|zona)|(?:mitad|campo|terreno)\s+propi[oa]|propia\s+mitad)\b"
)
# Un porcentaje justo antes ("con 6% en campo rival") es una cifra, no una afirmación de ubicación
RE_PCT_ANTES = re.compile(r"(?:%|por\s+ciento)\s+(?:\w+\s+){0,4}$")
# Redacción que cambia el significado de la métrica (sobre texto sin acentos)
RE_REDACCION_METRICA = re.compile(
    r"\d+(?:[.,]\d+)?\s*%\s+(?:del?\s+)?(?:su\s+)?territorio\b|"
    r"\bespacio\s+de\s+(?:un\s+)?\d+(?:[.,]\d+)?\s*%|"
    r"\ben\s+mitad\b(?!\s+de\b)"
)
# Decir que el territorio está repartido cuando pertenece a un equipo
RE_DICE_REPARTIDO = re.compile(
    r"\b(?:repartid[oa]s?|parej[oa]s?|equilibrad[oa]s?|igualad[oa]s?|ninguno\s+de\s+los\s+dos)\b"
)

# Números escritos con letras (3..10, 11..90, 100..900).
# No cuentan "uno", "un", "una", "dos", "ambos", "ambas".
RE_NUMEROS_EN_LETRAS = re.compile(
    r"\b(?:"
    r"tres|cuatro|cinco|seis|siete|ocho|nueve|diez|"
    r"once|doce|trece|catorce|quince|dieciseis|diecisiete|dieciocho|diecinueve|"
    r"veinte|veinti\w+|treinta|cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|"
    r"cien|ciento|doscientos|trescientos|cuatrocientos|quinientos|seiscientos|setecientos|ochocientos|novecientos"
    r")\b"
)

# Afirmaciones de estar adelantado, en campo rival o con más territorio (sobre texto sin acentos):
RE_AFIRMA_ADELANTADO = re.compile(
    r"\b(?:"
    r"adelantad[oa]s?|"
    r"mas\s+adelantad[oa]s?|"
    r"adelanta(?:\s+sus)?(?:\s+lineas)?|"
    r"mas\s+campo\s+rival|"
    r"pisa\s+campo\s+rival|"
    r"mayor\s+(?:presencia|porcentaje|ocupacion)\s+en\s+campo\s+rival|"
    r"mas\s+territorio|"
    r"territorio\s+de\b|"
    r"juega\s+en\s+campo\s+(?:rival|contrario|de\b)|"
    r"instalad[oa]s?\s+en\s+campo\s+(?:rival|contrario|de\b)|"
    r"bloque\s+alto|"
    r"en\s+campo\s+contrario"
    r")\b"
)

# Negación válida: solo entre el sujeto y el verbo en la misma cláusula (o sujeto "ninguno...").
# Un inciso entre comas con "sin ..." (p. ej. "SKN, sin espacio atrás, juega adelantado") NO niega el verbo.
RE_NEGACION_VERBO = re.compile(r"\b(?:no|nunca|tampoco|ni)\b")
RE_SUJETO_NINGUNO = re.compile(r"\b(?:ninguno|ninguna|ningun)\b")

RE_NUMERO = re.compile(r"(?<![\w])(\d+(?:[.,]\d+)?)(?![\w])")


def _sin_acentos(texto: str) -> str:
    descomp = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in descomp if not unicodedata.combining(c))


def _patrones_equipos_activos() -> Dict[str, re.Pattern]:
    """
    Devuelve {codigo_equipo: regex_compilada_sin_acentos} para los equipos del partido activo
    y códigos históricos (ARG/FRA).
    """
    from implementacion import partido_config
    partido = partido_config.activo()
    patrones: Dict[str, re.Pattern] = {}
    for eq in partido.equipos:
        menciones_norm = [_sin_acentos(m) for m in eq.menciones]
        nombre_norm = re.escape(_sin_acentos(eq.nombre))
        cod_norm = re.escape(_sin_acentos(eq.codigo))
        todas = list(dict.fromkeys([nombre_norm, cod_norm, *menciones_norm]))
        patrones[eq.codigo] = re.compile(r"\b(?:" + "|".join(todas) + r")\b")
    # Soporte para corridas sintéticas con ARG / FRA si no están en el partido activo
    if "ARG" not in patrones:
        patrones["ARG"] = re.compile(r"\b(?:arg|argentina\w*|albiceleste\w*)\b")
    if "FRA" not in patrones:
        patrones["FRA"] = re.compile(r"\b(?:fra|francia\w*|frances\w*|bleus)\b")
    return patrones


def _numeros_permitidos_equipo(datos_eq: dict) -> Set[float]:
    """
    Conjunto de valores numéricos válidos para un equipo en una ventana:
    acepta el valor con 1 decimal y su redondeo a entero.
    """
    permitidos: Set[float] = set()
    if not isinstance(datos_eq, dict):
        return permitidos
    for clave in ("posicion_m", "pct_campo_rival", "largo_m", "ancho_m"):
        val = datos_eq.get(clave)
        if val is None or (isinstance(val, float) and (val != val)):
            continue
        fval = float(val)
        permitidos.add(round(fval, 1))
        permitidos.add(float(int(round(fval))))
    return permitidos


def _coincide_numero(num: float, permitidos: Set[float], tol: float = 0.051) -> bool:
    return any(abs(num - p) <= tol for p in permitidos)


def _dividir_oraciones(texto: str) -> List[str]:
    partes = re.split(r"(?:[.!?]+(?:\s+|$)|\n+)", texto)
    return [p.strip() for p in partes if p and p.strip()]


# ---------------------------------------------------------------------------
# Monitor M3 — auditor de llamadas LLM
# ---------------------------------------------------------------------------

class GovernanceMonitorM3:
    """
    Audita llamadas LLM individualmente y registra cada intento en governance_audit.jsonl.
    """

    def __init__(
        self,
        tactical_summaries: list,
        audit_log: str | pathlib.Path = AUDIT_LOG,
    ):
        CLEAN_DIR.mkdir(parents=True, exist_ok=True)
        self.audit_log = pathlib.Path(audit_log)
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self.tactical_summaries = {w["window_id"]: w for w in tactical_summaries}
        self._call_count = 0
        self._pass_count = 0

    def _verificar_palabras_prohibidas(self, texto_norm: str) -> Tuple[bool, List[str]]:
        halladas = sorted(set(RE_PALABRAS_PROHIBIDAS.findall(texto_norm)))
        return len(halladas) == 0, halladas

    def _verificar_territorio(
        self,
        oraciones_norm: List[str],
        ground_truth: dict,
        patrones_eq: Dict[str, re.Pattern],
    ) -> Tuple[bool, List[str]]:
        territorio = ground_truth.get("territorio")
        if not territorio:
            dom = ground_truth.get("dominant_team", "neutro")
            territorio = "repartido" if dom in ("neutro", "repartido", None, "") else dom

        equipos_ventana = list((ground_truth.get("equipos") or {}).keys())
        if not equipos_ventana:
            equipos_ventana = [k for k in patrones_eq if k in ("SKN", "CRC", "ARG", "FRA")]

        errores: List[str] = []

        for oracion in oraciones_norm:
            # Dividir en sub-cláusulas para evaluar qué equipo es el sujeto de la afirmación
            clausulas = [c.strip() for c in re.split(r"[;:]|,\s+(?:mientras|pero|aunque|y)\s+", oracion) if c.strip()]
            for cl in clausulas:
                m_adel = RE_AFIRMA_ADELANTADO.search(cl)
                if not m_adel:
                    continue

                # Detectar menciones de equipos antes y después del predicado de adelanto/territorio
                texto_adel = m_adel.group(0)
                eqs_antes: List[Tuple[int, int, str]] = []
                eqs_despues: List[Tuple[int, int, str]] = []
                for cod in equipos_ventana:
                    pat = patrones_eq.get(cod)
                    if not pat:
                        continue
                    for m_eq in pat.finditer(cl):
                        if m_eq.end() <= m_adel.start():
                            eqs_antes.append((m_eq.start(), m_eq.end(), cod))
                        elif m_eq.start() >= m_adel.end():
                            eqs_despues.append((m_eq.start(), m_eq.end(), cod))

                # La negación cuenta SOLO si está en la misma cláusula entre el sujeto y el verbo
                # (sin comas que separen la negación del verbo) o si el sujeto es "ninguno...".
                # Una coma con "sin ..." antes (p. ej. "SKN, sin espacio atrás, juega adelantado") NO niega el verbo.
                prefijo_completo = cl[:m_adel.start()]
                ultimo_tramo = prefijo_completo.rsplit(",", 1)[-1]
                if eqs_antes:
                    eqs_antes.sort(key=lambda x: x[0])
                    fin_sujeto = eqs_antes[-1][1]
                    entre_suj_y_verbo = cl[fin_sujeto:m_adel.start()]
                    tramo_suj_verbo = entre_suj_y_verbo.rsplit(",", 1)[-1]
                    if RE_NEGACION_VERBO.search(tramo_suj_verbo) or RE_SUJETO_NINGUNO.search(ultimo_tramo):
                        continue
                else:
                    if RE_NEGACION_VERBO.search(ultimo_tramo) or RE_SUJETO_NINGUNO.search(ultimo_tramo):
                        continue

                sujeto_cod: Optional[str] = None
                if texto_adel.startswith("territorio de") and eqs_despues:
                    eqs_despues.sort(key=lambda x: x[0])
                    sujeto_cod = eqs_despues[0][2]
                elif eqs_antes:
                    # Si antes del predicado se nombran ambos equipos ("A y B están adelantados"), evaluar todos
                    cods_antes = list(dict.fromkeys(c for _, _, c in sorted(eqs_antes)))
                    if len(cods_antes) == 1:
                        sujeto_cod = cods_antes[0]
                    else:
                        # Ambos nombrados como sujetos
                        if territorio == "repartido":
                            errores.append(
                                f"Territorio es 'repartido', pero la oración afirma ventaja/adelanto: '{cl}'."
                            )
                        continue
                elif eqs_despues:
                    eqs_despues.sort(key=lambda x: x[0])
                    sujeto_cod = eqs_despues[0][2]

                if territorio == "repartido":
                    errores.append(
                        f"Territorio es 'repartido', pero se afirma que {sujeto_cod or 'un equipo'} está adelantado/con más campo rival en: '{cl}'."
                    )
                else:
                    if sujeto_cod is not None and sujeto_cod != territorio:
                        errores.append(
                            f"Territorio pertenece a '{territorio}', pero se afirma que '{sujeto_cod}' está adelantado/con más territorio en: '{cl}'."
                        )

        return len(errores) == 0, errores

    def _verificar_mitades(
        self,
        oraciones_norm: List[str],
        ground_truth: dict,
        patrones_eq: Dict[str, re.Pattern],
    ) -> List[str]:
        """Compara «mitad rival» y «su mitad» con el % en campo rival del equipo nombrado."""
        equipos_dict = ground_truth.get("equipos") or {}
        errores: List[str] = []
        for oracion in oraciones_norm:
            menciones: List[Tuple[int, int, str]] = []
            for cod in equipos_dict:
                pat = patrones_eq.get(cod)
                if pat:
                    menciones += [(m.start(), m.end(), cod) for m in pat.finditer(oracion)]
            menciones.sort()
            for regex, es_rival in ((RE_EN_MITAD_RIVAL, True), (RE_EN_SU_MITAD, False)):
                for m in regex.finditer(oracion):
                    antes = oracion[:m.start()]
                    if RE_PCT_ANTES.search(antes):
                        continue
                    previas = [x for x in menciones if x[1] <= m.start()]
                    if previas:
                        cod = previas[-1][2]
                        tramo = oracion[previas[-1][1]:m.start()]
                    else:
                        posteriores = [x for x in menciones if x[0] >= m.end()]
                        if not posteriores:
                            continue
                        cod = posteriores[0][2]
                        tramo = antes
                    tramo = re.split(r"[;:]", tramo.rsplit(",", 1)[-1])[-1]
                    if RE_NEGACION_VERBO.search(tramo) or RE_SUJETO_NINGUNO.search(antes.rsplit(",", 1)[-1]):
                        continue
                    pct = (equipos_dict.get(cod) or {}).get("pct_campo_rival")
                    if pct is None or pct != pct:
                        continue
                    if es_rival and pct < 50:
                        errores.append(
                            f"Se ubica a '{cod}' en la mitad rival, pero solo tiene {round(pct)}% en campo rival: '{oracion}'."
                        )
                    elif not es_rival and pct > 50:
                        errores.append(
                            f"Se ubica a '{cod}' en su mitad, pero tiene {round(pct)}% en campo rival: '{oracion}'."
                        )
        return errores

    def _verificar_nombra_territorio(
        self,
        narracion_norm: str,
        ground_truth: dict,
        patrones_eq: Dict[str, re.Pattern],
    ) -> List[str]:
        """Si el territorio es de un equipo, la narración debe nombrarlo y no decir que está repartido."""
        territorio = ground_truth.get("territorio")
        if not territorio:
            dom = ground_truth.get("dominant_team", "neutro")
            territorio = "repartido" if dom in ("neutro", "repartido", None, "") else dom
        if territorio == "repartido":
            return []
        errores: List[str] = []
        pat = patrones_eq.get(territorio)
        if pat and not pat.search(narracion_norm):
            errores.append(f"El territorio es de '{territorio}', pero la narración no lo nombra.")
        m = RE_DICE_REPARTIDO.search(narracion_norm)
        if m:
            errores.append(f"El territorio es de '{territorio}', pero la narración dice «{m.group(0)}».")
        return errores

    def _verificar_numeros(
        self,
        oraciones_norm: List[str],
        ground_truth: dict,
        patrones_eq: Dict[str, re.Pattern],
    ) -> Tuple[bool, List[str]]:
        equipos_dict = ground_truth.get("equipos") or {}
        permitidos_por_eq: Dict[str, Set[float]] = {
            cod: _numeros_permitidos_equipo(datos_eq)
            for cod, datos_eq in equipos_dict.items()
        }
        todos_permitidos: Set[float] = set()
        for s in permitidos_por_eq.values():
            todos_permitidos |= s

        errores: List[str] = []

        for oracion in oraciones_norm:
            oracion = re.sub(r"\s*por\s+ciento\b", "%", oracion)
            en_letras = sorted(set(RE_NUMEROS_EN_LETRAS.findall(oracion)))
            if en_letras:
                errores.append(
                    f"Número escrito en letras ({', '.join(en_letras)}): escribe las cifras con dígitos."
                )

            matches_num = list(RE_NUMERO.finditer(oracion))
            if not matches_num:
                continue

            # Buscar menciones de equipos en la oración con sus posiciones
            menciones_oracion: List[Tuple[int, int, str]] = []
            for cod in equipos_dict:
                pat = patrones_eq.get(cod)
                if not pat:
                    continue
                for m_eq in pat.finditer(oracion):
                    menciones_oracion.append((m_eq.start(), m_eq.end(), cod))
            menciones_oracion.sort(key=lambda x: x[0])
            equipos_en_oracion = list(dict.fromkeys(c for _, _, c in menciones_oracion))

            for m_num in matches_num:
                raw_num = m_num.group(1).replace(",", ".")
                val = float(raw_num)

                if not _coincide_numero(val, todos_permitidos):
                    errores.append(
                        f"Número {m_num.group(1)} no existe en los datos de la ventana."
                    )
                    continue

                if not equipos_en_oracion:
                    errores.append(
                        f"Número {m_num.group(1)} citado sin nombrar a qué equipo pertenece en la oración."
                    )
                    continue

                if len(equipos_en_oracion) == 1:
                    cod_asignado = equipos_en_oracion[0]
                else:
                    # Si la oración nombra a ambos equipos, asignar el equipo más reciente antes del número
                    # (o el más cercano si el número aparece antes del primer equipo)
                    previos = [m for m in menciones_oracion if m[1] <= m_num.start()]
                    if previos:
                        cod_asignado = previos[-1][2]
                    else:
                        cod_asignado = menciones_oracion[0][2]

                if not _coincide_numero(val, permitidos_por_eq.get(cod_asignado, set())):
                    errores.append(
                        f"Número {m_num.group(1)} atribuido a {cod_asignado}, pero no corresponde a sus métricas en esta ventana."
                    )

        return len(errores) == 0, errores

    def audit_call(
        self,
        model_id: str,
        window_id: str,
        llm_response: Optional[dict],
        latency_ms: float,
        tokens_in: int = 0,
        tokens_out: int = 0,
        mode: str = "online",
        attempt: int = 1,
    ) -> dict:
        """
        Audita una llamada LLM completa y la registra en audit_log.
        """
        self._call_count += 1
        checks = {}
        errors = []

        # --- Chequeo 1: modelo correcto (debe ser IBM Granite) ---
        model_ok = mode == "offline" or model_id in AUTHORIZED_MODELS
        checks["model_id"] = {
            "pass": model_ok,
            "expected": sorted(AUTHORIZED_MODELS),
            "observed": "sin LLM (offline)" if mode == "offline" else model_id,
        }
        if not model_ok:
            errors.append(f"MODELO PROHIBIDO: '{model_id}'. Solo se permite '{REQUIRED_MODEL}'.")

        # --- Chequeo 2: formato JSON ---
        if llm_response is None:
            json_ok = False
            checks["json_format"] = {"pass": False, "error": "respuesta nula"}
            errors.append("Respuesta LLM nula.")
        else:
            missing = REQUIRED_FIELDS - set(llm_response.keys())
            json_ok = len(missing) == 0
            checks["json_format"] = {
                "pass": json_ok,
                "missing_fields": list(missing),
                "present_fields": list(set(llm_response.keys()) & REQUIRED_FIELDS),
            }
            if not json_ok:
                errors.append(f"Campos faltantes en JSON: {missing}")

        # --- Chequeo 3: longitud de narración (<= 18 palabras) ---
        narration = llm_response.get("narracion_es", "") if llm_response else ""
        word_count = len(narration.split()) if narration else 0
        narration_ok = 0 < word_count <= MAX_NARRATION_WORDS if llm_response else False
        checks["narration_length"] = {
            "pass": narration_ok,
            "word_count": word_count,
            "max_allowed": MAX_NARRATION_WORDS,
        }
        if not narration_ok:
            errors.append(f"Narración fuera de límite: {word_count} palabras (máx {MAX_NARRATION_WORDS}).")

        # --- Chequeos 4, 5 y 6: palabras prohibidas, territorio y números ---
        ground_truth = self.tactical_summaries.get(window_id, {})
        expected_territorio = ground_truth.get("territorio", ground_truth.get("dominant_team", "repartido"))
        patrones_eq = _patrones_equipos_activos()

        if llm_response and json_ok:
            analisis_txt = str(llm_response.get("analisis_tactico", ""))
            narracion_txt = str(llm_response.get("narracion_es", ""))
            combinado_norm = _sin_acentos(analisis_txt + ". " + narracion_txt)
            oraciones_norm = _dividir_oraciones(_sin_acentos(analisis_txt)) + _dividir_oraciones(_sin_acentos(narracion_txt))

            palabras_ok, prohibidas_halladas = self._verificar_palabras_prohibidas(combinado_norm)
            territorio_ok, err_territorio = self._verificar_territorio(oraciones_norm, ground_truth, patrones_eq)
            err_territorio = (
                err_territorio
                + self._verificar_mitades(oraciones_norm, ground_truth, patrones_eq)
                + self._verificar_nombra_territorio(_sin_acentos(narracion_txt), ground_truth, patrones_eq)
                + [
                    f"Redacción engañosa de la métrica: «{m.group(0)}» (el % es de posiciones en campo rival)."
                    for m in RE_REDACCION_METRICA.finditer(combinado_norm)
                ]
            )
            territorio_ok = not err_territorio
            numeros_ok, err_numeros = self._verificar_numeros(oraciones_norm, ground_truth, patrones_eq)
        else:
            palabras_ok, prohibidas_halladas = False, []
            territorio_ok, err_territorio = False, ["Sin respuesta JSON válida"]
            numeros_ok, err_numeros = False, ["Sin respuesta JSON válida"]

        checks["forbidden_words"] = {
            "pass": palabras_ok,
            "found": prohibidas_halladas,
        }
        if not palabras_ok:
            errors.append(f"Palabras prohibidas detectadas: {prohibidas_halladas}")

        checks["territory_consistency"] = {
            "pass": territorio_ok,
            "expected_territorio": expected_territorio,
            "errors": err_territorio,
        }
        if not territorio_ok:
            errors.extend(err_territorio)

        checks["numbers_accuracy"] = {
            "pass": numeros_ok,
            "errors": err_numeros,
        }
        if not numeros_ok:
            errors.extend(err_numeros)

        # Compatibilidad hacia atrás con lectores que buscan anti_hallucination
        anti_hallucin_ok = palabras_ok and territorio_ok and numeros_ok
        checks["anti_hallucination"] = {
            "pass": anti_hallucin_ok,
            "expected_dominant_team": expected_territorio,
            "window_id": window_id,
        }

        # --- Estado global de la llamada ---
        all_pass = all(c["pass"] for c in checks.values())
        status = "PASS" if all_pass else "FAIL"
        if all_pass:
            self._pass_count += 1

        cost_ru = 0.0 if mode == "offline" else round(tokens_in * RU_PER_TOKEN_IN + tokens_out * RU_PER_TOKEN_OUT, 6)

        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_id,
            "mode": mode,
            "window_id": window_id,
            "attempt": attempt,
            "latency_ms": round(latency_ms, 2),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "cost_ru_est": cost_ru,
            "status": status,
            "checks": checks,
            "errors": errors,
            # Texto auditado, para poder revisar a mano lo que Granite escribió (aun si se rechazó)
            "texto": {
                "analisis_tactico": str(llm_response.get("analisis_tactico", "")) if llm_response else "",
                "narracion_es": narration if llm_response else "",
            },
        }

        with open(self.audit_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(audit_entry, ensure_ascii=False, allow_nan=False) + "\n")

        if not all_pass:
            print(f"  [M3] ❌ {window_id} (intento {attempt}): {errors}")

        return audit_entry

    def finalize_report(
        self,
        report_path: str | pathlib.Path = REPORT_PATH,
        has_credentials: Optional[bool] = None,
    ) -> dict:
        """
        Genera el reporte final del Monitor M3.
        Juzga el ÚLTIMO intento de cada ventana y cuenta los anteriores aparte (retries).
        Separa online_calls y offline_calls, y avisa con WARNING si hay >=1 offline en corrida con credenciales.
        """
        report_path = pathlib.Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        all_entries = []

        if self.audit_log.exists():
            with open(self.audit_log, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_entries.append(json.loads(line))

        # Agrupar por window_id conservando el último intento de cada ventana
        ultimos_por_ventana: Dict[str, dict] = {}
        for e in all_entries:
            wid = e.get("window_id", "?")
            ultimos_por_ventana[wid] = e

        final_entries = list(ultimos_por_ventana.values())
        n_windows = len(final_entries)
        n_total_attempts = len(all_entries)
        n_retries = max(0, n_total_attempts - n_windows)

        n_pass = sum(1 for e in final_entries if e.get("status") == "PASS")
        n_fail = n_windows - n_pass
        n_offline = sum(1 for e in final_entries if e.get("mode") == "offline")
        n_online = sum(1 for e in final_entries if e.get("mode") == "online")

        status = "PASS" if n_fail == 0 and n_windows > 0 else "FAIL"

        if has_credentials is None:
            hubo_intento_online = any(e.get("mode") == "online" for e in all_entries)
            hay_env_creds = bool(
                os.environ.get("IBM_CLOUD_API_KEY", "").strip()
                and os.environ.get("WATSONX_URL", "").strip()
                and (os.environ.get("WATSONX_PROJECT_ID", "").strip() or os.environ.get("WATSONX_SPACE_ID", "").strip())
            )
            has_credentials = hubo_intento_online or hay_env_creds

        warning_msg: Optional[str] = None
        if n_offline >= 1 and has_credentials:
            warning_msg = (
                f"WARNING: {n_offline} de {n_windows} ventana(s) usaron plantilla offline "
                f"en una corrida con credenciales."
            )

        latencies = [e["latency_ms"] for e in all_entries if "latency_ms" in e]
        tokens_in = [e["tokens_in"] for e in all_entries if "tokens_in" in e]
        tokens_out = [e["tokens_out"] for e in all_entries if "tokens_out" in e]

        summary = {
            "total_calls": n_windows,
            "passed_calls": n_pass,
            "failed_calls": n_fail,
            "online_calls": n_online,
            "offline_calls": n_offline,
            "retries": n_retries,
            "total_attempts": n_total_attempts,
            "model_used": REQUIRED_MODEL,
            "latency_ms_mean": round(statistics.mean(latencies), 2) if latencies else 0,
            "latency_ms_max": round(max(latencies), 2) if latencies else 0,
            "tokens_in_mean": round(statistics.mean(tokens_in), 1) if tokens_in else 0,
            "tokens_out_mean": round(statistics.mean(tokens_out), 1) if tokens_out else 0,
            "total_cost_ru_est": round(sum(
                0.0 if e.get("mode") == "offline" else e.get("cost_ru_est", 0)
                for e in all_entries
            ), 4),
        }
        if warning_msg:
            summary["warning"] = warning_msg

        report = {
            "monitor": "M3",
            "name": "Auditoría LLM y watsonx.governance",
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "audit_log": str(self.audit_log),
        }
        if warning_msg:
            report["warning"] = warning_msg

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)

        self._print_report(report)
        return report

    def _print_report(self, report: dict) -> None:
        icon = "✅" if report["status"] == "PASS" else "❌"
        print(f"\n{'='*60}")
        print(f" MONITOR M3 — {report['name']}")
        print(f" Estado: {icon} {report['status']}")
        s = report["summary"]
        print(
            f" Ventanas: {s['total_calls']} total, {s['passed_calls']} PASS, "
            f"{s['failed_calls']} FAIL | {s['online_calls']} online, {s['offline_calls']} offline "
            f"(reintentos: {s['retries']})"
        )
        if s.get("warning"):
            print(f" ⚠️  {s['warning']}")
        print(f" Modelo: {s['model_used']}")
        print(f" Latencia media: {s['latency_ms_mean']} ms")
        print(f" Tokens (in/out media): {s['tokens_in_mean']} / {s['tokens_out_mean']}")
        print(f" Costo estimado total: {s['total_cost_ru_est']} RU")
        print(f" Audit log: {report['audit_log']}")
        print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Función de conveniencia para uso directo
# ---------------------------------------------------------------------------

def audit_narration_batch(
    narrations: list,
    tactical_summaries: list,
    model_id: str = REQUIRED_MODEL,
    audit_log: str | pathlib.Path = AUDIT_LOG,
    report_path: str | pathlib.Path = REPORT_PATH,
) -> dict:
    """
    Audita una lista de narraciones generadas por el agente.
    """
    audit_log = pathlib.Path(audit_log)
    if audit_log.exists():
        audit_log.unlink()

    monitor = GovernanceMonitorM3(tactical_summaries, audit_log=audit_log)
    for narr in narrations:
        wid = narr.get("window_id", "W?")
        llm_resp = {k: narr[k] for k in REQUIRED_FIELDS if k in narr}
        monitor.audit_call(
            model_id=model_id,
            window_id=wid,
            llm_response=llm_resp,
            latency_ms=narr.get("latency_ms", 0),
            tokens_in=narr.get("tokens_in", 0),
            tokens_out=narr.get("tokens_out", 0),
            mode=narr.get("mode", "online"),
        )

    return monitor.finalize_report(report_path=report_path)


if __name__ == "__main__":
    tactical_path = pathlib.Path("data/clean/tactical_summaries.json")
    narrations_path = pathlib.Path("data/clean/narrations.json")

    if not tactical_path.exists():
        print("[monitor_m3] No existe tactical_summaries.json. Ejecuta el engine primero.")
        raise SystemExit(1)

    with open(tactical_path, encoding="utf-8") as f:
        tactical_summaries = json.load(f)

    if not narrations_path.exists():
        print("[monitor_m3] No existe narrations.json. Ejecuta agent_narrator.py primero.")
        raise SystemExit(1)

    with open(narrations_path, encoding="utf-8") as f:
        narrations = json.load(f)

    report = audit_narration_batch(narrations, tactical_summaries)
    raise SystemExit(0 if report["status"] == "PASS" else 1)
