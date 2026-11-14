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
Y la página Operaciones (también solo local):
    GET  /api/operaciones/chat   últimas llamadas del chat y totales de tokens y RU
    GET  /api/operaciones/ibm    IBM Cloud IAM y watsonx.ai sin generar texto (0 RU); ?forzar=1
El endpoint gasta cuota de watsonx.ai, así que solo atiende conexiones locales
(127.0.0.1 / ::1), exige Host y Origin locales, limita las peticiones por minuto y
el tamaño del cuerpo. Si no hay credenciales o SDK, el resto del tablero funciona igual.
MATEO_CHAT=0 desactiva el chat.

Uso local:
    .\.venv\Scripts\python.exe dashboard/serve.py            -> http://localhost:8600
    .\.venv\Scripts\python.exe dashboard/serve.py --port 9000

Modo prueba (para el equipo, 48 h con tope de 15 preguntas por persona):
    .\.venv\Scripts\python.exe dashboard/serve.py --prueba-horas 48 --tope-chat 15

    - Fija el fin de la prueba al primer arranque y lo guarda en data/clean/prueba_estado.json.
      Si el servidor se reinicia, NO vuelve a empezar: lee el archivo y respeta el fin original.
      Para empezar una prueba NUEVA, borra data/clean/prueba_estado.json a mano.
    - En modo prueba escucha SOLO en 127.0.0.1 (el túnel se conecta desde la misma PC).
    - --estado <ruta>    ruta alternativa para el archivo de estado (útil en tests).
    - --opiniones <ruta> ruta alternativa para el archivo de opiniones (útil en tests).
    - --chat-falso       responde texto fijo sin llamar a watsonx (opción oculta para tests).

En contenedor (IBM Cloud Code Engine) respeta la variable de entorno PORT. El chat
no atiende peticiones remotas, y necesitaría implementacion/ y las credenciales.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
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
DOMINIO_TUNEL = ".trycloudflare.com"  # solo se acepta en modo prueba (chat)
MAX_BODY_BYTES = 16 * 1024
MAX_PETICIONES_POR_MINUTO = 12
MAX_CARACTERES_MENSAJE = 2000


class ChatBackend:
    """Carga Granite en segundo plano y atiende una pregunta a la vez."""

    def __init__(self, chat_falso: bool = False) -> None:
        self.chat_falso = chat_falso
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
            if self.chat_falso:
                self.modelo = object()   # truthy — indica «listo» sin llamar a IBM
            else:
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
            "sugeridas": self.agente.preguntas_sugeridas(self.datos) if self.datos else [],
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
            respuesta = a.respuesta_por_regla(pregunta, self.datos, historial)
            origen = "regla" if respuesta else "granite"
            metricas: dict = {}
            if respuesta is None:
                if self.chat_falso:
                    respuesta = "Respuesta de prueba (chat falso). Granite no fue llamado."
                    metricas = {"latency_ms": 0, "tokens_in": 0, "tokens_out": 0}
                else:
                    try:
                        mensajes = a.construir_mensajes(pregunta, historial, self.datos)
                        respuesta = "".join(a.responder_stream(self.modelo, mensajes, metricas))
                    except Exception as exc:
                        a.auditar_respuesta(pregunta, None, contexto, metricas, error=str(exc))
                        raise
            auditoria = a.auditar_respuesta(
                pregunta,
                respuesta,
                contexto,
                metricas,
                origen=origen,
                hechos=self.datos.get("hechos"),
                bloquear=True,
            )
        bloqueada = auditoria["bloqueada"]
        if bloqueada:
            respuesta = a.MENSAJE_BLOQUEADA
        return {
            "respuesta": respuesta,
            "bloqueada": bloqueada,
            "origen": origen,
            "modelo": a.REQUIRED_MODEL,
            "estado": auditoria["status"],
            "latency_ms": auditoria["latency_ms"],
            "tokens_in": auditoria["tokens_in"],
            "tokens_out": auditoria["tokens_out"],
            "atribucion_incorrecta": [] if bloqueada else auditoria["atribucion_incorrecta"],
            "numeros_sin_respaldo": [] if bloqueada else auditoria["numeros_sin_respaldo"],
            "avisos": a.avisos_calidad(respuesta, self.datos),
        }


