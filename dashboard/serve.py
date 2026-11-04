r"""
dashboard/serve.py
==================
Servidor estático mínimo para el tablero MATEO con soporte de peticiones HTTP Range
(necesario para que el navegador pueda adelantar/retroceder los videos MP4).

`python -m http.server` NO soporta Range: los videos se reproducen pero al hacer
seek regresan a 0. Este servidor sí lo soporta y no tiene dependencias externas.

Uso local:
    .\.venv\Scripts\python.exe dashboard/serve.py            -> http://localhost:8600
    .\.venv\Scripts\python.exe dashboard/serve.py --port 9000

En contenedor (IBM Cloud Code Engine) respeta la variable de entorno PORT.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


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
        if self.path.endswith((".json", ".html")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
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
    print(f"MATEO dashboard → http://localhost:{args.port}/pages/mateo.html")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
