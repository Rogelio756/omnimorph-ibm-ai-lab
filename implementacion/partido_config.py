"""
Configuración del partido activo.

Cada partido vive en data/partidos/<id>/partido.config.json. El partido activo
se elige con la variable de entorno OMNIMORPH_PARTIDO o, si no está definida,
con data/partidos/partido_activo.json.

Los team_id 0 y 1 del pipeline se traducen aquí a código, nombre y menciones
válidas de cada equipo, para que engine, narrador, M3 y chatbot no tengan
nombres de selecciones escritos a mano.
"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
PARTIDOS_DIR = ROOT / "data" / "partidos"
ACTIVO_PATH = PARTIDOS_DIR / "partido_activo.json"

# Códigos que usaba el engine antes de la configuración por partido.
# Se aceptan al leer datos viejos: ARG = team_id 0, FRA = team_id 1.
CODIGOS_LEGADOS = {"ARG": 0, "FRA": 1}


@dataclass(frozen=True)
class Equipo:
    team_id: int
    codigo: str
    nombre: str
    menciones: tuple
    ataca_hacia: str  # "+x" (hacia x=12000) o "-x" (hacia x=0)

    @property
    def patron_menciones(self) -> str:
        return r"\b(" + "|".join(self.menciones) + r")\b"


@dataclass(frozen=True)
class Partido:
    id: str
    titulo: str
    competicion: str
    fps: float
    n_frames: int
    video_archivo: str
    video_dataset_id: str
    percepcion_dir: pathlib.Path
    equipos: tuple  # (Equipo team_id 0, Equipo team_id 1)
    datos_dir: pathlib.Path

    def equipo(self, team_id: int) -> Equipo:
        return self.equipos[team_id]

    def equipo_por_codigo(self, codigo: Optional[str]) -> Optional[Equipo]:
        """Devuelve el equipo de un código del engine (actual o legado)."""
        if codigo is None:
            return None
        for e in self.equipos:
            if e.codigo == codigo:
                return e
        if codigo in CODIGOS_LEGADOS:
            return self.equipos[CODIGOS_LEGADOS[codigo]]
        return None

    def nombre_de(self, codigo: Optional[str], neutro: str = "Ninguno") -> str:
        e = self.equipo_por_codigo(codigo)
        return e.nombre if e else neutro


def id_activo() -> str:
    env = os.environ.get("OMNIMORPH_PARTIDO", "").strip()
    if env:
        return env
    with open(ACTIVO_PATH, encoding="utf-8") as f:
        return json.load(f)["activo"]


@lru_cache(maxsize=None)
def cargar(partido_id: Optional[str] = None) -> Partido:
    pid = partido_id or id_activo()
    datos_dir = PARTIDOS_DIR / pid
    cfg_path = datos_dir / "partido.config.json"
    if not cfg_path.exists():
        raise FileNotFoundError(
            f"No existe {cfg_path}. Revisa OMNIMORPH_PARTIDO o {ACTIVO_PATH}."
        )
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    equipos = []
    for tid in (0, 1):
        e = cfg["equipos"][str(tid)]
        if e["ataca_hacia"] not in ("+x", "-x"):
            raise ValueError(f"{cfg_path}: ataca_hacia debe ser '+x' o '-x'")
        equipos.append(Equipo(
            team_id=tid,
            codigo=e["codigo"],
            nombre=e["nombre"],
            menciones=tuple(e["menciones"]),
            ataca_hacia=e["ataca_hacia"],
        ))
    if equipos[0].ataca_hacia == equipos[1].ataca_hacia:
        raise ValueError(f"{cfg_path}: los dos equipos no pueden atacar hacia el mismo lado")

    v = cfg["video"]
    return Partido(
        id=cfg["id"],
        titulo=cfg["titulo"],
        competicion=cfg["competicion"],
        fps=float(v["fps"]),
        n_frames=int(v["n_frames"]),
        video_archivo=v["archivo"],
        video_dataset_id=v.get("dataset_id", pathlib.Path(v["archivo"]).name),
        percepcion_dir=ROOT / cfg["percepcion_dir"],
        equipos=tuple(equipos),
        datos_dir=datos_dir,
    )


def activo() -> Partido:
    return cargar(None)
