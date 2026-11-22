"""
scripts/probar_transmision.py
=============================
Pruebas automáticas de la página Transmisión.
Acepta --hasta N (1–7, por defecto 7) y corre paso_1()…paso_N() en orden.
Sale con 0 si todos pasan, con 1 si alguno falla.

Uso:
  .venv/Scripts/python.exe scripts/probar_transmision.py --hasta 1
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import os
import pathlib
import socket
import subprocess
import time
import urllib.error
import urllib.request

ROOT   = pathlib.Path(__file__).resolve().parent.parent
PYTHON = sys.executable
SERVE  = str(ROOT / "dashboard" / "serve.py")

_OK    = "\033[32mOK   \033[0m"
_FALLA = "\033[31mFALLA\033[0m"
_SEP   = "─" * 90

resultados: list[tuple[str, bool, str]] = []


def caso(descripcion: str, ok: bool, nota: str = "") -> None:
    resultados.append((descripcion, ok, nota))
    estado = _OK if ok else _FALLA
    print(f"  {estado}  {descripcion}")
    if not ok and nota:
        print(f"         → {nota}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"GET {url}: {e}") from e


def _esperar_servidor(url: str, timeout: float = 20.0) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            code, _ = _get(url)
            if code in (200, 404, 410):
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


class Servidor:
    """Levanta dashboard/serve.py sin modo prueba."""

    def __init__(self) -> None:
        self.proc = None
        self.puerto = _puerto_libre()

    def __enter__(self) -> "Servidor":
        cmd = [PYTHON, SERVE, "--port", str(self.puerto)]
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen(cmd, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        url = f"http://127.0.0.1:{self.puerto}/pages/transmision.html"
        if not _esperar_servidor(url):
            self._terminar()
            raise RuntimeError("El servidor no arrancó a tiempo")
        return self

    def __exit__(self, *_) -> None:
        self._terminar()

    def _terminar(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def url(self, path: str = "") -> str:
        return f"http://127.0.0.1:{self.puerto}{path}"


# ── Paso 1 ────────────────────────────────────────────────────────────────────

def paso_1() -> None:
    print("\nPaso 1 — Exportar datos")
    export_py  = ROOT / "scripts" / "export_transmision.py"
    out_json   = ROOT / "dashboard" / "data" / "transmision.json"
    mateo_json = ROOT / "dashboard" / "data" / "mateo_data.json"

    # 1.1: ejecutar dos veces → sha256 idéntico, ambas salen 0
    ok = True
    nota = ""
    try:
        r1 = subprocess.run([PYTHON, str(export_py)], capture_output=True, timeout=120)
        sha1 = _sha256(out_json)
        r2 = subprocess.run([PYTHON, str(export_py)], capture_output=True, timeout=120)
        sha2 = _sha256(out_json)
        ok = r1.returncode == 0 and r2.returncode == 0 and sha1 == sha2
        if not ok:
            nota = f"rc1={r1.returncode} rc2={r2.returncode} sha_igual={sha1 == sha2}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.1 Dos ejecuciones → exit 0 y sha256 idéntico", ok, nota)

    # Cargar los JSON para los casos siguientes
    d, m = {}, {}
    try:
        with open(out_json, encoding="utf-8") as f:
            d = json.load(f)
        with open(mateo_json, encoding="utf-8") as f:
            m = json.load(f)
    except Exception as e:
        caso("1.2 version==1; len(cuadros)==len(cancha)==len(balon)==n_frames", False, str(e))
        caso("1.3 Cajas de 5 elementos; balon bien formado", False, str(e))
        caso("1.4 Protagonista W0==1 con frames_cerca>=15", False, str(e))
        caso("1.5 len(jugadas)==len(windows); textos idénticos", False, str(e))
        caso("1.6 reloj_inicio_s==63 y marcador==[0,0]", False, str(e))
        caso("1.7 Etiquetas correctas para id 6 e id 1", False, str(e))
        caso("1.8 Archivo < 3 000 000 bytes", False, str(e))
        caso("1.9 ficha correcta y sin 'kmh' en el archivo", False, str(e))
        return

    n = m["meta"]["n_frames"]

    # 1.2: version, longitudes
    ok = True
    nota = ""
    try:
        ok = (d["version"] == 1
              and len(d["cuadros"]) == n
              and len(d["cancha"]) == n
              and len(d["balon"]) == n
              and d["video"]["n_frames"] == n)
        if not ok:
            nota = (f"version={d['version']} cuadros={len(d['cuadros'])} "
                    f"cancha={len(d['cancha'])} balon={len(d['balon'])} n_frames={n}")
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.2 version==1; len(cuadros)==len(cancha)==len(balon)==n_frames", ok, nota)

    # 1.3: cajas de 5 elementos; balon bien formado
    ok = True
    nota = ""
    try:
        for fi, frame in enumerate(d["cuadros"]):
            for ci, caja in enumerate(frame):
                if len(caja) != 5:
                    ok = False
                    nota = f"cuadro {fi} caja {ci} tiene {len(caja)} elementos (esperado 5)"
                    break
            if not ok:
                break
        if ok:
            for fi, b in enumerate(d["balon"]):
                if b is None:
                    continue
                if (not isinstance(b, list) or len(b) != 2
                        or not (0 <= b[0] <= 1279) or not (0 <= b[1] <= 719)):
                    ok = False
                    nota = f"balon[{fi}] = {b!r} mal formado"
                    break
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.3 Cajas de 5 elementos; balon bien formado", ok, nota)

    # 1.4: todo id en jugadores; protagonista W0==1 con frames_cerca>=15
    ok = True
    nota = ""
    try:
        ids_j = set(d["jugadores"].keys())
        ids_mal = set()
        for frame in d["cuadros"]:
            for c in frame:
                if str(c[0]) not in ids_j:
                    ids_mal.add(str(c[0]))
        for j in d["jugadas"]:
            p = j.get("protagonista")
            if p is not None and str(p) not in ids_j:
                ids_mal.add(str(p))
        if ids_mal:
            ok = False
            nota = f"ids no en jugadores: {ids_mal}"
        if ok:
            # Verificar protagonista de W0 y frames_cerca >= 15
            j0 = d["jugadas"][0]
            ok = (j0["protagonista"] == 1 and j0["frames_cerca"] >= 15)
            if not ok:
                nota = (f"W0 protagonista={j0['protagonista']} "
                        f"frames_cerca={j0['frames_cerca']}")
            # Verificar que toda jugada con protagonista tiene frames_cerca >= 15
            if ok:
                for j in d["jugadas"]:
                    if j["protagonista"] is not None and j["frames_cerca"] < 15:
                        ok = False
                        nota = (f"{j['id']}: protagonista no nulo pero "
                                f"frames_cerca={j['frames_cerca']}")
                        break
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.4 Protagonista W0==1 con frames_cerca>=15", ok, nota)

    # 1.5: len(jugadas)==len(windows); texto==narration
    ok = True
    nota = ""
    try:
        windows = m["windows"]
        ok = len(d["jugadas"]) == len(windows)
        if ok:
            for j, w in zip(d["jugadas"], windows):
                if j["texto"] != w["narration"]:
                    ok = False
                    nota = f"jugada {j['id']}: texto no coincide"
                    break
        else:
            nota = f"len jugadas={len(d['jugadas'])} len windows={len(windows)}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.5 len(jugadas)==len(windows); textos idénticos", ok, nota)

    # 1.6: reloj_inicio_s==63 y marcador==[0,0]
    ok = True
    nota = ""
    try:
        ok = (d["partido"]["reloj_inicio_s"] == 63
              and d["partido"]["marcador"] == [0, 0])
        if not ok:
            nota = (f"reloj_inicio_s={d['partido']['reloj_inicio_s']} "
                    f"marcador={d['partido']['marcador']}")
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.6 reloj_inicio_s==63 y marcador==[0,0]", ok, nota)

    # 1.7: etiquetas correctas
    ok = True
    nota = ""
    try:
        e6 = d["jugadores"]["6"]["etiqueta"]
        e1 = d["jugadores"]["1"]["etiqueta"]
        ok = e6 == "14 · Galo" and e1 == "11 · Rogers"
        if ok:
            for pid, pdata in d["jugadores"].items():
                et = pdata["etiqueta"]
                if not (et[0].isdigit() or et.startswith("#") or et == "Árbitro"
                        or et.startswith("Jugador ")):
                    ok = False
                    nota = f"jugador {pid} tiene etiqueta inesperada: {et!r}"
                    break
        else:
            nota = f"e6={e6!r} e1={e1!r}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.7 Etiquetas: '14 · Galo' para id 6, '11 · Rogers' para id 1", ok, nota)

    # 1.8: tamaño < 3 000 000 bytes
    ok = True
    nota = ""
    try:
        n_bytes = out_json.stat().st_size
        ok = n_bytes < 3_000_000
        if not ok:
            nota = f"bytes={n_bytes}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.8 Archivo < 3 000 000 bytes", ok, nota)

    # 1.9: ficha correcta y sin "kmh" en el archivo
    ok = True
    nota = ""
    try:
        ficha_esperada = {
            "estadio": "Estadio Nacional de Costa Rica",
            "asistencia": 15700,
            "local":  {"esquema": "3-4-2-1", "entrenador": "Gustavo Alfaro"},
            "visita": {"esquema": "5-4-1",   "entrenador": "Francisco Molina"},
        }
        ok = d.get("ficha") == ficha_esperada
        if ok:
            contenido = out_json.read_text(encoding="utf-8")
            ok = "kmh" not in contenido
            if not ok:
                nota = "la cadena 'kmh' aparece en el archivo"
        else:
            nota = f"ficha={d.get('ficha')!r}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("1.9 ficha correcta y sin 'kmh' en el archivo", ok, nota)


# ── Paso 2 ────────────────────────────────────────────────────────────────────

def paso_2() -> None:
    print("\nPaso 2 — Lógica base (Node)")
    logica_js = ROOT / "dashboard" / "components" / "transmision-logica.js"
    test_js   = ROOT / "scripts" / "probar_transmision_logica.js"

    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", "--check", str(logica_js)],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = r.stderr.decode("utf-8", errors="replace")[:200]
    except Exception as e:
        ok, nota = False, str(e)
    caso("2.1 node --check transmision-logica.js → exit 0", ok, nota)

    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", str(test_js), "--hasta", "2"],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = (r.stdout.decode("utf-8", errors="replace")
                    + r.stderr.decode("utf-8", errors="replace"))[:300]
    except Exception as e:
        ok, nota = False, str(e)
    caso("2.2 node probar_transmision_logica.js --hasta 2 → exit 0", ok, nota)


# ── Paso 3 ────────────────────────────────────────────────────────────────────

def paso_3() -> None:
    print("\nPaso 3 — Página base (servidor)")
    transmision_js  = ROOT / "dashboard" / "components" / "transmision.js"
    transmision_css = ROOT / "dashboard" / "styles" / "components" / "transmision.css"

    # 3.1: node --check transmision.js
    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", "--check", str(transmision_js)],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = r.stderr.decode("utf-8", errors="replace")[:200]
    except Exception as e:
        ok, nota = False, str(e)
    caso("3.1 node --check transmision.js → exit 0", ok, nota)

    # 3.2: transmision.css sin box-shadow ni gradient
    ok = True
    nota = ""
    try:
        css = transmision_css.read_text(encoding="utf-8")
        ok = "box-shadow" not in css and "gradient" not in css
        if not ok:
            nota = f"box-shadow={'box-shadow' in css} gradient={'gradient' in css}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("3.2 transmision.css sin box-shadow ni gradient", ok, nota)

    ids_requeridos = [
        "tv", "tv-video", "tv-marcador", "tv-inicio",
        "tv-protagonista", "tv-trazos",
        "tv-radar", "tv-ficha", "tv-mateo", "tv-voz", "data-error",
    ]
    rutas = [
        "/data/transmision.json",
        "/components/transmision.js",
        "/components/transmision-logica.js",
        "/styles/components/transmision.css",
    ]

    try:
        with Servidor() as srv:
            # 3.3: transmision.html → 200 con todos los ids
            ok = True
            nota = ""
            try:
                code, body = _get(srv.url("/pages/transmision.html"))
                html = body.decode("utf-8", errors="replace")
                faltantes = [i for i in ids_requeridos if f'id="{i}"' not in html]
                ok = code == 200 and len(faltantes) == 0
                if not ok:
                    nota = f"code={code} faltantes={faltantes}"
            except Exception as e:
                ok, nota = False, str(e)
            caso("3.3 GET /pages/transmision.html → 200 con todos los ids", ok, nota)

            # 3.4: archivos estáticos → 200
            ok = True
            nota = ""
            try:
                for ruta in rutas:
                    code, _ = _get(srv.url(ruta))
                    if code != 200:
                        ok = False
                        nota = f"{ruta} → {code}"
                        break
            except Exception as e:
                ok, nota = False, str(e)
            caso("3.4 JSON, JS y CSS sirven con 200", ok, nota)

    except RuntimeError as e:
        caso("3.3 GET /pages/transmision.html → 200 con todos los ids", False, str(e))
        caso("3.4 JSON, JS y CSS sirven con 200", False, str(e))


# ── Paso 4 ────────────────────────────────────────────────────────────────────

def paso_4() -> None:
    print("\nPaso 4 — Protagonista, triángulo y estela")
    test_js   = ROOT / "scripts" / "probar_transmision_logica.js"
    logica_js = ROOT / "dashboard" / "components" / "transmision-logica.js"
    trans_js  = ROOT / "dashboard" / "components" / "transmision.js"
    out_json  = ROOT / "dashboard" / "data" / "transmision.json"

    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", str(test_js), "--hasta", "4"],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = (r.stdout.decode("utf-8", errors="replace")
                    + r.stderr.decode("utf-8", errors="replace"))[:300]
    except Exception as e:
        ok, nota = False, str(e)
    caso("4.1 probar_transmision_logica.js --hasta 4 → exit 0", ok, nota)

    for js in (logica_js, trans_js):
        ok = True
        nota = ""
        try:
            r = subprocess.run(["node", "--check", str(js)],
                               capture_output=True, timeout=15)
            ok = r.returncode == 0
            if not ok:
                nota = r.stderr.decode("utf-8", errors="replace")[:200]
        except Exception as e:
            ok, nota = False, str(e)
        caso(f"4.2 node --check {js.name} → exit 0", ok, nota)

    # 4.3: cada protagonista presente en su jugada
    ok = True
    nota = ""
    try:
        with open(out_json, encoding="utf-8") as f:
            d = json.load(f)
        for j in d["jugadas"]:
            prot = j.get("protagonista")
            if prot is None:
                continue
            f0, f1 = int(j["f0"]), int(j["f1"])
            encontrado = any(
                any(c[0] == prot for c in d["cuadros"][fr])
                for fr in range(f0, min(f1 + 1, len(d["cuadros"])))
            )
            if not encontrado:
                ok = False
                nota = f"protagonista {prot} de {j['id']} no aparece entre f{f0} y f{f1}"
                break
    except Exception as e:
        ok, nota = False, str(e)
    caso("4.3 Cada protagonista presente en su jugada", ok, nota)


# ── Paso 5 ────────────────────────────────────────────────────────────────────

def paso_5() -> None:
    print("\nPaso 5 — Mini radar y alineaciones")
    test_js   = ROOT / "scripts" / "probar_transmision_logica.js"
    logica_js = ROOT / "dashboard" / "components" / "transmision-logica.js"
    trans_js  = ROOT / "dashboard" / "components" / "transmision.js"

    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", str(test_js), "--hasta", "5"],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = (r.stdout.decode("utf-8", errors="replace")
                    + r.stderr.decode("utf-8", errors="replace"))[:300]
    except Exception as e:
        ok, nota = False, str(e)
    caso("5.1 probar_transmision_logica.js --hasta 5 → exit 0", ok, nota)

    for js in (logica_js, trans_js):
        ok = True
        nota = ""
        try:
            r = subprocess.run(["node", "--check", str(js)],
                               capture_output=True, timeout=15)
            ok = r.returncode == 0
            if not ok:
                nota = r.stderr.decode("utf-8", errors="replace")[:200]
        except Exception as e:
            ok, nota = False, str(e)
        caso(f"5.2 node --check {js.name} → exit 0", ok, nota)


# ── Paso 6 ────────────────────────────────────────────────────────────────────

def paso_6() -> None:
    print("\nPaso 6 — Voz de MATEO")
    test_js   = ROOT / "scripts" / "probar_transmision_logica.js"
    logica_js = ROOT / "dashboard" / "components" / "transmision-logica.js"
    trans_js  = ROOT / "dashboard" / "components" / "transmision.js"
    html      = ROOT / "dashboard" / "pages" / "transmision.html"

    ok = True
    nota = ""
    try:
        r = subprocess.run(["node", str(test_js), "--hasta", "6"],
                           capture_output=True, timeout=15)
        ok = r.returncode == 0
        if not ok:
            nota = (r.stdout.decode("utf-8", errors="replace")
                    + r.stderr.decode("utf-8", errors="replace"))[:300]
    except Exception as e:
        ok, nota = False, str(e)
    caso("6.1 probar_transmision_logica.js --hasta 6 → exit 0", ok, nota)

    for js in (logica_js, trans_js):
        ok = True
        nota = ""
        try:
            r = subprocess.run(["node", "--check", str(js)],
                               capture_output=True, timeout=15)
            ok = r.returncode == 0
            if not ok:
                nota = r.stderr.decode("utf-8", errors="replace")[:200]
        except Exception as e:
            ok, nota = False, str(e)
        caso(f"6.2 node --check {js.name} → exit 0", ok, nota)

    # 6.3: transmision.html tiene aria-live="polite"
    ok = True
    nota = ""
    try:
        contenido = html.read_text(encoding="utf-8")
        ok = 'aria-live="polite"' in contenido
        if not ok:
            nota = "aria-live='polite' no encontrado en transmision.html"
    except Exception as e:
        ok, nota = False, str(e)
    caso('6.3 transmision.html contiene aria-live="polite"', ok, nota)


# ── Paso 7 ────────────────────────────────────────────────────────────────────

def paso_7() -> None:
    print("\nPaso 7 — Menú y regresión")
    nav_js = ROOT / "dashboard" / "components" / "site-nav.js"

    # 7.1: site-nav.js contiene las 5 entradas en orden correcto
    ok = True
    nota = ""
    try:
        contenido = nav_js.read_text(encoding="utf-8")
        tiene_trans = "'Transmisión', 'transmision.html'" in contenido
        orden_ok = all(
            contenido.index(e) < contenido.index("'Transmisión'")
            for e in ("'Inicio'", "'MATEO'", "'Partido'", "'Método'")
        )
        ok = tiene_trans and orden_ok
        if not ok:
            nota = f"tiene_transmision={tiene_trans} orden_original_ok={orden_ok}"
    except Exception as e:
        ok, nota = False, str(e)
    caso("7.1 site-nav.js contiene las 5 entradas en orden", ok, nota)

    # 7.2: todas las páginas responden 200
    paginas = [
        "/pages/index.html",
        "/pages/mateo.html",
        "/pages/partido.html",
        "/pages/metodo.html",
        "/pages/operaciones.html",
        "/pages/opinion.html",
        "/pages/transmision.html",
    ]
    try:
        with Servidor() as srv:
            ok = True
            nota = ""
            try:
                for ruta in paginas:
                    code, _ = _get(srv.url(ruta))
                    if code != 200:
                        ok = False
                        nota = f"{ruta} → {code}"
                        break
            except Exception as e:
                ok, nota = False, str(e)
            caso("7.2 Las 7 páginas responden 200", ok, nota)
    except RuntimeError as e:
        caso("7.2 Las 7 páginas responden 200", False, str(e))

    # 7.3: serve.py y mateo_data.json sin cambios respecto al paso 1
    ok = True
    nota = ""
    try:
        r = subprocess.run(
            ["git", "diff", "--quiet", "step-01-exportar-datos", "--",
             "dashboard/serve.py", "dashboard/data/mateo_data.json"],
            cwd=str(ROOT), capture_output=True, timeout=15,
        )
        ok = r.returncode == 0
        if not ok:
            nota = "serve.py o mateo_data.json cambiaron respecto a step-01"
    except Exception as e:
        ok, nota = False, str(e)
    caso("7.3 serve.py y mateo_data.json sin cambios desde paso 1", ok, nota)

    # 7.4: probar_modo_prueba.py pasa sus 15 casos
    ok = True
    nota = ""
    try:
        r = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "probar_modo_prueba.py")],
            capture_output=True, timeout=120,
        )
        ok = r.returncode == 0
        if not ok:
            salida = r.stdout.decode("utf-8", errors="replace")
            nota = salida[-400:] if len(salida) > 400 else salida
    except Exception as e:
        ok, nota = False, str(e)
    caso("7.4 probar_modo_prueba.py → exit 0", ok, nota)


# ── Main ──────────────────────────────────────────────────────────────────────

PASOS = [paso_1, paso_2, paso_3, paso_4, paso_5, paso_6, paso_7]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hasta", type=int, default=7,
                    help="Correr pasos 1…N (1–7, por defecto 7)")
    args = ap.parse_args()
    n = max(1, min(7, args.hasta))

    print(_SEP)
    print(f"Transmisión — pruebas 1…{n}")
    print(_SEP)

    for paso_fn in PASOS[:n]:
        paso_fn()

    print()
    print(_SEP)
    fallos = sum(1 for _, ok, _ in resultados if not ok)
    total  = len(resultados)
    print(f"Resultado: {total - fallos}/{total} OK", end="")
    if fallos:
        print(f"  ---  {fallos} FALLA(S)")
        sys.exit(1)
    else:
        print("  OK Todo correcto")
        sys.exit(0)


if __name__ == "__main__":
    main()
