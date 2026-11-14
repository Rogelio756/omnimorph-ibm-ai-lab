"""
scripts/resumen_opiniones.py
============================
Lee data/clean/opiniones_prueba.jsonl y muestra un resumen para el equipo:
- cuántas respuestas hay y de cuántas personas distintas
- media de cada escala
- cuenta de las preguntas de opciones (rol, dispositivo, ensenarias)
- todos los textos libres agrupados por pregunta

Uso:
    .venv\\Scripts\\python.exe scripts/resumen_opiniones.py
    .venv\\Scripts\\python.exe scripts/resumen_opiniones.py --archivo otra_ruta.jsonl
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import os
import pathlib
import statistics

ROOT = pathlib.Path(__file__).parent.parent

ESCALAS = [
    ("claridad",         "¿Entendiste en 10 s qué es y para quién?"),
    ("sin_programacion", "¿Se entiende sin programación?"),
    ("util_partido",     "¿Te sirve para analizar un partido?"),
    ("confianza_datos",  "¿Te fías de los datos?"),
    ("chat",             "¿Qué tal el chat? (1-5 o No lo usé)"),
    ("funcionamiento",   "¿Funcionó bien?"),
]

OPCIONES = [
    ("rol",         "¿Cuál es tu rol?"),
    ("dispositivo", "¿Dónde lo probaste?"),
    ("ensenarias",  "¿Se lo enseñarías a un entrenador?"),
]

TEXTOS = [
    ("gusto",     "Lo que más gustó"),
    ("confundio", "Lo que confundió o falló"),
    ("mejora",    "Mejora propuesta"),
    ("nombre",    "Nombre (si indicó)"),
]


def cargar(ruta: str) -> list[dict]:
    registros = []
    if not os.path.exists(ruta):
        print(f"Archivo no encontrado: {ruta}")
        return registros
    with open(ruta, encoding="utf-8") as f:
        for i, linea in enumerate(f, 1):
            linea = linea.strip()
            if not linea:
                continue
            try:
                registros.append(json.loads(linea))
            except json.JSONDecodeError as exc:
                print(f"  [línea {i}] JSON inválido: {exc}")
    return registros


def separador(ch: str = "─", n: int = 70) -> str:
    return ch * n


def main() -> None:
    ap = argparse.ArgumentParser(description="Resumen de opiniones de la prueba.")
    ap.add_argument(
        "--archivo",
        default=str(ROOT / "data" / "clean" / "opiniones_prueba.jsonl"),
        help="Ruta al archivo de opiniones (defecto: data/clean/opiniones_prueba.jsonl)",
    )
    args = ap.parse_args()

    registros = cargar(args.archivo)
    if not registros:
        print("Sin opiniones todavía.")
        return

    personas = {r.get("id_prueba") for r in registros if r.get("id_prueba")}
    print(separador())
    print(f"  Opiniones: {len(registros)}  |  Personas distintas: {len(personas)}")
    print(separador())

    # Escalas
    print("\nEscalas (1–5)\n" + separador("·"))
    for campo, etiqueta in ESCALAS:
        valores = []
        no_uso = 0
        for r in registros:
            v = r.get(campo)
            if v is None:
                continue
            if isinstance(v, int):
                valores.append(v)
            else:
                no_uso += 1
        if valores:
            media = statistics.mean(valores)
            med = statistics.median(valores)
            linea = f"  {etiqueta}"
            linea += f"\n    n={len(valores)}  media={media:.2f}  mediana={med:.1f}"
            if no_uso:
                linea += f"  |  «No lo usé»: {no_uso}"
            print(linea)
        elif no_uso:
            print(f"  {etiqueta}\n    Sin valoración numérica · «No lo usé»: {no_uso}")
        else:
            print(f"  {etiqueta}\n    Sin respuestas")

    # Opciones
    print("\nOpciones\n" + separador("·"))
    for campo, etiqueta in OPCIONES:
        conteos: dict[str, int] = {}
        for r in registros:
            v = r.get(campo)
            if v:
                conteos[v] = conteos.get(v, 0) + 1
        if conteos:
            partes = ", ".join(f"{k}: {n}" for k, n in sorted(conteos.items(), key=lambda x: -x[1]))
            print(f"  {etiqueta}\n    {partes}")
        else:
            print(f"  {etiqueta}\n    Sin respuestas")

    # Textos libres
    print("\nTextos libres\n" + separador("·"))
    for campo, etiqueta in TEXTOS:
        valores = [r[campo].strip() for r in registros if isinstance(r.get(campo), str) and r[campo].strip()]
        if not valores:
            continue
        print(f"\n  {etiqueta} ({len(valores)} respuesta{'s' if len(valores) != 1 else ''}):")
        for i, v in enumerate(valores, 1):
            # Truncar textos muy largos para legibilidad
            resumen = v[:300] + ("…" if len(v) > 300 else "")
            print(f"  {i}. {resumen}")

    print("\n" + separador())


if __name__ == "__main__":
    main()
