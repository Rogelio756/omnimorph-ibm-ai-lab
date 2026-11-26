"""
scripts/generar_datos_curiosos.py
Datos curiosos de cada equipo para los paneles de la página Transmisión.

IBM Granite (ibm/granite-4-h-small, watsonx.ai) redacta frases cortas a partir
de HECHOS que salen de partido.json. Cada frase se verifica antes de usarla:
  - 18 palabras o menos;
  - todo número debe estar en los hechos de ese equipo;
  - todo nombre propio debe aparecer en los hechos;
  - sin palabras de cosas que no se miden (velocidad, km/h, sprint, xG).
Si Granite no está disponible o una frase no pasa, se usa el hecho tal cual
(plantilla verificada). Una sola llamada por equipo (2 en total).

Uso:
    .venv\\Scripts\\python.exe -X utf8 scripts/generar_datos_curiosos.py            # con Granite si hay .env
    .venv\\Scripts\\python.exe -X utf8 scripts/generar_datos_curiosos.py --offline  # solo plantilla, 0 RU
Después: .venv\\Scripts\\python.exe -X utf8 scripts/export_transmision.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PARTIDO = ROOT / "dashboard" / "data" / "partido" / "partido.json"
OUT = ROOT / "dashboard" / "data" / "datos_curiosos.json"

MAX_PALABRAS = 18
N_DATOS = 6
PROHIBIDAS = re.compile(r"velocidad|km/?h|sprint|\bxg\b|kil[oó]metros", re.I)
# Juicios que los datos no respaldan (mismo criterio que M3 con la crónica)
ADJETIVOS = re.compile(
    r"domin|presi[oó]n|presion[oa]|control|clave|tempran|decisiv|espectacular|brillant|"
    r"hist[oó]ric|aplast|arroll|humill|contundent|impresionant|incre[ií]ble|abrumador", re.I)
EN_LETRAS = re.compile(
    r"\b(dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|veinte|treinta)\b", re.I)


def _sa(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower()


def _numeros(t: str) -> set[float]:
    return {float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", t)}


# ── Hechos verificados por equipo ──────────────────────────────────────────
def hechos_equipo(d: dict, clave: str) -> list[str]:
    eq = d["equipos"][clave]
    nombre = eq["pais"]
    tc = d["estadisticas"]["resumen_comparativo"]["tiempo_completo"]
    ma = d["estadisticas"]["metricas_adicionales"]["tiempo_completo"]
    v = lambda bloque, k: bloque.get(k, {}).get(clave)

    # Orden = prioridad de la plantilla: goles y figuras primero; esquema al final
    # (el encabezado del panel ya lo muestra)
    h: list[str] = []
    goles = [g for g in d.get("goles", []) if g.get("equipo_anotador") == nombre]
    for g in goles:
        h.append(f"{g['anotador']['nombre']} marcó el {g['marcador_momento']} al minuto {g['minuto']}.")

    ri = [r for r in d["estadisticas"].get("rendimiento_individual_destacado", [])
          if r.get("equipo") == nombre and r.get("calificacion_fotmob")]
    if ri:
        mejor = max(ri, key=lambda r: r["calificacion_fotmob"])
        h.append(f"El mejor calificado de {nombre} en FotMob fue {mejor['jugador']} (#{mejor['dorsal']}), con {mejor['calificacion_fotmob']}.")
    if v(tc, "posesion_pct") is not None:
        h.append(f"{nombre} tuvo el balón el {v(tc, 'posesion_pct')} % del partido completo.")
    if v(tc, "tiros_totales") is not None:
        h.append(f"{nombre} remató {v(tc, 'tiros_totales')} veces, {v(tc, 'tiros_a_puerta')} a puerta, en todo el partido.")
    if v(tc, "precision_pases_pct") is not None:
        h.append(f"{nombre} acertó el {v(tc, 'precision_pases_pct')} % de sus pases.")
    if v(ma, "toques_area_rival") is not None:
        h.append(f"{nombre} tocó el balón {v(ma, 'toques_area_rival')} veces dentro del área rival.")
    if v(ma, "duelos_aereos_ganados") is not None:
        h.append(f"{nombre} ganó {v(ma, 'duelos_aereos_ganados')} duelos aéreos.")
    if v(tc, "atajadas_portero"):
        h.append(f"El portero de {nombre} hizo {v(tc, 'atajadas_portero')} atajadas.")
    if v(ma, "despejes"):
        h.append(f"{nombre} despejó el balón {v(ma, 'despejes')} veces.")

    if eq.get("capitan"):
        h.append(f"El capitán de {nombre} fue {eq['capitan'].split(' (')[0]}.")
    h.append(f"{nombre} jugó con un {eq['esquema_inicial']}; su entrenador es {eq['entrenador']} ({eq['entrenador_nacionalidad']}).")
    return h


# ── Verificación ───────────────────────────────────────────────────────────
def verificar(frase: str, hechos: list[str]) -> list[str]:
    errores = []
    texto_hechos = " ".join(hechos)
    if len(frase.split()) > MAX_PALABRAS:
        errores.append(f"más de {MAX_PALABRAS} palabras")
    permitidos = _numeros(texto_hechos)
    for n in _numeros(frase):
        if n not in permitidos:
            errores.append(f"número sin respaldo: {n:g}")
    hechos_sa = _sa(texto_hechos)
    palabras = re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñü]+", frase)
    for i, p in enumerate(palabras):
        if frase.strip().startswith(p) and i == 0:
            continue
        if _sa(p) not in hechos_sa:
            errores.append(f"nombre sin respaldo: {p}")
    if PROHIBIDAS.search(frase):
        errores.append("menciona algo que no se mide")
    m = ADJETIVOS.search(frase)
    if m:
        errores.append(f"juicio sin respaldo: «{m.group(0)}»")
    m = EN_LETRAS.search(frase)
    if m:
        errores.append(f"número en letras: «{m.group(0)}»")
    return errores


# ── Granite ────────────────────────────────────────────────────────────────
def prompt_equipo(nombre: str, hechos: list[str]) -> str:
    lista = "\n".join(f"- {x}" for x in hechos)
    return (
        f"Escribe {N_DATOS} datos curiosos sobre {nombre} para el panel de una transmisión de fútbol.\n"
        f"Usa SOLO estos hechos; no agregues cifras, nombres ni detalles que no estén aquí:\n{lista}\n\n"
        f"Reglas: español, tono de transmisión deportiva, cada dato de {MAX_PALABRAS} palabras o menos, "
        "copia los números tal cual (con dígitos), un hecho distinto por dato, sin velocidades ni distancias. "
        "No califiques: nada de «dominó», «clave», «temprano», «decisivo» ni adjetivos que el hecho no diga.\n"
        'Responde solo este JSON: {"datos": ["...", "..."]}'
    )


def con_granite(nombre: str, hechos: list[str]):
    from implementacion.cloud_agent import agent_narrator as an
    creds = an._get_watsonx_credentials()
    if not creds:
        return None, {"motivo": "sin credenciales"}
    an.WATSONX_MAX_TOKENS = 450  # 6 frases no caben en los 220 del narrador
    model = an._init_watsonx_model(creds)
    if model is None:
        return None, {"motivo": "no se pudo iniciar el modelo"}
    parsed, lat, tin, tout = an._call_watsonx(model, prompt_equipo(nombre, hechos))
    meta = {"modelo": an.REQUIRED_MODEL, "latency_ms": round(lat, 1), "tokens_in": tin, "tokens_out": tout}
    if not parsed or not isinstance(parsed.get("datos"), list):
        meta["motivo"] = "respuesta sin JSON válido"
        return None, meta
    return [str(x).strip() for x in parsed["datos"] if str(x).strip()], meta


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="no llama a Granite (0 RU)")
    ap.add_argument("--reverificar", action="store_true",
                    help="vuelve a verificar las frases de Granite ya guardadas, sin llamarlo (0 RU)")
    args = ap.parse_args()
    previo = json.loads(OUT.read_text(encoding="utf-8")) if args.reverificar and OUT.exists() else None

    d = json.loads(PARTIDO.read_text(encoding="utf-8"))
    salida = {"generado": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "nota": "Frases de Granite verificadas contra partido.json; si una no pasa, se usa el hecho tal cual.",
              "equipos": {}, "auditoria": []}

    for clave in d.get("equipos_orden", list(d["equipos"])):
        eq = d["equipos"][clave]
        hechos = hechos_equipo(d, clave)
        if previo is not None:
            aud = next((a for a in previo.get("auditoria", []) if a.get("equipo") == eq["codigo"]), {})
            datos = aud.get("granite_crudas") or [x["texto"] for x in previo["equipos"].get(eq["codigo"], [])
                                                   if x.get("origen") == "granite"]
            meta = {k: v for k, v in aud.items()
                    if k in ("modelo", "latency_ms", "tokens_in", "tokens_out", "generado_granite")}
            meta.setdefault("generado_granite", previo.get("generado"))
            meta["reverificado"] = salida["generado"]
        elif args.offline:
            datos, meta = [], {"motivo": "--offline"}
        else:
            datos, meta = con_granite(eq["pais"], hechos)
            meta["generado_granite"] = salida["generado"]
        aceptados, rechazados = [], []
        for frase in datos or []:
            err = verificar(frase, hechos)
            (rechazados if err else aceptados).append({"texto": frase, "errores": err} if err else frase)
        lista = [{"texto": f, "origen": "granite"} for f in aceptados[:N_DATOS]]
        usados = {_sa(x["texto"]) for x in lista}
        for hecho in hechos:  # completar con plantilla verificada
            if len(lista) >= N_DATOS:
                break
            if _sa(hecho) not in usados and not verificar(hecho, hechos):
                lista.append({"texto": hecho, "origen": "plantilla"})
        salida["equipos"][eq["codigo"]] = lista
        salida["auditoria"].append({"equipo": eq["codigo"], **meta,
                                    "granite_crudas": list(datos or []),
                                    "granite_aceptadas": len(aceptados),
                                    "granite_rechazadas": rechazados})
        n_g = sum(1 for x in lista if x["origen"] == "granite")
        print(f"{eq['codigo']}: {len(lista)} datos ({n_g} de Granite, {len(lista) - n_g} de plantilla); "
              f"rechazadas {len(rechazados)}")
        for r in rechazados:
            print(f"   RECHAZADA: {r['texto']}  → {'; '.join(r['errores'])}")

    OUT.write_text(json.dumps(salida, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Escrito {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
