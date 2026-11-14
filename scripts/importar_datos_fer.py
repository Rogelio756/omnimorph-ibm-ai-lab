"""Pasa los datos validados por Fer (equipo de análisis) al partido Costa Rica vs. San Cristóbal y Nieves.

Fuente: repo FerTC8/omnimorph-costa-rica-skn-2024, commit 8010944.
Copia sus datos en data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/ y corrige,
con esos datos, contexto_partido.json, estadisticas_partido.json y cronologia_goles.json.

Uso:
    python scripts/importar_datos_fer.py <ruta_al_repo_de_fer> [--aplicar]

Sin --aplicar solo muestra las diferencias.
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PARTIDO = RAIZ / "data" / "partidos" / "costa_rica_skn_eliminatorias_2026"
COMMIT_FER = "8010944"
REPO_FER = "https://github.com/FerTC8/omnimorph-costa-rica-skn-2024"
FECHA = "2026-11-14"

CODIGO = {"costa_rica": "CRC", "san_cristobal_y_nieves": "SKN"}

# métrica nuestra -> métrica de Fer (estadisticas.csv)
METRICAS = {
    "posesion_pct": "posesion_fotmob_pct",
    "tiros_totales": "tiros_totales",
    "tiros_a_puerta": "tiros_a_puerta",
    "tiros_fuera": "tiros_fuera",
    "tiros_bloqueados": "tiros_bloqueados",
    "tiros_dentro_area": "tiros_dentro_area",
    "tiros_fuera_area": "tiros_fuera_area",
    "pases_completados": "pases_precisos",
    "pases_intentados": "pases_intentados",
    "precision_pases_pct": "precision_pases_pct",
    "corners": "tiros_de_esquina",
    "faltas_cometidas": "faltas_cometidas",
    "fueras_de_juego": "fueras_de_juego",
    "tarjetas_amarillas": "tarjetas_amarillas",
    "tarjetas_rojas": "tarjetas_rojas",
    "atajadas_portero": "atajadas",
    "recuperaciones": "recuperaciones_totales_suma_jugadores",
}
PERIODOS = {"primer_tiempo": "primer_tiempo", "segundo_tiempo": "segundo_tiempo", "tiempo_completo": "total"}

# Fuentes nuestras con identificadores que no coinciden con los de Fer.
FUENTES_CORREGIDAS = {
    "F2": ("FIFA — Match Centre: Costa Rica vs. Saint Kitts and Nevis (Partido 400017724)",
           "https://api.fifa.com/api/v3/live/football/520/288301/288302/400017724?language=es"),
    "F7": ("ESPN — Match Report: Costa Rica vs. St. Kitts and Nevis (Game ID 698147)",
           "https://www.espn.com/soccer/match/_/gameId/698147"),
    "F8": ("Transfermarkt — Informe de partido Costa Rica vs. San Cristóbal y Nieves (Spielbericht 4343320)",
           "https://www.transfermarkt.com/spielbericht/index/spielbericht/4343320"),
}


def leer_json(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta: Path, datos) -> None:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")


def leer_csv(ruta: Path) -> list[dict]:
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def numero(valor: str):
    if valor in ("", None, "no_disponible"):
        return None
    try:
        v = float(valor)
    except ValueError:
        return valor
    return int(v) if v.is_integer() else v


def corregir_plantillas(contexto: dict, alineaciones: list[dict], eventos: list[dict], cambios: list[str]) -> None:
    for clave, codigo in CODIGO.items():
        plantilla = contexto["equipos"][clave]["plantilla"]
        for fila in (r for r in alineaciones if r["codigo"] == codigo):
            dorsal = fila["dorsal"]
            j = plantilla.get(dorsal)
            if j is None:
                cambios.append(f"{codigo} #{dorsal}: no está en nuestra plantilla")
                continue
            if j["nombre"] != fila["nombre"]:
                cambios.append(f"{codigo} #{dorsal}: nombre {j['nombre']!r} -> {fila['nombre']!r}")
                j["nombre"] = fila["nombre"]
            minutos = int(fila["minutos_jugados"] or 0)
            if j.get("minutos") != minutos:
                cambios.append(f"{codigo} #{dorsal}: minutos {j.get('minutos')} -> {minutos}")
                j["minutos"] = minutos
            titular = fila["titular"] == "true"
            if j.get("titular") != titular:
                cambios.append(f"{codigo} #{dorsal}: titular {j.get('titular')} -> {titular}")
                j["titular"] = titular

    # Minuto de los cambios en el texto de los eventos.
    for ev in (e for e in eventos if e["tipo_evento"] == "sustitucion"):
        clave = next(k for k, c in CODIGO.items() if c == ev["codigo"])
        plantilla = contexto["equipos"][clave]["plantilla"]
        minuto = ev["minuto_num"]
        for dorsal, palabra in ((ev["dorsal_principal"], "Ingres"), (ev["dorsal_secundario"], "Sustituido")):
            j = plantilla.get(dorsal)
            if not j:
                continue
            nuevos = []
            for texto in j.get("eventos", []):
                if texto.startswith(palabra) and f"al {minuto}'" not in texto:
                    corregido = texto.split(" al ")[0] + f" al {minuto}'" + (
                        " por " + texto.split(" por ", 1)[1] if " por " in texto else "")
                    cambios.append(f"{ev['codigo']} #{dorsal}: evento {texto!r} -> {corregido!r}")
                    texto = corregido
                nuevos.append(texto)
            j["eventos"] = nuevos


def corregir_estadisticas(estad: dict, filas: list[dict], cambios: list[str]) -> None:
    fer = {(r["periodo"], r["metrica"]): r for r in filas}
    for nuestro_p, fer_p in PERIODOS.items():
        bloque = estad["resumen_comparativo"][nuestro_p]
        for nuestra, de_fer in METRICAS.items():
            fila = fer.get((fer_p, de_fer))
            if not fila:
                continue
            nuevo = {"costa_rica": numero(fila["costa_rica"]),
                     "san_cristobal_y_nieves": numero(fila["san_cristobal_y_nieves"])}
            if bloque.get(nuestra) != nuevo:
                cambios.append(f"estadísticas {nuestro_p}.{nuestra}: {bloque.get(nuestra)} -> {nuevo}")
                bloque[nuestra] = nuevo
        comp, intent = bloque.get("pases_completados", {}), bloque.get("pases_intentados", {})
        if comp.get("costa_rica") is not None and intent.get("costa_rica") is not None:
            bloque["pases_completados_intentados"] = {
                k: f"{comp[k]}/{intent[k]}" for k in ("costa_rica", "san_cristobal_y_nieves")}
        # Fer: xG no publicado por FotMob, ESPN ni FIFA para este partido.
        if bloque.get("xg_esperado", {}).get("costa_rica") is not None:
            cambios.append(f"estadísticas {nuestro_p}.xg_esperado: {bloque['xg_esperado']} -> sin dato (Fer: no disponible)")
        bloque["xg_esperado"] = {"costa_rica": None, "san_cristobal_y_nieves": None}


def corregir_goles(goles: list[dict], eventos: list[dict], cambios: list[str]) -> None:
    fer = [e for e in eventos if e["tipo_evento"] == "gol"]
    for g, e in zip(goles, fer):
        if g["minuto"] != int(e["minuto_num"]) or g["anotador"]["dorsal"] != int(e["dorsal_principal"]):
            raise SystemExit(f"Gol {g['orden']} no coincide con Fer: {g['minuto']}' vs {e['minuto']}")
        reloj = numero(e["reloj_segundos"])
        if g.get("segundo_oficial") != reloj:
            cambios.append(f"gol {g['orden']}: segundo_oficial {g.get('segundo_oficial')} -> {reloj}")
            g["segundo_oficial"] = reloj
        if e["parte_cuerpo"] and g.get("pie_remate") != e["parte_cuerpo"]:
            cambios.append(f"gol {g['orden']}: pie_remate {g.get('pie_remate')} -> {e['parte_cuerpo']}")
            g["pie_remate"] = e["parte_cuerpo"]


def corregir_procedencia(contexto: dict, ficha: dict, cambios: list[str]) -> None:
    info = contexto["partido_info"]
    ids = ficha["meta"]["identificadores_externos"]
    if info.get("identificadores_externos") != ids:
        cambios.append("partido_info.identificadores_externos <- ficha de Fer")
        info["identificadores_externos"] = ids

    proc = contexto["procedencia"]
    for fuente in proc["fuentes"]:
        if fuente["id"] in FUENTES_CORREGIDAS:
            nombre, url = FUENTES_CORREGIDAS[fuente["id"]]
            if fuente["url"] != url:
                cambios.append(f"fuente {fuente['id']}: {fuente['url']} -> {url}")
                fuente["nombre"], fuente["url"] = nombre, url
    if not any(f["id"] == "F17" for f in proc["fuentes"]):
        proc["fuentes"].append({
            "id": "F17",
            "nombre": "Fer (equipo de análisis) — Paquete de datos verificados del partido",
            "url": f"{REPO_FER}/tree/{COMMIT_FER}",
            "datos": "Alineaciones, minutos, cambios, eventos con hora UTC, estadísticas por tiempo (FotMob/Opta) e identificadores oficiales.",
            "fecha_consulta": FECHA,
        })
    if proc.get("validado") is not True:
        cambios.append("procedencia.validado: false -> true")
    proc.update({
        "validado": True,
        "validado_por": "Fer (equipo de análisis)",
        "fecha_validacion": FECHA,
        "fuente_validacion": f"{REPO_FER} (commit {COMMIT_FER})",
        "copia_local": "data/partidos/costa_rica_skn_eliminatorias_2026/fer_validacion/",
    })


def corregir_textos(contexto: dict, goles: list[dict], cambios: list[str]) -> None:
    """Textos que los datos de Fer dejan desactualizados."""
    clima = contexto["partido_info"].get("condiciones_climaticas", {})
    cielo = "Lluvia intensa durante todo el partido (cancha rápida y resbaladiza)"
    if clima.get("cielo") != cielo:
        cambios.append(f"clima.cielo: {clima.get('cielo')!r} -> {cielo!r}")
        clima["cielo"] = cielo
    textos = {
        "F1": "Competición, fase, formato de ronda única del Grupo B, resultado 4-0 y goleadores.",
        "F9": "Estadísticas por equipo en total, 1T y 2T (tiros 23-5, a puerta 7-1, pases 483/571 vs 221/300). Sin xG publicado.",
    }
    for fuente in contexto["procedencia"]["fuentes"]:
        if fuente["id"] in textos and fuente["datos"] != textos[fuente["id"]]:
            cambios.append(f"fuente {fuente['id']}: descripción actualizada")
            fuente["datos"] = textos[fuente["id"]]
    for g in goles:
        narracion = g.get("narracion") or ""
        if "DISCREPANCIA" in narracion:
            limpio = narracion.split(" DISCREPANCIA")[0]
            cambios.append(f"gol {g['orden']}: discrepancia resuelta con la cronología oficial FIFA ({g['minuto']}')")
            g["narracion"] = limpio


NOMBRE_EQUIPO = {"costa_rica": "Costa Rica", "san_cristobal_y_nieves": "San Cristóbal y Nieves"}


def _pct(acertados, intentados):
    return round(100 * acertados / intentados, 1) if intentados else None


def rendimiento_individual(estadisticas_fer: dict) -> list[dict]:
    """Una fila compacta por jugador con minutos (FotMob/Opta vía Fer)."""
    filas = []
    for clave, nombre_equipo in NOMBRE_EQUIPO.items():
        for j in estadisticas_fer["estadisticas_jugadores"][clave]:
            if not j.get("participo"):
                continue
            fila = {
                "jugador": j["nombre"], "dorsal": j["dorsal"], "equipo": nombre_equipo,
                "minutos": j["minutos_jugados"], "calificacion_fotmob": j.get("rating_fotmob"),
            }
            if j.get("es_portero"):
                fila.update({
                    "atajadas": j.get("atajadas"),
                    "goles_recibidos": j.get("goles_concedidos"),
                    "error_derivado_en_gol": j.get("error_derivado_en_gol"),
                })
            else:
                fila.update({
                    "goles": j.get("goles"), "asistencias": j.get("asistencias"),
                    "tiros_totales": j.get("tiros_totales"), "tiros_a_puerta": j.get("tiros_a_puerta"),
                    "ocasiones_creadas": j.get("ocasiones_creadas"),
                    "duelos_ganados": j.get("duelos_ganados"),
                    "entradas": j.get("entradas_tackles"), "intercepciones": j.get("intercepciones"),
                    "despejes": j.get("despejes"),
                })
            fila.update({
                "toques": j.get("toques"),
                "pases_completados": j.get("pases_precisos"),
                "pases_totales": j.get("pases_intentados"),
                "precision_pases_pct": _pct(j.get("pases_precisos") or 0, j.get("pases_intentados") or 0),
                "recuperaciones": j.get("recuperaciones"),
            })
            filas.append({k: v for k, v in fila.items() if v is not None})
    return filas


def metricas_adicionales(filas_csv: list[dict]) -> dict:
    """Métricas de equipo de Fer que no tienen lugar en resumen_comparativo."""
    ya = set(METRICAS.values()) | {"posesion_fifa_oficial_pct", "recuperaciones_jugadores_campo",
                                   "recuperaciones_porteros"}
    salida: dict = {}
    for r in filas_csv:
        if r["metrica"] in ya or r["periodo"] not in PERIODOS.values():
            continue
        periodo = {v: k for k, v in PERIODOS.items()}.get(r["periodo"], r["periodo"])
        salida.setdefault(periodo, {})[r["metrica"]] = {
            "costa_rica": numero(r["costa_rica"]),
            "san_cristobal_y_nieves": numero(r["san_cristobal_y_nieves"]),
        }
    return salida


def eventos_compactos(eventos: list[dict]) -> list[dict]:
    salida = []
    for e in eventos:
        fila = {
            "minuto": e["minuto"], "tipo": e["tipo_evento"], "equipo": e["equipo"],
            "jugador": e["jugador_principal"] or None,
            "dorsal": numero(e["dorsal_principal"]),
            "jugador_secundario": e["jugador_secundario"] or None,
            "hora_utc": e["timestamp_utc"] or None,
            "descripcion": e["descripcion"],
        }
        salida.append({k: v for k, v in fila.items() if v is not None})
    return salida


def seccion_markdown(texto: str, numero_seccion: int) -> str:
    """Sección '## N.' de ANALISIS_PARTIDO.md, hasta la siguiente '## '."""
    lineas, dentro = [], False
    for linea in texto.splitlines():
        if linea.startswith("## "):
            dentro = linea.startswith(f"## {numero_seccion}.")
        if dentro:
            lineas.append(linea)
    return "\n".join(lineas).strip() + "\n"


def enriquecer(contexto: dict, estad: dict, goles: list[dict], datos: Path, cambios: list[str]) -> dict:
    """Todo lo demás del paquete de Fer. Devuelve archivos nuevos {nombre: contenido}."""
    ficha = leer_json(datos / "ficha_partido.json")
    estad_fer = leer_json(datos / "estadisticas.json")
    alineaciones = leer_csv(datos / "alineaciones.csv")
    eventos = leer_csv(datos / "goles_y_eventos.csv")
    info = contexto["partido_info"]

    # Clima: Fer solo confirma la lluvia; temperatura, humedad y viento no tienen fuente oficial.
    clima = info.get("condiciones_climaticas", {})
    nuevo_clima = {
        "resumen": "Lluvia intensa",
        "cielo": "Lluvia intensa durante todo el partido (cancha rápida y resbaladiza)",
        "temperatura_c": None, "humedad_pct": None, "viento_kmh": None,
        "nota": "Temperatura, humedad y viento: sin dato oficial (FIFA no los publica).",
    }
    if clima != nuevo_clima:
        cambios.append("clima: temperatura, humedad y viento -> sin dato (Fer)")
        info["condiciones_climaticas"] = nuevo_clima

    info["contexto_competitivo"] = ficha["contexto_competitivo"]
    info["discrepancias_resueltas"] = [
        {"tema": d["tema"], "valor_adoptado": d.get("valor_adoptado"), "motivo": d.get("motivo")}
        for d in ficha["resumen_discrepancias_interfuentes"]
    ]
    no_disp = estad_fer["metricas_no_disponibles"]
    info["datos_no_disponibles"] = {
        "campos": no_disp["campos"] + ["temperatura_humedad_viento"],
        "motivo": no_disp["motivo"],
    }

    roles = {(r["codigo"], r["dorsal"]): r for r in alineaciones}
    for clave, codigo in CODIGO.items():
        equipo = contexto["equipos"][clave]
        for dorsal, j in equipo["plantilla"].items():
            r = roles.get((codigo, dorsal))
            if r and r["rol_tactico"]:
                j["rol_tactico"] = r["rol_tactico"]
        esquema = {r["esquema_inicial"] for r in alineaciones if r["codigo"] == codigo}
        if codigo == "CRC":
            equipo["esquema_nota"] = "3-4-3 según FIFA y ESPN; 3-4-2-1 según FotMob (5-2-3 / 5-4-1 sin balón)."
        elif esquema:
            equipo["esquema_nota"] = f"{esquema.pop()} según FIFA, FotMob y ESPN."
        equipo["uniforme_detalle"] = {
            k.removeprefix(clave + "_"): v for k, v in ficha["uniformes"].items() if k.startswith(clave)
        }
        dt = ficha["directores_tecnicos"].get(clave, {})
        if dt.get("nacionalidad"):
            equipo["entrenador_nacionalidad"] = dt["nacionalidad"]
    cambios.append("plantillas: rol táctico, nota de esquema, uniforme detallado y nacionalidad del DT")

    estad["rendimiento_individual_destacado"] = rendimiento_individual(estad_fer)
    estad["fuente_rendimiento_individual"] = estad_fer["estadisticas_jugadores"]["fuente"]
    estad["metricas_adicionales"] = metricas_adicionales(leer_csv(datos / "estadisticas.csv"))
    cambios.append(f"estadísticas: {len(estad['rendimiento_individual_destacado'])} jugadores con datos individuales "
                   f"y {len(estad['metricas_adicionales'].get('tiempo_completo', {}))} métricas adicionales")

    for g, e in zip(goles, (e for e in eventos if e["tipo_evento"] == "gol")):
        g["jugada"] = e["descripcion"]
        g["zona_remate"] = e["zona_aproximada_tactica"].replace("[estimacion_tactica] ", "") or None
        g["coordenadas_fifa"] = {"x": numero(e["coord_fifa_x"]), "y": numero(e["coord_fifa_y"])}

    analisis = (datos.parent / "ANALISIS_PARTIDO.md").read_text(encoding="utf-8")
    return {
        "eventos_partido.json": eventos_compactos(eventos),
        "analisis_tactico.md": seccion_markdown(analisis, 6),
    }


def copiar_paquete(repo: Path) -> None:
    destino = PARTIDO / "fer_validacion"
    destino.mkdir(exist_ok=True)
    for ruta in sorted((repo / "datos").glob("*")):
        shutil.copy2(ruta, destino / ruta.name)
    for nombre in ("README.md", "FUENTES.md", "ANALISIS_PARTIDO.md"):
        shutil.copy2(repo / nombre, destino / nombre)
    (destino / "ORIGEN.txt").write_text(
        f"Copia de {REPO_FER}, commit {COMMIT_FER}, hecha el {FECHA}.\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    repo = Path(sys.argv[1])
    aplicar = "--aplicar" in sys.argv[2:]
    datos = repo / "datos"

    contexto_p = PARTIDO / "partido" / "contexto_partido.json"
    estad_p = PARTIDO / "partido" / "estadisticas_partido.json"
    goles_p = PARTIDO / "partido" / "cronologia_goles.json"
    contexto, estad, goles = leer_json(contexto_p), leer_json(estad_p), leer_json(goles_p)
    alineaciones = leer_csv(datos / "alineaciones.csv")
    eventos = leer_csv(datos / "goles_y_eventos.csv")

    cambios: list[str] = []
    corregir_plantillas(contexto, alineaciones, eventos, cambios)
    corregir_estadisticas(estad, leer_csv(datos / "estadisticas.csv"), cambios)
    corregir_goles(goles, eventos, cambios)
    corregir_procedencia(contexto, leer_json(datos / "ficha_partido.json"), cambios)
    corregir_textos(contexto, goles, cambios)
    nuevos = enriquecer(contexto, estad, goles, datos, cambios)

    for c in cambios:
        print(" -", c)
    print(f"{len(cambios)} cambios.")
    if aplicar:
        escribir_json(contexto_p, contexto)
        escribir_json(estad_p, estad)
        escribir_json(goles_p, goles)
        for nombre, contenido in nuevos.items():
            ruta = PARTIDO / "partido" / nombre
            if nombre.endswith(".json"):
                escribir_json(ruta, contenido)
            else:
                ruta.write_text(contenido, encoding="utf-8")
        copiar_paquete(repo)
        print("[OK] aplicados y paquete de Fer copiado en fer_validacion/")
    else:
        print("Vista previa. Agrega --aplicar para escribir.")


if __name__ == "__main__":
    main()
