r"""
dashboard/serve.py
==================
Servidor estático mínimo para el tablero MATEO con soporte de peticiones HTTP Range
(necesario para que el navegador pueda adelantar/retroceder los videos MP4).

`python -m http.server` NO soporta Range: los videos se reproducen pero al hacer
seek regresan a 0. Este servidor sí lo soporta y no tiene dependencias externas.

Además expone el chatbot táctico (ibm/granite-4-h-small):
    POST /api/chat          {"pregunta": "...", "historial": [{"role", "content"}]}
    GET  /api/chat/estado   {"estado": "cargando|listo|no_disponible|desactivado", ...}
El endpoint gasta cuota de watsonx.ai, así que solo atiende conexiones locales
(127.0.0.1 / ::1), exige Host y Origin locales, limita las peticiones por minuto y
el tamaño del cuerpo. Si no hay credenciales o SDK, el resto del tablero funciona igual.
MATEO_CHAT=0 desactiva el chat.

Uso local:
    .\.venv\Scripts\python.exe dashboard/serve.py            -> http://localhost:8600
    .\.venv\Scripts\python.exe dashboard/serve.py --port 9000

En contenedor (IBM Cloud Code Engine) respeta la variable de entorno PORT. El chat
no atiende peticiones remotas, y necesitaría implementacion/ y las credenciales.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import deque
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

# ---------------------------------------------------------------------------
# Chatbot táctico
# ---------------------------------------------------------------------------
LOCAL_ADDRS = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
MAX_BODY_BYTES = 16 * 1024
MAX_PETICIONES_POR_MINUTO = 12
MAX_CARACTERES_MENSAJE = 2000


class ChatBackend:
    """Carga Granite en segundo plano y atiende una pregunta a la vez."""

    def __init__(self) -> None:
        self.estado = "desactivado" if os.environ.get("MATEO_CHAT") == "0" else "cargando"
        self.motivo = ""
        self.agente = None
        self.modelo = None
        self.datos = None
        self._lock = threading.Lock()
        self._recientes: deque = deque()

    def iniciar(self) -> None:
        if self.estado == "cargando":
            threading.Thread(target=self._cargar, name="chat-carga", daemon=True).start()

    def _cargar(self) -> None:
        try:
            if PROJECT_ROOT not in sys.path:
                sys.path.insert(0, PROJECT_ROOT)
            from implementacion.cloud_agent import chat_agent

            self.agente = chat_agent
            self.datos = chat_agent.cargar_datos()
            self.modelo = chat_agent.obtener_modelo()
            if self.modelo is None:
                self.estado, self.motivo = "no_disponible", "sin credenciales o SDK de watsonx.ai"
            else:
                self.estado = "listo"
        except Exception as exc:  # el tablero debe seguir funcionando sin el chat
            self.estado, self.motivo = "no_disponible", type(exc).__name__
        print(f"[chat] estado: {self.estado} {self.motivo}".rstrip(), flush=True)

    def info(self) -> dict:
        return {
            "estado": self.estado,
            "motivo": self.motivo,
            "modelo": getattr(self.agente, "REQUIRED_MODEL", "ibm/granite-4-h-small"),
            "max_pregunta": getattr(self.agente, "MAX_CARACTERES_PREGUNTA", 500),
        }

    def permitir(self) -> bool:
        """Límite de peticiones por minuto, global (el servidor es de uso local)."""
        ahora = time.monotonic()
        with self._lock:
            while self._recientes and ahora - self._recientes[0] > 60:
                self._recientes.popleft()
            if len(self._recientes) >= MAX_PETICIONES_POR_MINUTO:
                return False
            self._recientes.append(ahora)
            return True

    def responder(self, pregunta: str, historial: list) -> dict:
        a = self.agente
        with self._lock:
            contexto = a.serializar_contexto(self.datos)
            respuesta = a.respuesta_sin_datos(pregunta, self.datos)
            origen = "regla" if respuesta else "granite"
            metricas: dict = {}
            if respuesta is None:
                try:
                    mensajes = a.construir_mensajes(pregunta, historial, self.datos)
                    respuesta = "".join(a.responder_stream(self.modelo, mensajes, metricas))
                except Exception as exc:
                    a.auditar_respuesta(pregunta, None, contexto, metricas, error=str(exc))
                    raise
            auditoria = a.auditar_respuesta(
                pregunta, respuesta, contexto, metricas, origen=origen, hechos=self.datos["hechos"]
            )
        return {
            "respuesta": respuesta,
            "origen": origen,
            "modelo": a.REQUIRED_MODEL,
            "estado": auditoria["status"],
            "latency_ms": auditoria["latency_ms"],
            "tokens_in": auditoria["tokens_in"],
            "tokens_out": auditoria["tokens_out"],
            "atribucion_incorrecta": auditoria["atribucion_incorrecta"],
            "numeros_sin_respaldo": auditoria["numeros_sin_respaldo"],
            "avisos": a.avisos_calidad(respuesta),
        }


CHAT = ChatBackend()


def _historial_valido(crudo) -> list:
    """Solo mensajes {role: user|assistant, content: str}; el resto se descarta."""
    if not isinstance(crudo, list):
        return []
    limpio = []
    for m in crudo[-12:]:
        if (
            isinstance(m, dict)
            and m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
        ):
            limpio.append({"role": m["role"], "content": m["content"][:MAX_CARACTERES_MENSAJE]})
    return limpio


class RangeHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".mp4": "video/mp4",
        ".vtt": "text/vtt",
        ".wav": "audio/wav",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".js": "text/javascript",
        ".css": "text/css",
    }

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        # Sin caché en lo que cambia durante el desarrollo, para no ver versiones viejas
        if self.path.split("?")[0].endswith((".json", ".html", ".js", ".css")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    # ── API del chat ────────────────────────────────────────────────────────
    def _json(self, codigo: int, cuerpo: dict) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(datos)

    def _origen_local(self) -> bool:
        """Cliente local y Host/Origin locales (frena también el DNS rebinding)."""
        if self.client_address[0] not in LOCAL_ADDRS:
            return False
        host = (self.headers.get("Host") or "").strip().lower()
        if host.rsplit(":", 1)[0] not in LOCAL_HOSTS and host not in LOCAL_HOSTS:
            return False
        origen = self.headers.get("Origin")
        return origen is None or (urlparse(origen).netloc.lower() == host)

    def do_POST(self):
        if self.path.split("?")[0] != "/api/chat":
            return self._json(404, {"error": "no_encontrado"})
        if not self._origen_local():
            return self._json(403, {"error": "solo_local"})
        if CHAT.estado != "listo":
            return self._json(503, {"error": "chat_no_disponible", **CHAT.info()})
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._json(415, {"error": "se_espera_json"})
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        if largo <= 0 or largo > MAX_BODY_BYTES:
            return self._json(413, {"error": "cuerpo_invalido"})
        try:
            cuerpo = json.loads(self.rfile.read(largo).decode("utf-8"))
            pregunta = cuerpo["pregunta"].strip()
        except (ValueError, KeyError, AttributeError, UnicodeDecodeError):
            return self._json(400, {"error": "peticion_invalida"})
        if not pregunta or len(pregunta) > CHAT.info()["max_pregunta"]:
            return self._json(400, {"error": "pregunta_invalida"})
        if not CHAT.permitir():
            return self._json(429, {"error": "demasiadas_peticiones"})
        try:
            self._json(200, CHAT.responder(pregunta, _historial_valido(cuerpo.get("historial"))))
        except Exception:
            self._json(502, {"error": "granite_no_respondio"})

    def do_GET(self):
        if self.path.split("?")[0] == "/api/chat/estado":
            if not self._origen_local():
                return self._json(403, {"error": "solo_local"})
            return self._json(200, CHAT.info())
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/pages/index.html")
            self.end_headers()
            return

        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().do_GET()

        m = _RANGE_RE.match(rng.strip())
        size = os.path.getsize(path)
        if not m:
            return super().do_GET()
        start_s, end_s = m.groups()
        if start_s == "":
            length = int(end_s or 0)
            start, end = max(0, size - length), size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return

        chunk = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(chunk))
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            remaining = chunk
            try:
                while remaining > 0:
                    data = f.read(min(1024 * 256, remaining))
                    if not data:
                        break
                    self.wfile.write(data)
                    remaining -= len(data)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                pass  # el navegador cancela rangos al hacer seek; es normal

    def log_message(self, fmt, *args):
        if os.environ.get("MATEO_QUIET"):
            return
        super().log_message(fmt, *args)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8600)))
    ap.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    args = ap.parse_args()
    handler = partial(RangeHandler, directory=ROOT)
    srv = ThreadingHTTPServer((args.host, args.port), handler)
    CHAT.iniciar()
    print(f"MATEO dashboard → http://localhost:{args.port}/pages/mateo.html")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
