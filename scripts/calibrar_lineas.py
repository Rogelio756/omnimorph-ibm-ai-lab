"""
scripts/calibrar_lineas.py
==========================
C1b · Calibración por las líneas blancas de la cancha.

Los puntos que detecta el modelo no caen sobre las líneas reales, aunque traigan confianza
1.00. Aquí cada cuadro se ajusta a las líneas visibles y se propaga con el movimiento de la
cámara (flujo óptico fuera de los jugadores). No usa GPU ni modelos, y no modifica posiciones.

Lee   : el video del partido activo, data/raw/frames.parquet (puntos del cuadro ancla) y
        los recuadros de data/raw/objects.parquet.
Escribe (data/clean/):
  calibracion_lineas.npz  H (n,3,3) imagen -> cancha 12000x7000 cm; valida (n,); cobertura (n,)
  radar_error.json        error medido en el área grande sin usarla para calibrar

Supone una cancha de 105 x 68 m. La cancha del radar (12000 x 7000) es esa misma, escalada:
    x_m = pitch_x * 105 / 12000     y_m = pitch_y * 68 / 7000

Uso: .venv/Scripts/python.exe -X utf8 scripts/calibrar_lineas.py   (unos 4 minutos)
"""

from __future__ import annotations

import json
import pathlib
import sys

import cv2
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from implementacion import partido_config  # noqa: E402
from sports.configs.soccer import SoccerPitchConfiguration  # noqa: E402

CLEAN = ROOT / "data" / "clean"
LARGO, ANCHO = 105.0, 68.0
IMG_W, IMG_H = 1280, 720
ANCLA = 300                    # cuadro con el círculo y la media cancha a la vista
MARCADOR = (30, 0, 540, 80)    # gráfico de TV: x1, y1, x2, y2
A_CONFIG = np.diag([12000 / LARGO, 7000 / ANCHO, 1.0])
ESCALA_IMG = np.array([[640.0, 0, 640], [0, 360, 360], [0, 0, 1]])
ESCALA_CANCHA = np.linalg.inv(
    np.array([[LARGO / 2, 0, LARGO / 2], [0, ANCHO / 2, ANCHO / 2], [0, 0, 1]])
)


def _seg(a, b, n=40):
    return np.linspace(a, b, n)


def _arco(cx, cy, r, a0, a1, n):
    t = np.linspace(a0, a1, n)
    return np.c_[cx + r * np.cos(t), cy + r * np.sin(t)]


def _area(x0, s):
    y1, y2, a = ANCHO / 2 - 20.16, ANCHO / 2 + 20.16, np.arccos(5.5 / 9.15)
    giro = 0 if s > 0 else np.pi
    return [
        _seg((x0 + s * 16.5, y1), (x0 + s * 16.5, y2)),
        _seg((x0, y1), (x0 + s * 16.5, y1), 20),
        _seg((x0, y2), (x0 + s * 16.5, y2), 20),
        _seg((x0 + s * 5.5, ANCHO / 2 - 9.16), (x0 + s * 5.5, ANCHO / 2 + 9.16), 20),
        _seg((x0, ANCHO / 2 - 9.16), (x0 + s * 5.5, ANCHO / 2 - 9.16), 8),
        _seg((x0, ANCHO / 2 + 9.16), (x0 + s * 5.5, ANCHO / 2 + 9.16), 8),
        _arco(x0 + s * 11, ANCHO / 2, 9.15, giro - a, giro + a, 30),
    ]


BASE = np.vstack([
    _seg((LARGO / 2, 0), (LARGO / 2, ANCHO), 70),
    _arco(LARGO / 2, ANCHO / 2, 9.15, 0, 2 * np.pi, 120),
    _seg((0, 0), (LARGO, 0), 105),
    _seg((0, ANCHO), (LARGO, ANCHO), 105),
])
AREAS = np.vstack([
    *_area(0, 1), *_area(LARGO, -1),
    _seg((0, 0), (0, ANCHO), 70), _seg((LARGO, 0), (LARGO, ANCHO), 70),
])
COMPLETO = np.vstack([BASE, AREAS])
REJILLA = np.array([(x, y) for x in np.linspace(0, LARGO, 15) for y in np.linspace(0, ANCHO, 9)])


def proyectar(g, pts):
    h = np.c_[pts, np.ones(len(pts))] @ g.T
    w = np.where(np.abs(h[:, 2]) < 1e-9, 1e-9, h[:, 2])
    return h[:, :2] / w[:, None], w


def dentro(q, w=None, margen=3):
    ok = (q[:, 0] > margen) & (q[:, 0] < IMG_W - margen) & (q[:, 1] > margen) & (q[:, 1] < IMG_H - margen)
    return ok if w is None else ok & (w * np.sign(np.median(w)) > 0)


