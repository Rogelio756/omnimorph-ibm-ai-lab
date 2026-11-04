"""
scripts/restore_clip13_backup.py
================================
Restaura en 1 segundo los artefactos limpios de clip_13 (Brasil vs Alemania)
desde `backups/clip_13_estable/` hacia `data/clean/`, `data/audio/` y `outputs/`.

Uso:
    .\\.venv\\Scripts\\python.exe scripts/restore_clip13_backup.py
"""

from __future__ import annotations

import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backups" / "clip_13_estable"


def main() -> None:
    if not BACKUP_DIR.exists():
        raise FileNotFoundError(f"No existe el respaldo en: {BACKUP_DIR}")

    # 1. Restaurar data/clean
    src_clean = BACKUP_DIR / "clean"
    dst_clean = ROOT / "data" / "clean"
    if src_clean.exists():
        dst_clean.mkdir(parents=True, exist_ok=True)
        for f in src_clean.iterdir():
            if f.is_file():
                shutil.copy2(f, dst_clean / f.name)
        print(f"[OK] Restaurado data/clean/ ({len(list(src_clean.iterdir()))} archivos)")

    # 2. Restaurar data/audio
    src_audio = BACKUP_DIR / "audio"
    dst_audio = ROOT / "data" / "audio"
    if src_audio.exists():
        dst_audio.mkdir(parents=True, exist_ok=True)
        for f in src_audio.iterdir():
            if f.is_file():
                shutil.copy2(f, dst_audio / f.name)
        print(f"[OK] Restaurado data/audio/ ({len(list(src_audio.iterdir()))} archivos)")

    # 3. Restaurar videos H.264 de clip_13
    src_vids = BACKUP_DIR / "videos_clip_13"
    dst_vids = ROOT / "outputs" / "mvp_pruebas" / "mundial_2014_brasil_alemania" / "clip_13"
    if src_vids.exists():
        dst_vids.mkdir(parents=True, exist_ok=True)
        for f in src_vids.iterdir():
            if f.is_file():
                shutil.copy2(f, dst_vids / f.name)
        print(f"[OK] Restaurados videos H.264 en {dst_vids}")


if __name__ == "__main__":
    main()
