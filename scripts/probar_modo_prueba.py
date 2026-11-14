"""
scripts/probar_modo_prueba.py
=============================
Comprueba el modo prueba de dashboard/serve.py en 15 casos, sin llamar a watsonx.

Levanta el servidor en un puerto libre con --prueba-horas, archivos de estado y
opiniones temporales, y --chat-falso (Granite simulado). Simula el paso del tiempo
escribiendo un fin ya pasado en el archivo de estado para los casos de prueba vencida.

Casos:
  1  Sin --prueba-horas       /api/prueba/estado → activa: false
  2  Primer arranque 48 h     fin = inicio + 48 h (dentro del rango)
  3  Reinicio                 fin no cambia
  4  Pregunta por regla       no cuenta (contadores siguen en 0)
  5  Tope alcanzado           tercera pregunta Granite da 429 con --tope-chat 2
  6  Otra persona (cookie)    contador propio, no bloqueada
  7  Prueba vencida           GET index.html → 410; POST /api/chat → 410
  8  /api/operaciones/ibm     → 404 en modo prueba
  9  /data/                   → sin listado (403)
  10 /../.env y /%2e%2e/.env  → no devuelven .env
  11 POST /api/opinion válido → 201 + línea nueva en opiniones
  12 Opinión con escala 7     → 400 sin escribir nada
  13 Cuarta opinión           → 429
  14 /api/opinion sin prueba o con prueba vencida → 404 / 410
  15 resumen_opiniones.py     → imprime sin error
"""

from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import pathlib
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).parent.parent
SERVE = str(ROOT / "dashboard" / "serve.py")
PYTHON = sys.executable

# ── Colores ───────────────────────────────────────────────────────────────────
_OK   = "\033[32mOK   \033[0m"
_FALLA = "\033[31mFALLA\033[0m"
_SEP  = "─" * 90

# ── Helpers HTTP ──────────────────────────────────────────────────────────────

def _puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _get(url: str, headers: dict | None = None) -> tuple[int, bytes, dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)
    except urllib.error.URLError as e:
        raise RuntimeError(f"GET {url}: {e}") from e


def _post(url: str, cuerpo: dict, headers: dict | None = None, cookie: str | None = None) -> tuple[int, dict, str | None]:
    hdrs = {"Content-Type": "application/json; charset=utf-8"}
    if headers:
        hdrs.update(headers)
    if cookie:
        hdrs["Cookie"] = f"om_prueba={cookie}"
    datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=datos, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp_body = json.loads(r.read().decode("utf-8"))
            new_cookie = None
            sc = r.headers.get("Set-Cookie", "")
            if "om_prueba=" in sc:
                for parte in sc.split(";"):
                    if parte.strip().startswith("om_prueba="):
                        new_cookie = parte.strip()[len("om_prueba="):]
                        break
            return r.status, resp_body, new_cookie
    except urllib.error.HTTPError as e:
        resp_body = {}
        try:
            resp_body = json.loads(e.read().decode("utf-8"))
        except Exception:
            pass
        return e.code, resp_body, None


def _esperar_listo(url_estado: str, timeout: float = 20.0) -> bool:
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            code, body, _ = _get(url_estado)
            data = json.loads(body)
            if data.get("estado") in ("listo", "no_disponible"):
                return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


