"""
scripts/animacion_recreacion.py
Recreación animada del clip a partir de los datos de Omnimorph, con el ángulo
de la cámara de TV, sin usar ningún píxel de la transmisión.

Qué usa:
  - data/clean/objects_cleaned.parquet: posición en la cancha de cada jugador,
    árbitro y balón por cuadro (pitch_x_smooth, pitch_y_smooth) y la altura del
    recuadro de detección (para el tamaño de la figura).
  - data/clean/calibracion_lineas.npz: la matriz de cámara H de cada cuadro
    (imagen -> cancha). Su inversa lleva la cancha dibujada a la vista de TV.
  - El audio de MATEO (dashboard/media/NARRACION_COMPLETA_60S.wav), opcional.

Qué no usa: la imagen ni el audio de la transmisión, ni logos.

Uso:
    .venv\\Scripts\\python.exe -X utf8 scripts/animacion_recreacion.py
    .venv\\Scripts\\python.exe -X utf8 scripts/animacion_recreacion.py --sin-audio
Salida (git ignora outputs/): outputs/animacion/recreacion_tv.mp4
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from implementacion import partido_config

CLEAN = ROOT / "data" / "clean"
AUDIO = ROOT / "dashboard" / "media" / "NARRACION_COMPLETA_60S.wav"
OUT_DIR = ROOT / "outputs" / "animacion"

W, H_IMG = 1280, 720
LARGO, ANCHO = 12000.0, 7000.0          # unidades internas de la cancha
MX, MY = LARGO / 105.0, ANCHO / 68.0     # unidades por metro
HUECO_MAX = 10                           # cuadros que se rellenan si un jugador se pierde
FUENTE = pathlib.Path("C:/Windows/Fonts/segoeui.ttf")
FUENTE_B = pathlib.Path("C:/Windows/Fonts/segoeuib.ttf")


def hex_bgr(h: str) -> tuple:
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b, g, r)


def oscurecer(c: tuple, f: float) -> tuple:
    return tuple(int(v * f) for v in c)


# ----------------------------------------------------------------------------- cancha
def lineas_cancha() -> list[np.ndarray]:
    """Polilíneas de la cancha (105 x 68 m) en unidades internas."""
    def m(x, y):
        return (x * MX, y * MY)

    def rect(x0, y0, x1, y1):
        return np.array([m(x0, y0), m(x1, y0), m(x1, y1), m(x0, y1), m(x0, y0)])

    def arco(cx, cy, r, a0, a1, n=48):
        a = np.linspace(np.radians(a0), np.radians(a1), n)
        return np.array([m(cx + r * np.cos(t), cy + r * np.sin(t)) for t in a])

    L = [rect(0, 0, 105, 68), np.array([m(52.5, 0), m(52.5, 68)]), arco(52.5, 34, 9.15, 0, 360, 96)]
    for x0, s in ((0, 1), (105, -1)):
        L.append(rect(x0, 34 - 20.16, x0 + s * 16.5, 34 + 20.16))
        L.append(rect(x0, 34 - 9.16, x0 + s * 5.5, 34 + 9.16))
        L.append(rect(x0, 34 - 3.66, x0 - s * 1.5, 34 + 3.66))          # portería
        # media luna del área (solo la parte fuera del área)
        cx = x0 + s * 11
        ang = np.degrees(np.arccos(5.5 / 9.15))
        L.append(arco(cx, 34, 9.15, -ang, ang) if s == 1 else arco(cx, 34, 9.15, 180 - ang, 180 + ang))
    return L


def puntos_cancha() -> list[tuple]:
    return [(52.5 * MX, 34 * MY), (11 * MX, 34 * MY), (94 * MX, 34 * MY)]


def proyectar(pts: np.ndarray, Hi: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(pts.reshape(-1, 1, 2).astype(np.float64), Hi).reshape(-1, 2)


def dibujar_cancha(img, Hi, LINEAS):
    # fondo: gradiente oscuro (gradas abstractas)
    img[:] = (24, 20, 16)
    # césped con franjas
    n = 14
    for i in range(n):
        x0, x1 = i * LARGO / n, (i + 1) * LARGO / n
        poly = np.array([(x0, -700), (x1, -700), (x1, ANCHO + 700), (x0, ANCHO + 700)])
        if i == 0:
            poly[[0, 3], 0] = -900
        if i == n - 1:
            poly[[1, 2], 0] = LARGO + 900
        col = (52, 118, 48) if i % 2 == 0 else (46, 106, 43)
        cv2.fillPoly(img, [np.round(proyectar(poly, Hi) * 16).astype(np.int32)], col, cv2.LINE_AA, shift=4)
    # líneas
    for pl in LINEAS:
        p = np.round(proyectar(pl, Hi) * 16).astype(np.int32)
        cv2.polylines(img, [p], False, (225, 232, 228), 2, cv2.LINE_AA, shift=4)
    for pt in puntos_cancha():
        q = proyectar(np.array([pt]), Hi)[0]
        cv2.circle(img, (int(q[0]), int(q[1])), 3, (225, 232, 228), -1, cv2.LINE_AA)


def suavizar_camara(Hs: np.ndarray, valida: np.ndarray, ventana: int = 21) -> np.ndarray:
    """Quita el temblor de la cámara: lleva 4 puntos fijos de la imagen a la cancha en
    cada cuadro, suaviza esas trayectorias en el tiempo y rehace la matriz con ellos."""
    from scipy.signal import savgol_filter
    img_pts = np.array([[160, 200], [1120, 200], [1120, 690], [160, 690]], np.float64)
    idx = np.flatnonzero(valida)
    campo = np.array([cv2.perspectiveTransform(img_pts.reshape(-1, 1, 2), Hs[f]).reshape(-1, 2) for f in idx])
    v = min(ventana, len(idx) - (1 - len(idx) % 2))
    campo_s = savgol_filter(campo, v, 2, axis=0, mode="interp")
    out = Hs.copy()
    for k, f in enumerate(idx):
        out[f] = cv2.getPerspectiveTransform(img_pts.astype(np.float32), campo_s[k].astype(np.float32))
    return out


# ----------------------------------------------------------------------------- datos
def preparar(o: pd.DataFrame) -> pd.DataFrame:
    """Una fila por persona y cuadro, con huecos cortos rellenados por interpolación."""
    gente = o[o["class_name"].isin(["player", "referee"])].copy()
    gente["alto"] = gente["y2"] - gente["y1"]
    gente = gente.dropna(subset=["pitch_x_smooth", "pitch_y_smooth"])
    filas = []
    for tid, g in gente.groupby("track_id_stitched"):
        g = g.groupby("frame").agg(
            x=("pitch_x_smooth", "mean"), y=("pitch_y_smooth", "mean"), alto=("alto", "mean"),
            team=("team", lambda s: s.mode().iloc[0] if s.notna().any() else np.nan),
            clase=("class_name", "first"))
        idx = np.arange(g.index.min(), g.index.max() + 1)
        g = g.reindex(idx)
        # solo se rellenan huecos de hasta HUECO_MAX cuadros
        hueco = g["x"].isna()
        grupo = (hueco != hueco.shift()).cumsum()
        largo = hueco.groupby(grupo).transform("sum")
        g[["x", "y", "alto"]] = g[["x", "y", "alto"]].interpolate(limit_area="inside")
        g.loc[hueco & (largo > HUECO_MAX), ["x", "y", "alto"]] = np.nan
        g["alto"] = g["alto"].rolling(9, center=True, min_periods=1).median()
        g[["team", "clase"]] = g[["team", "clase"]].ffill().bfill()
        g["tid"] = tid
        filas.append(g.dropna(subset=["x"]).reset_index(names="frame"))
    return pd.concat(filas, ignore_index=True)


def balon(o: pd.DataFrame) -> pd.DataFrame:
    b = o[o["class_name"] == "ball"].dropna(subset=["pitch_x", "pitch_y"])
    b = b.groupby("frame").agg(x=("pitch_x", "mean"), y=("pitch_y", "mean"))
    idx = np.arange(b.index.min(), b.index.max() + 1)
    b = b.reindex(idx)
    hueco = b["x"].isna()
    grupo = (hueco != hueco.shift()).cumsum()
    largo = hueco.groupby(grupo).transform("sum")
    b = b.interpolate(limit_area="inside")
    b.loc[hueco & (largo > 6), ["x", "y"]] = np.nan
    return b.dropna()


# ----------------------------------------------------------------------------- figuras
def dibujar_figura(img, pie, alto, color):
    x, y = pie
    h = float(np.clip(alto, 18, 140))
    w = h * 0.26
    sombra = (int(w * 1.1), max(2, int(h * 0.07)))
    ov = img.copy()
    cv2.ellipse(ov, (int(x), int(y)), sombra, 0, 0, 360, (10, 30, 10), -1, cv2.LINE_AA)
    cv2.addWeighted(ov, 0.45, img, 0.55, 0, img)
    oscuro = oscurecer(color, 0.55)
    # piernas (short) y torso (camiseta), formas simples
    y_cadera = y - h * 0.45
    y_hombro = y - h * 0.80
    cv2.line(img, (int(x - w * 0.22), int(y)), (int(x - w * 0.18), int(y_cadera)), (30, 30, 30), max(2, int(w * 0.32)), cv2.LINE_AA)
    cv2.line(img, (int(x + w * 0.22), int(y)), (int(x + w * 0.18), int(y_cadera)), (30, 30, 30), max(2, int(w * 0.32)), cv2.LINE_AA)
    cv2.rectangle(img, (int(x - w * 0.42), int(y_cadera - h * 0.04)), (int(x + w * 0.42), int(y_cadera + h * 0.08)), oscuro, -1, cv2.LINE_AA)
    torso = np.array([(x - w * 0.5, y_hombro), (x + w * 0.5, y_hombro),
                      (x + w * 0.42, y_cadera), (x - w * 0.42, y_cadera)])
    cv2.fillPoly(img, [np.round(torso * 16).astype(np.int32)], color, cv2.LINE_AA, shift=4)
    cv2.circle(img, (int(x), int(y_hombro - h * 0.09)), max(2, int(h * 0.085)), oscuro, -1, cv2.LINE_AA)


# ----------------------------------------------------------------------------- textos
class Rotulos:
    def __init__(self, partido):
        self.f = ImageFont.truetype(str(FUENTE), 18)
        self.fb = ImageFont.truetype(str(FUENTE_B), 20)
        self.fs = ImageFont.truetype(str(FUENTE), 15)
        self.partido = partido

    def aplicar(self, img, t: float, equipos):
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert("RGBA")
        capa = Image.new("RGBA", pil.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        # caja superior izquierda: título y equipos
        d.rounded_rectangle((20, 18, 470, 92), 10, fill=(8, 12, 20, 190))
        d.text((34, 26), "OMNIMORPH · recreación con datos", font=self.fb, fill=(245, 245, 245, 255))
        xx = 34
        for nombre, col in equipos:
            d.ellipse((xx, 64, xx + 12, 76), fill=col + (255,))
            d.text((xx + 18, 58), nombre, font=self.f, fill=(225, 225, 225, 255))
            xx += 28 + int(d.textlength(nombre, font=self.f)) + 14
        # reloj
        txt = f"{int(t // 60):02d}:{t % 60:04.1f}"
        d.rounded_rectangle((W - 140, 18, W - 20, 58), 10, fill=(8, 12, 20, 190))
        d.text((W - 124, 24), txt, font=self.fb, fill=(245, 245, 245, 255))
        # aviso inferior
        aviso = ("Animación generada con las posiciones que calcula Omnimorph "
                 "(error mediano ≈ 2.4 m). No es la imagen de la transmisión.")
        tw = d.textlength(aviso, font=self.fs)
        d.rounded_rectangle(((W - tw) / 2 - 14, H_IMG - 44, (W + tw) / 2 + 14, H_IMG - 16), 8, fill=(8, 12, 20, 170))
        d.text(((W - tw) / 2, H_IMG - 41), aviso, font=self.fs, fill=(210, 210, 210, 255))
        out = Image.alpha_composite(pil, capa).convert("RGB")
        return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-audio", action="store_true", help="no mezcla la voz de MATEO")
    ap.add_argument("--hasta", type=int, default=None, help="último cuadro (para pruebas)")
    ap.add_argument("--muestra", type=int, nargs="*", default=None,
                    help="solo guarda PNG de estos cuadros (para revisar)")
    args = ap.parse_args()

    P = partido_config.activo()
    z = np.load(CLEAN / "calibracion_lineas.npz")
    Hs, valida = z["H"], z["valida"]
    Hs = suavizar_camara(Hs, valida)
    o =pd.read_parquet(CLEAN / "objects_cleaned.parquet")
    gente = preparar(o)
    bal = balon(o)
    por_cuadro = {f: g for f, g in gente.groupby("frame")}

    col = {0: hex_bgr(P.equipo(0).color_ui), 1: hex_bgr(P.equipo(1).color_ui)}
    col_arbitro = (40, 200, 230)
    equipos_rot = [(P.equipo(t).nombre, tuple(reversed(col[t]))) for t in (0, 1)]
    rot = Rotulos(P)
    LINEAS = lineas_cancha()

    ultimo = int(np.flatnonzero(valida).max())
    if args.hasta is not None:
        ultimo = min(ultimo, args.hasta)
    fps = P.fps
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cuadros = args.muestra if args.muestra else range(0, ultimo + 1)

    tmp = OUT_DIR / "_sin_audio.mp4"
    vw = None if args.muestra else cv2.VideoWriter(str(tmp), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H_IMG))
    img = np.zeros((H_IMG, W, 3), np.uint8)
    for f in cuadros:
        if not valida[f]:
            continue
        Hi = np.linalg.inv(Hs[f])
        dibujar_cancha(img, Hi, LINEAS)
        figs = []
        g = por_cuadro.get(f)
        if g is not None:
            pie = proyectar(g[["x", "y"]].to_numpy(), Hi)
            for (px, py), alto, team, clase in zip(pie, g["alto"], g["team"], g["clase"]):
                if -60 < px < W + 60 and -20 < py < H_IMG + 160:
                    c = col_arbitro if clase == "referee" or np.isnan(team) else col[int(team)]
                    figs.append((py, px, alto, c))
        for py, px, alto, c in sorted(figs):
            dibujar_figura(img, (px, py), alto, c)
        if f in bal.index:
            q = proyectar(bal.loc[[f], ["x", "y"]].to_numpy(), Hi)[0]
            cv2.ellipse(img, (int(q[0]), int(q[1]) + 2), (6, 2), 0, 0, 360, (10, 30, 10), -1, cv2.LINE_AA)
            cv2.circle(img, (int(q[0]), int(q[1]) - 4), 5, (250, 250, 250), -1, cv2.LINE_AA)
            cv2.circle(img, (int(q[0]), int(q[1]) - 4), 5, (40, 40, 40), 1, cv2.LINE_AA)
        out = rot.aplicar(img, f / fps, equipos_rot)
        if args.muestra:
            cv2.imwrite(str(OUT_DIR / f"muestra_{f:04d}.png"), out)
        else:
            vw.write(out)
    if args.muestra:
        print(f"Muestras en {OUT_DIR.relative_to(ROOT)}")
        return 0
    vw.release()

    final = OUT_DIR / "recreacion_tv.mp4"
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        tmp.replace(final)
        print(f"Sin ffmpeg: video sin recodificar en {final.relative_to(ROOT)}")
        return 0
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp)]
    if not args.sin_audio and AUDIO.exists():
        cmd += ["-i", str(AUDIO), "-c:a", "aac", "-b:a", "160k", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(final)]
    subprocess.run(cmd, check=True)
    tmp.unlink(missing_ok=True)
    print(f"Listo: {final.relative_to(ROOT)} ({final.stat().st_size / 1e6:.1f} MB, {ultimo + 1} cuadros a {fps} fps)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