def mascara_lineas(img, cajas):
    """Píxeles de líneas blancas sobre el pasto, sin jugadores ni marcador."""
    hsv, gris = cv2.cvtColor(img, cv2.COLOR_BGR2HSV), cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pasto = ((hsv[..., 0] > 28) & (hsv[..., 0] < 62) & (hsv[..., 1] > 90)).astype(np.uint8)
    pasto = cv2.morphologyEx(pasto, cv2.MORPH_CLOSE, np.ones((25, 25)))
    n, et, st, _ = cv2.connectedComponentsWithStats(pasto)
    if n > 1:
        pasto = (et == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
    pasto = cv2.erode(pasto, np.ones((3, 3)))
    realce = cv2.morphologyEx(gris, cv2.MORPH_TOPHAT, np.ones((13, 13)))
    m = ((realce > 28) & (hsv[..., 1] < 150) & (pasto > 0)).astype(np.uint8)
    for x1, y1, x2, y2 in cajas:
        m[max(0, int(y1) - 6):int(y2) + 8, max(0, int(x1) - 6):int(x2) + 6] = 0
    x1, y1, x2, y2 = MARCADOR
    m[y1:y2, x1:x2] = 0
    n, et, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    queda = np.zeros(n, bool)
    queda[1:] = np.maximum(st[1:, 2], st[1:, 3]) > 25
    return queda[et].astype(np.uint8)


def distancia(m):
    return cv2.distanceTransform(1 - m, cv2.DIST_L2, 5)


def muestrear(d, q):
    q = np.clip(q, -1e4, 1e4).astype(np.float32)
    return cv2.remap(d, q[:, 0][None], q[:, 1][None], cv2.INTER_LINEAR, borderValue=0)[0]


def refinar(g0, d, modelo, topes, previo=0.0):
    """Acerca las líneas del modelo a las líneas blancas. previo: peso de no alejarse de g0."""
    a0 = np.linalg.inv(ESCALA_IMG) @ g0 @ np.linalg.inv(ESCALA_CANCHA)
    v = (a0 / a0[2, 2]).ravel()[:8]
    q0, w0 = proyectar(g0, REJILLA)
    vis = (
        (w0 * np.sign(np.median(w0)) > 0)
        & (np.abs(q0[:, 0] - 640) < 900) & (np.abs(q0[:, 1] - 360) < 500)
    )

    def g_de(x):
        return ESCALA_IMG @ np.r_[x, 1].reshape(3, 3) @ ESCALA_CANCHA

    for tope in topes:
        idx = np.where(dentro(*proyectar(g_de(v), modelo)))[0]
        if len(idx) < 15:
            break

        def residuos(x):
            q, _ = proyectar(g_de(x), modelo[idx])
            e = np.where(dentro(q, margen=0), np.minimum(muestrear(d, q), tope) / tope, 0.5)
            r = e / np.sqrt(len(idx)) * 10
            if previo > 0 and vis.any():
                qg, _ = proyectar(g_de(x), REJILLA)
                r = np.r_[r, ((qg[vis] - q0[vis]) / tope * previo / np.sqrt(vis.sum())).ravel()]
            return r

        v = least_squares(residuos, v, diff_step=1e-4, max_nfev=60).x
    g = g_de(v)
    q, w = proyectar(g, modelo)
    ok = dentro(q, w)
    return g, float((muestrear(d, q[ok]) < 4).mean()) if ok.sum() > 15 else 0.0


def movimiento(a, b, cajas):
    """Homografía del cuadro a al b, por el fondo. None si hay un corte."""
    m = np.full((IMG_H, IMG_W), 255, np.uint8)
    for x1, y1, x2, y2 in [*cajas, MARCADOR]:
        m[max(0, int(y1) - 5):int(y2) + 5, max(0, int(x1) - 5):int(x2) + 5] = 0
    p = cv2.goodFeaturesToTrack(a, 900, 0.004, 7, mask=m)
    if p is None or len(p) < 12:
        return None
    q, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p, None, winSize=(21, 21), maxLevel=4)
    ok = st.ravel() == 1
    if ok.sum() < 12:
        return None
    h, inl = cv2.findHomography(p[ok], q[ok], cv2.RANSAC, 2.0)
    return h if h is not None and inl.sum() > 12 else None