class Servidor:
    """Context manager que levanta serve.py como subproceso."""

    def __init__(self, args: list[str]) -> None:
        self.args = args
        self.proc = None
        self.puerto = _puerto_libre()

    def __enter__(self):
        cmd = [
            PYTHON, SERVE,
            "--port", str(self.puerto),
            *self.args,
        ]
        env = {**os.environ, "MATEO_QUIET": "1", "PYTHONIOENCODING": "utf-8"}
        self.proc = subprocess.Popen(
            cmd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        url_estado = f"http://127.0.0.1:{self.puerto}/api/chat/estado"
        if not _esperar_listo(url_estado):
            self._terminar()
            raise RuntimeError("El servidor no arrancó a tiempo")
        return self

    def __exit__(self, *_):
        self._terminar()

    def _terminar(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def url(self, path: str = "") -> str:
        return f"http://127.0.0.1:{self.puerto}{path}"


# ── Resultados ────────────────────────────────────────────────────────────────

resultados: list[tuple[int, str, bool, str]] = []


def caso(num: int, descripcion: str, ok: bool, nota: str = "") -> None:
    resultados.append((num, descripcion, ok, nota))
    estado = _OK if ok else _FALLA
    print(f"{num:>3}  {estado}  {descripcion}")
    if not ok:
        print(f"     {'':7}  → {nota}")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_sin_prueba_horas():
    """Caso 1: Sin --prueba-horas → /api/prueba/estado activa: false."""
    with Servidor([]) as srv:
        code, body, _ = _get(srv.url("/api/prueba/estado"))
        try:
            data = json.loads(body)
            ok = code == 200 and data.get("activa") == False
            nota = "" if ok else f"status={code} body={data}"
        except Exception as e:
            ok, nota = False, str(e)
    caso(1, "Sin --prueba-horas → /api/prueba/estado activa: false", ok, nota)


def test_primer_arranque(estado_tmp: str):
    """Caso 2: Primer arranque 48 h → fin = inicio + 48 h (aproximado)."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)

    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", estado_tmp + ".ops.jsonl",
            "--chat-falso"]
    with Servidor(args) as srv:
        code, body, _ = _get(srv.url("/api/prueba/estado"))
        try:
            data = json.loads(body)
            ok1 = code == 200 and data.get("activa") == True
            fin_iso = data.get("fin", "")
            fin_dt = datetime.fromisoformat(fin_iso)
            if fin_dt.tzinfo is None:
                fin_dt = fin_dt.replace(tzinfo=timezone.utc)
            ahora = datetime.now(tz=timezone.utc)
            # fin debe ser ~48 h desde ahora (tolerancia ±10 min)
            diff = (fin_dt - ahora).total_seconds()
            ok2 = 47 * 3600 < diff < 49 * 3600
            ok = ok1 and ok2
            nota = "" if ok else f"activa={data.get('activa')} diff_h={diff/3600:.2f}"
        except Exception as e:
            ok, nota = False, str(e)
    caso(2, "Primer arranque 48 h → fin = inicio + 48 h", ok, nota)
    return fin_iso   # guardar para caso 3


def test_reinicio(estado_tmp: str, fin_original: str):
    """Caso 3: Reinicio → fin no cambia."""
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", estado_tmp + ".ops.jsonl",
            "--chat-falso"]
    with Servidor(args) as srv:
        code, body, _ = _get(srv.url("/api/prueba/estado"))
        try:
            data = json.loads(body)
            ok = code == 200 and data.get("fin") == fin_original
            nota = "" if ok else f"fin_original={fin_original!r} fin_nuevo={data.get('fin')!r}"
        except Exception as e:
            ok, nota = False, str(e)
    caso(3, "Reinicio → fin no cambia", ok, nota)


def test_regla_no_cuenta(estado_tmp: str, ops_tmp: str):
    """Caso 4: Pregunta por regla no cuenta para el tope."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "2",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    with Servidor(args) as srv:
        # Pregunta que va por regla: «¿Qué tarjetas hubo?»
        code, data, cookie = _post(srv.url("/api/chat"), {"pregunta": "¿Qué tarjetas hubo?"})
        try:
            # Verificar que no consume el tope: origen debe ser regla
            origen = data.get("origen", "")
            ok = code == 200 and origen == "regla"
            # Verificar que el contador sigue en 0 leyendo /api/prueba/estado
            code2, body2, _ = _get(srv.url("/api/prueba/estado"),
                                   headers={"Cookie": f"om_prueba={cookie}"} if cookie else {})
            data2 = json.loads(body2)
            # restantes debe seguir siendo 2 (no se consumió nada)
            restantes = data2.get("restantes", -1)
            ok2 = restantes == 2
            ok = ok and ok2
            nota = "" if ok else f"origen={origen!r} restantes={restantes}"
        except Exception as e:
            ok, nota = False, str(e)
    caso(4, "Pregunta por regla no cuenta para el tope", ok, nota)
    return cookie


def test_tope_alcanzado(estado_tmp: str, ops_tmp: str):
    """Caso 5: Tope alcanzado → tercera pregunta da 429."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "2",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        cookie = None
        try:
            # Dos preguntas que van a Granite (chat falso)
            for _ in range(2):
                code, data, new_cookie = _post(
                    srv.url("/api/chat"),
                    {"pregunta": "¿Quién ganó el partido?"},
                    cookie=cookie,
                )
                if new_cookie:
                    cookie = new_cookie
            # Tercera pregunta debe dar 429
            code3, data3, _ = _post(
                srv.url("/api/chat"),
                {"pregunta": "¿Quién ganó el partido?"},
                cookie=cookie,
            )
            ok = code3 == 429 and data3.get("error") == "tope_alcanzado"
            nota = "" if ok else f"status={code3} data={data3}"
        except Exception as e:
            nota = str(e)
    caso(5, "Tope alcanzado → tercera pregunta Granite da 429", ok, nota)
    return cookie   # cookie que ya tiene el tope


def test_otra_persona(estado_tmp: str, ops_tmp: str, cookie_llena: str | None):
    """Caso 6: Otra persona (otra cookie) tiene su propio contador."""
    # El estado ya tiene al menos una persona con contador = 2 (del caso 5)
    args = ["--prueba-horas", "48", "--tope-chat", "2",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            # Nueva persona (sin cookie) → debe responder 200
            code, data, nueva_cookie = _post(
                srv.url("/api/chat"),
                {"pregunta": "¿Quién ganó el partido?"},
            )
            ok = code == 200 and nueva_cookie is not None and nueva_cookie != cookie_llena
            nota = "" if ok else f"status={code} nueva_cookie={nueva_cookie!r}"
        except Exception as e:
            nota = str(e)
    caso(6, "Otra persona (otra cookie) tiene su propio contador", ok, nota)


def _vencer_prueba(estado_tmp: str) -> None:
    """Escribe un fin ya pasado en el archivo de estado para simular prueba vencida."""
    with open(estado_tmp, encoding="utf-8") as f:
        est = json.load(f)
    fin_pasado = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    est["fin"] = fin_pasado
    with open(estado_tmp, "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=2)


def test_prueba_vencida(estado_tmp: str, ops_tmp: str):
    """Caso 7: Prueba vencida → GET index.html da 410; POST /api/chat da 410."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "1", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            # Vencer la prueba
            _vencer_prueba(estado_tmp)
            time.sleep(0.1)   # dar tiempo al servidor a que relea (no lo hace; el estado lo lee en cada request)

            # GET página HTML → 410
            code_html, body_html, _ = _get(srv.url("/pages/index.html"))
            # POST /api/chat → 410
            code_chat, data_chat, _ = _post(srv.url("/api/chat"), {"pregunta": "¿Hola?"})
            ok = (code_html == 410 and code_chat == 410
                  and data_chat.get("error") == "prueba_terminada")
            nota = "" if ok else f"html={code_html} chat={code_chat} data={data_chat}"
        except Exception as e:
            nota = str(e)
    caso(7, "Prueba vencida → GET html 410; POST /api/chat 410", ok, nota)


def test_operaciones_ibm(estado_tmp: str, ops_tmp: str):
    """Caso 8: /api/operaciones/ibm en modo prueba → 404."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            code, body, _ = _get(srv.url("/api/operaciones/ibm"))
            data = json.loads(body)
            ok = code == 404 and "prueba" in data.get("error", "")
            nota = "" if ok else f"status={code} data={data}"
        except Exception as e:
            nota = str(e)
    caso(8, "/api/operaciones/ibm en modo prueba → 404", ok, nota)


def test_listado_carpetas(estado_tmp: str, ops_tmp: str):
    """Caso 9: /data/ → sin listado de carpetas (403)."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            code, body, _ = _get(srv.url("/data/"))
            # Debe ser 403 (bloqueado por nuestro código) o 404 (carpeta no existe bajo dashboard/)
            # En ningún caso debe devolver un listado HTML con archivos
            contenido = body.decode("utf-8", errors="replace").lower()
            tiene_listado = "<a href=" in contenido and "index of" in contenido
            ok = not tiene_listado and code in (403, 404)
            nota = "" if ok else f"status={code} tiene_listado={tiene_listado}"
        except Exception as e:
            nota = str(e)
    caso(9, "/data/ → sin listado de carpetas", ok, nota)


def test_path_traversal(estado_tmp: str, ops_tmp: str):
    """Caso 10: /../.env y /%2e%2e/.env no devuelven el contenido de .env."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            rutas_peligrosas = ["/../.env", "/%2e%2e/.env"]
            for ruta in rutas_peligrosas:
                code, body, _ = _get(srv.url(ruta))
                contenido = body.decode("utf-8", errors="replace")
                # Si devuelve el .env, contendrá API_KEY o algo similar
                if "API_KEY" in contenido or "WATSONX" in contenido:
                    ok = False
                    nota = f"ruta {ruta!r} devolvió contenido de .env!"
                    caso(10, "/../.env y /%2e%2e/.env no devuelven .env", ok, nota)
                    return
            ok = True
        except Exception as e:
            nota = str(e)
    caso(10, "/../.env y /%2e%2e/.env no devuelven .env", ok, nota)


def test_opinion_valida(estado_tmp: str, ops_tmp: str) -> str | None:
    """Caso 11: POST /api/opinion válido → 201 + línea en opiniones."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    if os.path.exists(ops_tmp):
        os.remove(ops_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    cookie_opinion = None
    with Servidor(args) as srv:
        try:
            cuerpo = {
                "claridad": 4,
                "sin_programacion": 5,
                "util_partido": 4,
                "confianza_datos": 3,
                "funcionamiento": 5,
                "rol": "Analista",
                "gusto": "Me gustó el chat",
            }
            code, data, cookie_opinion = _post(srv.url("/api/opinion"), cuerpo)
            # Verificar 201 y línea nueva
            ok1 = code == 201 and data.get("ok") == True
            lineas_antes = 0
            # El archivo se crea después del POST
            time.sleep(0.1)
        except Exception as e:
            nota = str(e)
            caso(11, "POST /api/opinion válido → 201 + línea nueva", ok, nota)
            return None

    # Verificar el archivo fuera del context manager
    try:
        if os.path.exists(ops_tmp):
            with open(ops_tmp, encoding="utf-8") as f:
                lineas = [l for l in f if l.strip()]
            ok2 = len(lineas) >= 1
            registro = json.loads(lineas[-1])
            ok3 = registro.get("claridad") == 4 and registro.get("rol") == "Analista"
            ok = ok1 and ok2 and ok3
            nota = "" if ok else f"status={code} lineas={len(lineas)} registro={registro}"
        else:
            ok = False
            nota = "archivo de opiniones no creado"
    except Exception as e:
        ok, nota = False, str(e)
    caso(11, "POST /api/opinion válido → 201 + línea nueva", ok, nota)
    return cookie_opinion


def test_opinion_invalida(estado_tmp: str, ops_tmp: str):
    """Caso 12: Opinión con escala 7 → 400 sin escribir nada."""
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    lineas_antes = 0
    if os.path.exists(ops_tmp):
        with open(ops_tmp, encoding="utf-8") as f:
            lineas_antes = sum(1 for l in f if l.strip())

    with Servidor(args) as srv:
        try:
            cuerpo = {
                "claridad": 7,     # inválido
                "sin_programacion": 5,
                "util_partido": 4,
                "confianza_datos": 3,
                "funcionamiento": 5,
            }
            code, data, _ = _post(srv.url("/api/opinion"), cuerpo)
            ok1 = code == 400
        except Exception as e:
            nota = str(e)
            caso(12, "Opinión con escala 7 → 400 sin escribir nada", False, nota)
            return

    lineas_despues = 0
    if os.path.exists(ops_tmp):
        with open(ops_tmp, encoding="utf-8") as f:
            lineas_despues = sum(1 for l in f if l.strip())
    ok = ok1 and lineas_despues == lineas_antes
    nota = "" if ok else f"status={code} lineas_antes={lineas_antes} lineas_despues={lineas_despues}"
    caso(12, "Opinión con escala 7 → 400 sin escribir nada", ok, nota)


def test_cuarta_opinion(estado_tmp: str, ops_tmp: str, cookie_opinion: str | None):
    """Caso 13: Cuarta opinión de la misma persona → 429."""
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    cuerpo_valido = {
        "claridad": 3,
        "sin_programacion": 3,
        "util_partido": 3,
        "confianza_datos": 3,
        "funcionamiento": 3,
    }
    with Servidor(args) as srv:
        try:
            # La persona ya envió 1 opinión (caso 11). Enviar 2 más (hasta 3 = tope).
            for _ in range(2):
                _post(srv.url("/api/opinion"), cuerpo_valido, cookie=cookie_opinion)
            # La cuarta debe dar 429
            code4, data4, _ = _post(srv.url("/api/opinion"), cuerpo_valido, cookie=cookie_opinion)
            ok = code4 == 429 and data4.get("error") == "tope_opiniones"
            nota = "" if ok else f"status={code4} data={data4}"
        except Exception as e:
            nota = str(e)
    caso(13, "Cuarta opinión de la misma persona → 429", ok, nota)


def test_opinion_fuera_prueba(estado_tmp: str, ops_tmp: str):
    """Caso 14: /api/opinion sin modo prueba → 404; con prueba vencida → 410."""
    nota = ""
    ok = False
    # Sin modo prueba
    with Servidor([]) as srv:
        try:
            cuerpo = {
                "claridad": 3, "sin_programacion": 3,
                "util_partido": 3, "confianza_datos": 3, "funcionamiento": 3,
            }
            code, data, _ = _post(srv.url("/api/opinion"), cuerpo)
            ok1 = code == 404
        except Exception as e:
            caso(14, "/api/opinion sin prueba→404 / vencida→410", False, str(e))
            return

    # Con prueba vencida
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "1", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    with Servidor(args) as srv:
        try:
            _vencer_prueba(estado_tmp)
            time.sleep(0.1)
            cuerpo = {
                "claridad": 3, "sin_programacion": 3,
                "util_partido": 3, "confianza_datos": 3, "funcionamiento": 3,
            }
            code2, data2, _ = _post(srv.url("/api/opinion"), cuerpo)
            ok2 = code2 == 410 and data2.get("error") == "prueba_terminada"
            ok = ok1 and ok2
            nota = "" if ok else f"sin_prueba={code if not ok1 else 'ok'} vencida={code2}"
        except Exception as e:
            nota = str(e)
    caso(14, "/api/opinion sin prueba→404 / vencida→410", ok, nota)


def test_resumen_opiniones(ops_tmp: str):
    """Caso 15: resumen_opiniones.py imprime sin error."""
    nota = ""
    ok = False
    if not os.path.exists(ops_tmp):
        caso(15, "resumen_opiniones.py imprime sin error", False, "archivo de opiniones no existe")
        return
    try:
        resultado = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "resumen_opiniones.py"), "--archivo", ops_tmp],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20,
        )
        ok = resultado.returncode == 0 and "Opiniones:" in resultado.stdout
        nota = "" if ok else f"rc={resultado.returncode} stderr={resultado.stderr[:100]}"
    except Exception as e:
        nota = str(e)
    caso(15, "resumen_opiniones.py imprime sin error", ok, nota)