CHAT = ChatBackend()


# ---------------------------------------------------------------------------
# Modo prueba — estado y contadores
# ---------------------------------------------------------------------------

class ModoPrueba:
    """
    Gestiona el estado de la prueba de equipo (límite de tiempo + tope por persona).

    El estado se guarda en un archivo JSON (por defecto data/clean/prueba_estado.json).
    Si el servidor se reinicia, NO vuelve a empezar: lee el archivo y respeta el fin
    original.  Para empezar una nueva prueba, borra el archivo a mano.

    Formato::

        {
          "inicio": "<ISO>",
          "fin": "<ISO>",
          "tope_chat": 15,
          "tope_global": 300,
          "contadores": {"<om_id_hex32>": <n>, ...},
          "granite_total": <n>,
          "opiniones_por_persona": {"<om_id_hex32>": <n>, ...}
        }
    """

    TOPE_GLOBAL = 300
    TOPE_OPINIONES = 3   # una persona puede enviar hasta 3 veces

    def __init__(
        self,
        horas: int,
        tope_chat: int,
        estado_path: str,
        opiniones_path: str,
    ) -> None:
        self.horas = horas
        self.tope_chat = tope_chat
        self.estado_path = estado_path
        self.opiniones_path = opiniones_path
        self._lock = threading.Lock()
        self._estado: dict = {}
        self._cargar_o_crear()

    def _cargar_o_crear(self) -> None:
        if os.path.exists(self.estado_path):
            try:
                with open(self.estado_path, encoding="utf-8") as f:
                    self._estado = json.load(f)
                print(
                    f"[prueba] estado existente leído: fin={self._estado.get('fin')}",
                    flush=True,
                )
                return
            except Exception as exc:
                print(
                    f"[prueba] no se pudo leer {self.estado_path}: {exc}. Creando nuevo.",
                    flush=True,
                )

        ahora = datetime.now(tz=timezone.utc)
        fin = ahora + timedelta(hours=self.horas)
        self._estado = {
            "inicio": ahora.isoformat(),
            "fin": fin.isoformat(),
            "tope_chat": self.tope_chat,
            "tope_global": self.TOPE_GLOBAL,
            "contadores": {},
            "granite_total": 0,
            "opiniones_por_persona": {},
        }
        self._guardar()
        print(f"[prueba] iniciada. fin={fin.isoformat()}", flush=True)

    def _guardar(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.estado_path)), exist_ok=True)
        tmp = self.estado_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._estado, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.estado_path)

    def activa(self) -> bool:
        # Re-lee el fin del archivo para que los tests (y un operador manual) puedan
        # vencer la prueba escribiendo un fin ya pasado sin reiniciar el servidor.
        try:
            with open(self.estado_path, encoding="utf-8") as f:
                fin_iso = json.load(f).get("fin", self._estado["fin"])
        except Exception:
            fin_iso = self._estado["fin"]
        # Actualizar en memoria para que restantes() use el tope actual
        self._estado["fin"] = fin_iso
        fin = datetime.fromisoformat(fin_iso)
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        return datetime.now(tz=timezone.utc) < fin

    def fin_iso(self) -> str:
        return self._estado["fin"]

    def fin_legible(self) -> str:
        fin = datetime.fromisoformat(self._estado["fin"])
        if fin.tzinfo is None:
            fin = fin.replace(tzinfo=timezone.utc)
        return fin.astimezone().strftime("%d/%m/%Y a las %H:%M")

    # ── Chat ─────────────────────────────────────────────────────────────────

    def restantes(self, om_id: str) -> int:
        tope = self._estado.get("tope_chat", self.tope_chat)
        usado = self._estado["contadores"].get(om_id, 0)
        return max(0, tope - usado)

    def tope_alcanzado(self, om_id: str) -> bool:
        return self.restantes(om_id) <= 0

    def tope_global_alcanzado(self) -> bool:
        return self._estado.get("granite_total", 0) >= self._estado.get(
            "tope_global", self.TOPE_GLOBAL
        )

    def contar_granite(self, om_id: str) -> None:
        with self._lock:
            self._estado["contadores"][om_id] = (
                self._estado["contadores"].get(om_id, 0) + 1
            )
            self._estado["granite_total"] = self._estado.get("granite_total", 0) + 1
            self._guardar()

    def estado_api(self, om_id: str) -> dict:
        return {
            "activa": self.activa(),
            "fin": self.fin_iso(),
            "restantes": self.restantes(om_id) if self.activa() else 0,
        }

    # ── Opiniones ─────────────────────────────────────────────────────────────

    def opiniones_de(self, om_id: str) -> int:
        return self._estado.get("opiniones_por_persona", {}).get(om_id, 0)

    def registrar_opinion(self, om_id: str, datos: dict) -> None:
        """Añade una línea al jsonl y actualiza el contador."""
        entrada = {
            "fecha": datetime.now(tz=timezone.utc).isoformat(),
            "id_prueba": om_id,
            **datos,
        }
        os.makedirs(os.path.dirname(os.path.abspath(self.opiniones_path)), exist_ok=True)
        with open(self.opiniones_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        with self._lock:
            ops = self._estado.setdefault("opiniones_por_persona", {})
            ops[om_id] = ops.get(om_id, 0) + 1
            self._guardar()


PRUEBA: ModoPrueba | None = None   # None = modo normal


# ---------------------------------------------------------------------------
# Validación del formulario de opinión
# ---------------------------------------------------------------------------
_ESCALAS_VALIDAS = {1, 2, 3, 4, 5}
_ROLES_VALIDOS = {
    "Analista", "Cuerpo técnico", "Jugador", "Desarrollo o datos", "Otro"
}
_DISPOSITIVOS_VALIDOS = {"Computadora", "Celular", "Los dos"}
_ENSENAR_VALIDOS = {
    "Sí, tal cual", "Si, tal cual",
    "Sí, con avisos", "Si, con avisos",
    "Todavía no", "Todavia no",
}
_CHAT_VALIDOS = _ESCALAS_VALIDAS | {"No lo usé", "No lo use"}
_MAX_TEXTO = 1000
_MAX_NOMBRE = 60


def _validar_opinion(cuerpo: dict) -> tuple[bool, str]:
    """Devuelve (ok, mensaje_error). Todos los campos son opcionales menos las escalas."""
    if not isinstance(cuerpo, dict):
        return False, "cuerpo no es objeto JSON"

    # Escalas obligatorias 1-5
    for campo in ("claridad", "sin_programacion", "util_partido", "confianza_datos", "funcionamiento"):
        v = cuerpo.get(campo)
        if v is None:
            return False, f"falta campo obligatorio: {campo}"
        if v not in _ESCALAS_VALIDAS:
            return False, f"escala inválida en {campo}: {v!r}"

    # Chat: 1-5 o "No lo usé"
    chat_val = cuerpo.get("chat")
    if chat_val is not None and chat_val not in _CHAT_VALIDOS:
        return False, f"valor inválido en chat: {chat_val!r}"

    # Rol
    rol = cuerpo.get("rol")
    if rol is not None and rol not in _ROLES_VALIDOS:
        return False, f"rol inválido: {rol!r}"

    # Dispositivo
    disp = cuerpo.get("dispositivo")
    if disp is not None and disp not in _DISPOSITIVOS_VALIDOS:
        return False, f"dispositivo inválido: {disp!r}"

    # Enseñarías
    ens = cuerpo.get("ensenarias")
    if ens is not None and ens not in _ENSENAR_VALIDOS:
        return False, f"valor inválido en ensenarias: {ens!r}"

    # Textos opcionales
    for campo, maxlen in (
        ("gustó", _MAX_TEXTO), ("gusto", _MAX_TEXTO),
        ("confundio", _MAX_TEXTO),
        ("mejora", _MAX_TEXTO),
        ("nombre", _MAX_NOMBRE),
    ):
        v = cuerpo.get(campo)
        if v is not None:
            if not isinstance(v, str):
                return False, f"{campo} debe ser texto"
            if len(v) > maxlen:
                return False, f"{campo} supera el límite de {maxlen} caracteres"

    return True, ""


# ---------------------------------------------------------------------------
# Página de cierre (prueba vencida)
# ---------------------------------------------------------------------------

def _pagina_cierre() -> bytes:
    """HTML sencillo con el estilo mínimo de la app para cuando la prueba termina."""
    fin = PRUEBA.fin_legible() if PRUEBA else "—"
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OMNIMORPH \u2014 Prueba terminada</title>
  <style>
    body {{ font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
           background: #0f1117; color: #c9d1d9; margin: 0;
           display: flex; align-items: center; justify-content: center;
           min-height: 100vh; }}
    .box {{ max-width: 540px; padding: 2.5rem; text-align: center; }}
    h1 {{ font-size: 1.4rem; color: #e6edf3; margin-bottom: 1rem; }}
    p {{ font-size: 0.95rem; line-height: 1.6; color: #8b949e; margin: 0.5rem 0; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>La prueba de Omnimorph termin\u00f3</h1>
    <p>La prueba finaliz\u00f3 el {fin}.</p>
    <p>Gracias por probarla. El formulario de opini\u00f3n ya cerr\u00f3 con la prueba.</p>
  </div>
</body>
</html>""".encode("utf-8")
    return html


# ---------------------------------------------------------------------------
# Operaciones: consumo del chat y conexión con IBM
# ---------------------------------------------------------------------------
CHAT_AUDIT = os.path.join(PROJECT_ROOT, "data", "clean", "chat_audit.jsonl")
IAM_URL = "https://iam.cloud.ibm.com/identity/token"
MODELO_GRANITE = "ibm/granite-4-h-small"
CACHE_IBM_S = 60
MIN_ENTRE_COMPROBACIONES_S = 10


def resumen_chat(ultimas: int = 15) -> dict:
    """Últimas llamadas del chat y totales, desde chat_audit.jsonl. Sin respuestas ni contexto."""
    from datetime import date, datetime as dt

    registros = []
    if os.path.exists(CHAT_AUDIT):
        with open(CHAT_AUDIT, encoding="utf-8") as f:
            for linea in f:
                try:
                    registros.append(json.loads(linea))
                except ValueError:
                    continue

    def totales(regs: list) -> dict:
        granite = [r for r in regs if r.get("origen") == "granite"]
        lat = [r["latency_ms"] for r in granite if r.get("latency_ms")]
        return {
            "preguntas": len(regs),
            "por_regla": sum(1 for r in regs if r.get("origen") == "regla"),
            "a_granite": len(granite),
            "bloqueadas": sum(1 for r in regs if r.get("bloqueada")),
            "errores": sum(1 for r in regs if r.get("error")),
            "tokens_in": sum(r.get("tokens_in") or 0 for r in granite),
            "tokens_out": sum(r.get("tokens_out") or 0 for r in granite),
            "ru": round(sum(r.get("cost_ru_est") or 0 for r in granite), 4),
            "latencia_ms_media": round(sum(lat) / len(lat), 1) if lat else None,
        }

    hoy = date.today()

    def es_hoy(r: dict) -> bool:
        try:
            return dt.fromisoformat(r["timestamp"]).astimezone().date() == hoy
        except (KeyError, ValueError):
            return False

    entradas = []
    for r in registros[-ultimas:]:
        pregunta = str(r.get("pregunta") or "")
        entradas.append({
            "timestamp": r.get("timestamp"),
            "origen": r.get("origen"),
            "modelo": r.get("model"),
            "pregunta": pregunta[:80] + ("\u2026" if len(pregunta) > 80 else ""),
            "tokens_in": r.get("tokens_in"),
            "tokens_out": r.get("tokens_out"),
            "latency_ms": r.get("latency_ms"),
            "primer_token_ms": r.get("primer_token_ms"),
            "ru": r.get("cost_ru_est"),
            "status": r.get("status"),
            "bloqueada": bool(r.get("bloqueada")),
            "error": bool(r.get("error")),
        })
    return {
        "entradas": entradas,
        "hoy": totales([r for r in registros if es_hoy(r)]),
        "historico": totales(registros),
    }


class EstadoIBM:
    """Comprueba IBM Cloud IAM y watsonx.ai sin generar texto (0 RU). Nunca devuelve la clave ni el token."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ultimo: dict | None = None
        self._t = 0.0

    @staticmethod
    def _credenciales() -> tuple[str, str]:
        try:
            from dotenv import load_dotenv
            load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
        except ImportError:
            pass
        return (os.environ.get("IBM_CLOUD_API_KEY", "").strip(),
                os.environ.get("WATSONX_URL", "").strip().rstrip("/"))

    @staticmethod
    def _peticion(req) -> tuple[bool, float, object]:
        import urllib.request
        inicio = time.perf_counter()
        with urllib.request.urlopen(req, timeout=5) as resp:
            cuerpo = json.loads(resp.read().decode("utf-8"))
        return True, round((time.perf_counter() - inicio) * 1000, 1), cuerpo

    def _comprobar(self) -> dict:
        import urllib.parse
        import urllib.request

        clave, url = self._credenciales()
        iam = {"ok": False, "motivo": "sin credenciales en .env"}
        if clave:
            try:
                datos = urllib.parse.urlencode({
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": clave,
                }).encode()
                req = urllib.request.Request(IAM_URL, data=datos, method="POST", headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                })
                ok, ms, cuerpo = self._peticion(req)
                iam = {"ok": ok and bool(cuerpo.get("access_token")), "ms": ms}
            except Exception as exc:
                iam = {"ok": False, "motivo": type(exc).__name__}

        wx = {"ok": False, "motivo": "sin WATSONX_URL en .env"}
        if url:
            try:
                q = urllib.parse.urlencode({
                    "version": "2024-05-01",
                    "filters": "modelid_" + MODELO_GRANITE,
                })
                req = urllib.request.Request(
                    f"{url}/ml/v1/foundation_model_specs?{q}",
                    headers={"Accept": "application/json"},
                )
                ok, ms, cuerpo = self._peticion(req)
                disponible = any(
                    r.get("model_id") == MODELO_GRANITE for r in cuerpo.get("resources", [])
                )
                wx = {
                    "ok": disponible,
                    "ms": ms,
                    "region": urllib.parse.urlparse(url).netloc,
                    "modelo": MODELO_GRANITE,
                    **({} if disponible else {"motivo": "modelo no listado en la región"}),
                }
            except Exception as exc:
                wx = {"ok": False, "motivo": type(exc).__name__}

        return {"comprobado": time.time(), "iam": iam, "watsonx": wx}

    def estado(self, forzar: bool = False) -> dict:
        with self._lock:
            edad = time.time() - self._t
            if self._ultimo is None or edad > CACHE_IBM_S or (
                forzar and edad > MIN_ENTRE_COMPROBACIONES_S
            ):
                self._ultimo = self._comprobar()
                self._t = time.time()
            ultimo = dict(self._ultimo)
        chat = CHAT.info()
        ultimo["chat"] = {
            "estado": chat["estado"],
            "motivo": chat["motivo"],
            "modelo": chat["modelo"],
        }
        ultimo["orchestrate"] = {
            "estado": "probado",
            "nota": "Integración probada en desarrollo · sin comprobación en vivo",
        }
        return ultimo


IBM = EstadoIBM()


# ---------------------------------------------------------------------------
# Helpers de cookies y cuerpo
# ---------------------------------------------------------------------------

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


def _om_id_de_cookie(cookie_header: str | None) -> str | None:
    """Extrae el valor de la cookie om_prueba del header Cookie."""
    if not cookie_header:
        return None
    for parte in cookie_header.split(";"):
        kv = parte.strip().split("=", 1)
        if len(kv) == 2 and kv[0].strip() == "om_prueba":
            v = kv[1].strip()
            if re.fullmatch(r"[a-f0-9]{32}", v):
                return v
    return None


# ---------------------------------------------------------------------------
# Handler HTTP
# ---------------------------------------------------------------------------

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
        if self.path.split("?")[0].endswith((".json", ".html", ".js", ".css")):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _json(self, codigo: int, cuerpo: dict, extra_headers: list | None = None) -> None:
        datos = json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.send_header("Cache-Control", "no-store")
        for nombre, valor in (extra_headers or []):
            self.send_header(nombre, valor)
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

    def _origen_chat(self) -> bool:
        """
        Quién puede usar el chat. Fuera del modo prueba, solo la propia PC.
        En modo prueba también el túnel de Cloudflare: cloudflared se conecta
        desde la PC (cliente local) con el Host público *.trycloudflare.com,
        y el navegador envía un Origin igual a ese Host (o ninguno).
        """
        if self._origen_local():
            return True
        if PRUEBA is None or self.client_address[0] not in LOCAL_ADDRS:
            return False
        host = (self.headers.get("Host") or "").strip().lower()
        if not host.endswith(DOMINIO_TUNEL):
            return False
        origen = self.headers.get("Origin")
        return origen is None or (urlparse(origen).netloc.lower() == host)

    def _om_id(self) -> tuple[str, bool]:
        """Devuelve (om_id, es_nuevo). Crea uno nuevo si no existe en la cookie."""
        om_id = _om_id_de_cookie(self.headers.get("Cookie"))
        if om_id:
            return om_id, False
        return secrets.token_hex(16), True

    def _prueba_terminada_html(self) -> None:
        cuerpo = _pagina_cierre()
        self.send_response(410)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _leer_cuerpo_json(self) -> tuple[dict | None, str]:
        """Lee y parsea el cuerpo JSON. Devuelve (dict, "") o (None, mensaje_error)."""
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return None, "se_espera_json"
        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = 0
        if largo <= 0 or largo > MAX_BODY_BYTES:
            return None, "cuerpo_invalido"
        try:
            return json.loads(self.rfile.read(largo).decode("utf-8")), ""
        except (ValueError, UnicodeDecodeError):
            return None, "json_invalido"

    # ── POST ─────────────────────────────────────────────────────────────────

    def do_POST(self):
        ruta = self.path.split("?")[0]

        if ruta == "/api/opinion":
            return self._handle_opinion()

        if ruta != "/api/chat":
            return self._json(404, {"error": "no_encontrado"})
        return self._handle_chat()

    def _handle_chat(self):
        if not self._origen_chat():
            return self._json(403, {"error": "solo_local"})

        # Modo prueba: tiempo agotado → 410
        if PRUEBA is not None and not PRUEBA.activa():
            return self._json(410, {"error": "prueba_terminada"})

        if CHAT.estado != "listo":
            return self._json(503, {"error": "chat_no_disponible", **CHAT.info()})

        cuerpo, err = self._leer_cuerpo_json()
        if cuerpo is None:
            return self._json(415 if err == "se_espera_json" else 413, {"error": err})

        try:
            pregunta = cuerpo["pregunta"].strip()
        except (KeyError, AttributeError):
            return self._json(400, {"error": "peticion_invalida"})
        if not pregunta or len(pregunta) > CHAT.info()["max_pregunta"]:
            return self._json(400, {"error": "pregunta_invalida"})
        if not CHAT.permitir():
            return self._json(429, {"error": "demasiadas_peticiones"})

        # Gestión de cookies y topes en modo prueba
        cookie_headers: list = []
        om_id: str | None = None
        if PRUEBA is not None:
            om_id, es_nuevo = self._om_id()
            if es_nuevo:
                cookie_headers = [
                    ("Set-Cookie", f"om_prueba={om_id}; HttpOnly; SameSite=Lax; Path=/")
                ]

            # Tope global → solo responde por regla
            if PRUEBA.tope_global_alcanzado():
                agente = CHAT.agente
                resp_regla = None
                if agente:
                    resp_regla = agente.respuesta_por_regla(
                        pregunta, CHAT.datos,
                        _historial_valido(cuerpo.get("historial")),
                    )
                if resp_regla is None:
                    resp_regla = (
                        "El chat está pausado temporalmente: se alcanzó el tope "
                        "de preguntas de esta prueba. Las preguntas que respondo "
                        "directamente desde los datos siguen disponibles."
                    )
                return self._json(200, {
                    "respuesta": resp_regla, "bloqueada": False,
                    "origen": "regla", "modelo": getattr(CHAT.agente, "REQUIRED_MODEL", ""),
                    "estado": "PASS", "latency_ms": 0,
                    "tokens_in": 0, "tokens_out": 0,
                    "atribucion_incorrecta": [], "numeros_sin_respaldo": [], "avisos": [],
                    "prueba_restantes": PRUEBA.restantes(om_id),
                }, extra_headers=cookie_headers)

            # Tope individual: verificar si esta pregunta necesitaría Granite
            if PRUEBA.tope_alcanzado(om_id):
                agente = CHAT.agente
                resp_regla = None
                if agente:
                    try:
                        resp_regla = agente.respuesta_por_regla(
                            pregunta, CHAT.datos,
                            _historial_valido(cuerpo.get("historial")),
                        )
                    except Exception:
                        resp_regla = None
                if resp_regla is None:
                    # Necesitaría Granite pero el tope está alcanzado
                    tope = PRUEBA._estado.get("tope_chat", PRUEBA.tope_chat)
                    return self._json(429, {
                        "error": "tope_alcanzado", "tope": tope,
                    }, extra_headers=cookie_headers)
                # Es una respuesta por regla: se sirve sin contar
                return self._json(200, {
                    "respuesta": resp_regla, "bloqueada": False,
                    "origen": "regla", "modelo": getattr(CHAT.agente, "REQUIRED_MODEL", ""),
                    "estado": "PASS", "latency_ms": 0,
                    "tokens_in": 0, "tokens_out": 0,
                    "atribucion_incorrecta": [], "numeros_sin_respaldo": [], "avisos": [],
                    "prueba_restantes": 0,
                }, extra_headers=cookie_headers)

        try:
            resultado = CHAT.responder(
                pregunta, _historial_valido(cuerpo.get("historial"))
            )
        except Exception:
            return self._json(502, {"error": "granite_no_respondio"}, extra_headers=cookie_headers)

        # Contar solo si fue a Granite
        if PRUEBA is not None and om_id and resultado.get("origen") == "granite":
            PRUEBA.contar_granite(om_id)
            resultado["prueba_restantes"] = PRUEBA.restantes(om_id)

        return self._json(200, resultado, extra_headers=cookie_headers)

    def _handle_opinion(self):
        # Solo en modo prueba activa
        if PRUEBA is None:
            return self._json(404, {"error": "no_disponible_fuera_de_prueba"})
        if not PRUEBA.activa():
            return self._json(410, {"error": "prueba_terminada"})

        om_id, es_nuevo = self._om_id()
        cookie_headers: list = []
        if es_nuevo:
            cookie_headers = [
                ("Set-Cookie", f"om_prueba={om_id}; HttpOnly; SameSite=Lax; Path=/")
            ]

        if PRUEBA.opiniones_de(om_id) >= PRUEBA.TOPE_OPINIONES:
            return self._json(429, {
                "error": "tope_opiniones", "tope": PRUEBA.TOPE_OPINIONES,
            }, extra_headers=cookie_headers)

        cuerpo, err = self._leer_cuerpo_json()
        if cuerpo is None:
            return self._json(415 if err == "se_espera_json" else 413, {"error": err})

        ok, mensaje = _validar_opinion(cuerpo)
        if not ok:
            return self._json(400, {"error": "opinion_invalida", "detalle": mensaje},
                              extra_headers=cookie_headers)

        PRUEBA.registrar_opinion(om_id, cuerpo)
        return self._json(201, {"ok": True, "mensaje": "Gracias. Tu opinión llegó al equipo."},
                          extra_headers=cookie_headers)

    # ── GET ──────────────────────────────────────────────────────────────────

    def send_error(self, code, message=None, explain=None):
        ruta = urlparse(self.path).path
        es_pagina = ruta.endswith(".html") or not os.path.splitext(ruta)[1]

        # Modo prueba: tiempo agotado → páginas devuelven 410
        if PRUEBA is not None and not PRUEBA.activa() and self.command == "GET" and es_pagina:
            return self._prueba_terminada_html()

        if code == 404 and self.command == "GET" and es_pagina:
            error_path = os.path.join(self.directory, "pages", "error.html")
            if os.path.exists(error_path):
                with open(error_path, "rb") as f:
                    cuerpo = f.read()
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(cuerpo)))
                self.end_headers()
                self.wfile.write(cuerpo)
                return
        super().send_error(code, message, explain)

    def do_GET(self):
        ruta = self.path.split("?")[0]

        # /api/prueba/estado — siempre disponible
        if ruta == "/api/prueba/estado":
            om_id, es_nuevo = self._om_id()
            cookie_headers: list = []
            if PRUEBA is not None and es_nuevo:
                cookie_headers = [
                    ("Set-Cookie", f"om_prueba={om_id}; HttpOnly; SameSite=Lax; Path=/")
                ]
            if PRUEBA is None:
                return self._json(200, {"activa": False}, extra_headers=cookie_headers)
            return self._json(200, PRUEBA.estado_api(om_id), extra_headers=cookie_headers)

        if ruta == "/api/chat/estado":
            if not self._origen_chat():
                return self._json(403, {"error": "solo_local"})
            return self._json(200, CHAT.info())

        if ruta in ("/api/operaciones/chat", "/api/operaciones/ibm"):
            if not self._origen_local():
                return self._json(403, {"error": "solo_local"})
            # En modo prueba, /api/operaciones/ibm no se expone por internet
            if ruta.endswith("/ibm") and PRUEBA is not None:
                return self._json(404, {"error": "no_disponible_en_modo_prueba"})
            if ruta.endswith("/chat"):
                return self._json(200, resumen_chat())
            return self._json(200, IBM.estado(forzar="forzar=1" in self.path))

        # Modo prueba: páginas HTML → 410 si tiempo agotado
        if PRUEBA is not None and not PRUEBA.activa():
            ruta_limpia = urlparse(self.path).path
            es_pagina = ruta_limpia.endswith(".html") or not os.path.splitext(ruta_limpia)[1]
            ext = os.path.splitext(ruta_limpia)[1].lower()
            es_recurso_estatico = ext in (
                ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".ico",
                ".woff", ".woff2", ".ttf", ".mp4", ".wav",
            )
            if es_pagina and not es_recurso_estatico:
                return self._prueba_terminada_html()

        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/pages/index.html")
            self.end_headers()
            return

        # Bloquear listado de directorios en modo prueba
        if PRUEBA is not None:
            path_local = self.translate_path(self.path)
            if os.path.isdir(path_local):
                return self._json(403, {"error": "listado_no_permitido"})

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


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Servidor del tablero MATEO.",
        epilog=(
            "Modo prueba:\n"
            "  --prueba-horas 48  activa el modo prueba con 48 h de duracion.\n"
            "  El fin se guarda en data/clean/prueba_estado.json.\n"
            "  Para empezar una prueba NUEVA, borra ese archivo a mano.\n"
        ),
    )
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8600)))
    ap.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    # Modo prueba
    ap.add_argument("--prueba-horas", type=int, default=0,
                    help="Activa el modo prueba con N horas de duracion (0 = sin modo prueba).")
    ap.add_argument("--tope-chat", type=int, default=15,
                    help="Preguntas a Granite por persona (solo en modo prueba; defecto: 15).")
    ap.add_argument("--estado", default=None,
                    help="Ruta alternativa para el archivo de estado (util en tests).")
    ap.add_argument("--opiniones", default=None,
                    help="Ruta alternativa para el archivo de opiniones (util en tests).")
    # Opciones ocultas para tests
    ap.add_argument("--chat-falso", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    global CHAT, PRUEBA

    if args.chat_falso:
        CHAT = ChatBackend(chat_falso=True)

    if args.prueba_horas > 0:
        estado_path = args.estado or os.path.join(
            PROJECT_ROOT, "data", "clean", "prueba_estado.json"
        )
        opiniones_path = args.opiniones or os.path.join(
            PROJECT_ROOT, "data", "clean", "opiniones_prueba.jsonl"
        )
        PRUEBA = ModoPrueba(
            horas=args.prueba_horas,
            tope_chat=args.tope_chat,
            estado_path=estado_path,
            opiniones_path=opiniones_path,
        )
        # En modo prueba: escuchar solo en 127.0.0.1
        host = "127.0.0.1"
    else:
        host = args.host

    handler = partial(RangeHandler, directory=ROOT)
    srv = ThreadingHTTPServer((host, args.port), handler)
    CHAT.iniciar()

    if PRUEBA is not None:
        print(f"MATEO dashboard (MODO PRUEBA) -> http://localhost:{args.port}/pages/index.html")
        print(f"  fin de prueba: {PRUEBA.fin_legible()}")
        print(f"  tope por persona: {args.tope_chat} preguntas a Granite")
    else:
        print(f"MATEO dashboard -> http://localhost:{args.port}/pages/mateo.html")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
