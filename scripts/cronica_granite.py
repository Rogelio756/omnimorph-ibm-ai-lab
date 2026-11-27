"""
scripts/cronica_granite.py
Vuelve a escribir la crónica de los 8 tramos con IBM Granite y regenera solo
lo que depende de ella: voces, video con subtítulos y datos de la web.
No toca data/raw, posiciones ni radar.

Pasos:
  1. Respaldo de narrations.json, auditoría M3, monitores y audio en
     backups/pre_m3_<fecha-hora>/ (git ignora backups/).
  2. Narrador + Monitor M3 (Granite; ~1.4 RU con reintentos).
  3. Voces + Monitor M4.
  4. render_post_engine_video.py, export_dashboard_data.py y export_transmision.py.
  5. Imprime las 8 frases (Granite o plantilla) para revisarlas a mano.

Uso (lo corre el usuario, porque usa las credenciales de .env):
    .venv\\Scripts\\python.exe -X utf8 scripts/cronica_granite.py
Para volver al respaldo más reciente:
    .venv\\Scripts\\python.exe -X utf8 scripts/cronica_granite.py --restaurar
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CLEAN = ROOT / "data" / "clean"
AUDIO = ROOT / "data" / "audio"
BACKUPS = ROOT / "backups"
ARCHIVOS = ["narrations.json", "narrations_es.vtt", "governance_audit.jsonl",
            "monitor_m3.json", "monitor_m4.json"]
EXPORTS = ["scripts/render_post_engine_video.py", "scripts/export_dashboard_data.py",
           "scripts/export_transmision.py"]


def respaldar() -> pathlib.Path:
    dest = BACKUPS / f"pre_m3_{dt.datetime.now():%Y-%m-%d_%H%M}"
    (dest / "data_clean").mkdir(parents=True, exist_ok=True)
    for nombre in ARCHIVOS:
        if (CLEAN / nombre).exists():
            shutil.copy2(CLEAN / nombre, dest / "data_clean" / nombre)
    if AUDIO.exists():
        shutil.copytree(AUDIO, dest / "data_audio", dirs_exist_ok=True)
    print(f"Respaldo en {dest.relative_to(ROOT)}")
    return dest


def restaurar() -> int:
    previos = sorted(BACKUPS.glob("pre_m3_*"))
    if not previos:
        print("No hay respaldos pre_m3_* en backups/.")
        return 1
    src = previos[-1]
    for f in (src / "data_clean").iterdir():
        shutil.copy2(f, CLEAN / f.name)
    if (src / "data_audio").exists():
        shutil.copytree(src / "data_audio", AUDIO, dirs_exist_ok=True)
    print(f"Restaurado desde {src.relative_to(ROOT)}. Regenerando la web…")
    return exportar()


def exportar() -> int:
    py = sys.executable
    for script in EXPORTS:
        print(f"\n→ {script}")
        r = subprocess.run([py, "-X", "utf8", str(ROOT / script)], cwd=ROOT)
        if r.returncode != 0:
            print(f"FALLÓ {script} (código {r.returncode})")
            return r.returncode
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restaurar", action="store_true", help="vuelve al respaldo pre_m3 más reciente")
    args = ap.parse_args()
    if args.restaurar:
        return restaurar()

    respaldar()

    import run_pipeline as rp
    r3 = rp.run_etapa3()
    if r3.get("status") != "PASS":
        print("\nM3 no quedó en PASS. Nada más se regeneró; usa --restaurar para volver.")
        return 1
    r4 = rp.run_etapa4()
    if r4.get("status") not in ("PASS", "SKIP"):
        print("\nLas voces no quedaron en PASS; usa --restaurar para volver.")
        return 1
    codigo = exportar()

    narr = json.loads((CLEAN / "narrations.json").read_text(encoding="utf-8"))
    n_granite = sum(1 for n in narr if n.get("mode") != "offline")
    print("\n" + "=" * 78)
    print(f"Crónica: {n_granite} tramos de Granite y {len(narr) - n_granite} de plantilla")
    print("=" * 78)
    for n in narr:
        origen = "plantilla" if n.get("mode") == "offline" else "GRANITE"
        print(f"{n['window_id']} [{origen:9}] {n['narracion_es']}")
    print("\nRevisa a mano cada frase de GRANITE contra el video antes de publicar.")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