def ancla_inicial():
    """Cancha (m) -> imagen en el cuadro ancla, con los puntos confiables del modelo."""
    frames = pd.read_parquet(ROOT / "data" / "raw" / "frames.parquet")
    fila = frames.loc[frames.frame == ANCLA].iloc[0] if "frame" in frames else frames.iloc[ANCLA]
    kx, ky, kc = (np.asarray(fila[c], float) for c in ("kp_x", "kp_y", "kp_conf"))
    ok = (kc > 0.5) & (kx > 2) & (kx < IMG_W - 2) & (ky > 2) & (ky < IMG_H - 2)
    vertices = np.array(SoccerPitchConfiguration().vertices, float)[ok]
    h, _ = cv2.findHomography(np.c_[kx, ky][ok], vertices, cv2.RANSAC, 150)
    return np.linalg.inv(np.linalg.inv(A_CONFIG) @ h)


def encadenar(dist, mov, modelo):
    n = len(dist)
    g, cob = [None] * n, np.zeros(n)
    g[ANCLA], cob[ANCLA] = refinar(ancla_inicial(), dist[ANCLA], modelo, (60, 40, 25, 12, 6, 4))
    for k in range(ANCLA + 1, n):
        if mov[k - 1] is None:
            break  # corte de cámara: desde aquí no hay calibración
        g[k], cob[k] = refinar(mov[k - 1] @ g[k - 1], dist[k], modelo, (10, 6, 4), 0.6)
    for k in range(ANCLA - 1, -1, -1):
        if mov[k] is None:
            break
        g[k], cob[k] = refinar(np.linalg.inv(mov[k]) @ g[k + 1], dist[k], modelo, (10, 6, 4), 0.6)
    return g, cob


def error_area(g_sin, g_con, dist):
    """Metros entre el área grande calibrada sin sus líneas y con ellas, donde se ve."""
    errores = []
    for k in range(len(dist)):
        if g_sin[k] is None or g_con[k] is None:
            continue
        q, w = proyectar(g_con[k], AREAS)
        ok = dentro(q, w, 5) & ~((q[:, 1] < MARCADOR[3]) & (q[:, 0] < MARCADOR[2]))
        ok &= muestrear(dist[k], q) < 4  # puntos del área con línea blanca debajo
        if ok.sum() < 20:
            continue
        m, _ = proyectar(np.linalg.inv(g_sin[k]), q[ok])
        errores.append(float(np.median(np.hypot(*(m - AREAS[ok]).T))))
    e = np.array(errores)
    return {
        "mediana_m": round(float(np.median(e)), 1),
        "p90_m": round(float(np.percentile(e, 90)), 1),
        "pct_mayor_5m": int(round(float((e > 5).mean() * 100))),
        "puntos": len(e),
        "cuadros": len(e),
        "metodo": "área grande sin usarla para calibrar",
        "explicacion": (
            "Se calibra sin las líneas del área grande y se mide a cuántos metros queda el área "
            "en los cuadros donde se ve."
        ),
    }


def main() -> int:
    partido = partido_config.activo()
    ruta = ROOT / "data" / "partidos" / partido.id / "partido.config.json"
    config = json.loads(ruta.read_text(encoding="utf-8"))
    cap = cv2.VideoCapture(str(ROOT / config["video"]["archivo"]))
    cuadros = []
    while len(cuadros) < partido.n_frames:
        ok, img = cap.read()
        if not ok:
            break
        cuadros.append(img)
    if len(cuadros) < partido.n_frames:
        print(f"[FALLA] el video tiene {len(cuadros)} cuadros; se esperaban {partido.n_frames}")
        return 1
    objetos = pd.read_parquet(ROOT / "data" / "raw" / "objects.parquet")
    cajas = {
        k: g[["x1", "y1", "x2", "y2"]].values
        for k, g in objetos[objetos.x1.notna()].groupby("frame")
    }
    n = len(cuadros)
    dist = [distancia(mascara_lineas(cuadros[k], cajas.get(k, []))) for k in range(n)]
    grises = [cv2.cvtColor(i, cv2.COLOR_BGR2GRAY) for i in cuadros]
    mov = [movimiento(grises[k], grises[k + 1], cajas.get(k, [])) for k in range(n - 1)]

    g, cob = encadenar(dist, mov, COMPLETO)
    g_sin, _ = encadenar(dist, mov, BASE)
    valida = np.array([x is not None for x in g])
    h = np.array([
        A_CONFIG @ np.linalg.inv(x) if x is not None else np.full((3, 3), np.nan) for x in g
    ])
    h = h / h[:, 2:, 2:]
    np.savez_compressed(CLEAN / "calibracion_lineas.npz", H=h, valida=valida, cobertura=cob)
    error = error_area(g_sin, g, dist)
    (CLEAN / "radar_error.json").write_text(json.dumps(error, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {valida.sum()}/{n} cuadros calibrados; cobertura mediana "
          f"{np.median(cob[valida]):.2f}, mínima {cob[valida].min():.2f}")
    print("[OK] radar_error.json:", json.dumps(error, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