def test_inicio_enlaza_opinion(estado_tmp: str, ops_tmp: str):
    """Caso 16 (P1): index.html en modo prueba contiene enlace a opinion.html."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            code, body, _ = _get(srv.url("/pages/index.html"))
            contenido = body.decode("utf-8", errors="replace")
            # La página debe cargarse bien (200) y contener el script que inyecta el enlace
            # Verificamos que el script de la franja de prueba esté en el HTML
            ok = code == 200 and "opinion.html" in contenido
            nota = "" if ok else f"status={code} 'opinion.html' en HTML={('opinion.html' in contenido)}"
        except Exception as e:
            nota = str(e)
    caso(16, "P1: index.html en modo prueba contiene enlace a opinion.html", ok, nota)


TUNEL = "prueba-ejemplo.trycloudflare.com"


def test_chat_por_tunel_prueba(estado_tmp: str, ops_tmp: str):
    """Caso 17: en modo prueba, el chat acepta el Host del túnel; Operaciones no."""
    if os.path.exists(estado_tmp):
        os.remove(estado_tmp)
    args = ["--prueba-horas", "48", "--tope-chat", "15",
            "--estado", estado_tmp, "--opiniones", ops_tmp,
            "--chat-falso"]
    nota = ""
    ok = False
    with Servidor(args) as srv:
        try:
            h = {"Host": TUNEL, "Origin": f"https://{TUNEL}"}
            c_estado, _, _ = _get(srv.url("/api/chat/estado"), headers=h)
            c_chat, _, _ = _post(srv.url("/api/chat"),
                                 {"pregunta": "¿Qué tarjetas hubo?", "historial": []}, headers=h)
            c_ops, _, _ = _get(srv.url("/api/operaciones/chat"), headers=h)
            h_malo = {"Host": TUNEL, "Origin": "https://otro-sitio.example"}
            c_otro, _, _ = _post(srv.url("/api/chat"),
                                 {"pregunta": "¿Qué tarjetas hubo?", "historial": []}, headers=h_malo)
            ok = c_estado == 200 and c_chat == 200 and c_ops == 403 and c_otro == 403
            nota = "" if ok else f"estado={c_estado} chat={c_chat} operaciones={c_ops} origen_ajeno={c_otro}"
        except Exception as e:
            nota = str(e)
    caso(17, "Túnel en modo prueba: chat 200, Operaciones y Origin ajeno 403", ok, nota)


def test_chat_por_tunel_sin_prueba():
    """Caso 18: sin modo prueba, el Host del túnel sigue bloqueado en el chat."""
    nota = ""
    ok = False
    with Servidor([]) as srv:
        try:
            h = {"Host": TUNEL, "Origin": f"https://{TUNEL}"}
            c_estado, _, _ = _get(srv.url("/api/chat/estado"), headers=h)
            c_chat, _, _ = _post(srv.url("/api/chat"),
                                 {"pregunta": "¿Qué tarjetas hubo?", "historial": []}, headers=h)
            ok = c_estado == 403 and c_chat == 403
            nota = "" if ok else f"estado={c_estado} chat={c_chat}"
        except Exception as e:
            nota = str(e)
    caso(18, "Túnel sin modo prueba: chat 403", ok, nota)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(_SEP)
    print(f"{'#':>3}  {'Estado':7}  {'Descripción'}")
    print(_SEP)

    with tempfile.TemporaryDirectory() as tmpdir:
        estado_tmp   = os.path.join(tmpdir, "prueba_estado.json")
        ops_tmp      = os.path.join(tmpdir, "opiniones.jsonl")
        ops_tmp2     = os.path.join(tmpdir, "opiniones2.jsonl")

        test_sin_prueba_horas()
        fin_original = test_primer_arranque(estado_tmp)
        test_reinicio(estado_tmp, fin_original)
        test_regla_no_cuenta(estado_tmp, ops_tmp)
        cookie_llena = test_tope_alcanzado(estado_tmp, ops_tmp)
        test_otra_persona(estado_tmp, ops_tmp, cookie_llena)
        test_prueba_vencida(estado_tmp, ops_tmp)
        test_operaciones_ibm(estado_tmp, ops_tmp)
        test_listado_carpetas(estado_tmp, ops_tmp)
        test_path_traversal(estado_tmp, ops_tmp)
        cookie_opinion = test_opinion_valida(estado_tmp, ops_tmp2)
        test_opinion_invalida(estado_tmp, ops_tmp2)
        test_cuarta_opinion(estado_tmp, ops_tmp2, cookie_opinion)
        test_opinion_fuera_prueba(estado_tmp, ops_tmp)
        test_resumen_opiniones(ops_tmp2)
        test_inicio_enlaza_opinion(estado_tmp, ops_tmp)
        test_chat_por_tunel_prueba(estado_tmp, ops_tmp)
        test_chat_por_tunel_sin_prueba()

    print(_SEP)
    fallos = sum(1 for _, _, ok, _ in resultados if not ok)
    total = len(resultados)
    print(f"Resultado: {total - fallos}/{total} OK", end="")
    if fallos:
        print(f"  ---  {fallos} FALLA(S)")
        sys.exit(1)
    else:
        print("  OK Todo correcto")
        sys.exit(0)


if __name__ == "__main__":
    main()
