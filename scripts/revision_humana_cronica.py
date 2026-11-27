"""
scripts/revision_humana_cronica.py
Corrección humana de la redacción de la crónica, con rastro en la auditoría M3.

Uso: cuando una frase de Granite acierta en los datos pero los redacta mal
(por ejemplo «88% del territorio»), se corrige aquí el texto, se deja la nota
«revision_humana» en narrations.json, y el texto corregido se vuelve a auditar
con M3 (costo 0 RU, sin llamar a Granite). Si M3 no da PASS, no se guarda nada.

    .venv\\Scripts\\python.exe -X utf8 scripts/revision_humana_cronica.py
Después: run_pipeline.run_etapa4 (voces) y los exportadores; o
    .venv\\Scripts\\python.exe -X utf8 scripts/revision_humana_cronica.py --regenerar
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementacion.cloud_agent.governance_monitor_m3 import GovernanceMonitorM3, REQUIRED_MODEL

CLEAN = ROOT / "data" / "clean"
NARR = CLEAN / "narrations.json"
AUDIT = CLEAN / "governance_audit.jsonl"
REPORT = CLEAN / "monitor_m3.json"

# Correcciones del 2026-11-26 (corrida de Granite de las 17:58). Solo redacción; mismos datos.
CORRECCIONES = {
    "W0": {
        "analisis_tactico": (
            "San Cristóbal y Nieves se ubica en su mitad, a 37 metros de su portería, con 6% en campo rival. "
            "Costa Rica se encuentra en campo rival, a 70 metros de su portería, con un largo de 12 metros "
            "y un ancho de 38 metros, y 88% en campo rival."
        ),
        "motivo": "«ocupando el 88% del territorio» y «un espacio de 6%»: el % es de posiciones en campo rival",
    },
    "W5": {
        "analisis_tactico": (
            "San Cristóbal y Nieves se ubica en su mitad de campo, a 36 metros de su portería, con 6% en campo rival, "
            "un largo de 13 metros y un ancho de 33 metros. Costa Rica se encuentra en campo rival, a 67 metros "
            "de su portería, con 94% en campo rival, un largo de 14 metros y un ancho de 38 metros."
        ),
        "motivo": "«94% de territorio» y «un espacio de 6%»: el % es de posiciones en campo rival",
    },
    "W6": {
        "narracion_es": "Costa Rica adelantado, 61 metros; San Cristóbal y Nieves en su mitad.",
        "motivo": "«en mitad» sin «su»",
    },
}
CAMPOS = ("window_id", "t0", "t1", "analisis_tactico", "narracion_es")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regenerar", action="store_true",
                    help="después de corregir, regenera voces, video y datos de la web")
    args = ap.parse_args()

    narr = json.loads(NARR.read_text(encoding="utf-8"))
    tactical = json.loads((CLEAN / "tactical_summaries.json").read_text(encoding="utf-8"))
    hoy = dt.date.today().isoformat()

    # 1) Auditar los textos corregidos en una auditoría temporal: si alguno falla, no se guarda nada
    tmp_audit = CLEAN / "_revision_tmp.jsonl"
    mon = GovernanceMonitorM3(tactical, audit_log=tmp_audit)
    nuevos = {}
    for n in narr:
        c = CORRECCIONES.get(n["window_id"])
        if not c:
            continue
        nuevo = dict(n)
        for k in ("analisis_tactico", "narracion_es"):
            if k in c:
                nuevo[k] = c[k]
        aud = mon.audit_call(REQUIRED_MODEL, n["window_id"], {k: nuevo[k] for k in CAMPOS}, 0.0, 0, 0,
                             mode="online")
        if aud["status"] != "PASS":
            tmp_audit.unlink(missing_ok=True)
            print(f"{n['window_id']}: la corrección no pasa M3 → {aud['errors']}. No se guardó nada.")
            return 1
        aud["revision_humana"] = f"{hoy}: {c['motivo']}"
        aud["texto_granite"] = {k: n[k] for k in ("analisis_tactico", "narracion_es")}
        nuevo["revision_humana"] = f"{hoy}: Granite acertó en los datos; se corrigió la redacción ({c['motivo']})"
        nuevos[n["window_id"]] = (nuevo, aud)
    tmp_audit.unlink(missing_ok=True)

    # 2) Guardar: narrations.json y una entrada por corrección al final de la auditoría real
    narr = [nuevos[n["window_id"]][0] if n["window_id"] in nuevos else n for n in narr]
    NARR.write_text(json.dumps(narr, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    with open(AUDIT, "a", encoding="utf-8") as f:
        for _, aud in nuevos.values():
            f.write(json.dumps(aud, ensure_ascii=False, allow_nan=False) + "\n")
    rep = GovernanceMonitorM3(tactical, audit_log=AUDIT).finalize_report(report_path=REPORT, has_credentials=True)
    print(f"Corregidos: {', '.join(nuevos)}. M3: {rep.get('status')}")

    if args.regenerar:
        import run_pipeline as rp
        if rp.run_etapa4().get("status") not in ("PASS", "SKIP"):
            print("Las voces no quedaron en PASS.")
            return 1
        for script in ("scripts/render_post_engine_video.py", "scripts/export_dashboard_data.py",
                       "scripts/export_transmision.py"):
            r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / script)], cwd=ROOT)
            if r.returncode:
                print(f"FALLÓ {script}")
                return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
