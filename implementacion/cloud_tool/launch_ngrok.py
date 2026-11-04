"""
implementacion/cloud_tool/launch_ngrok.py
==========================================
Lanza el servidor FastAPI del Omnimorph Engine en localhost:8000
y abre un túnel ngrok público para importación directa en IBM watsonx Orchestrate.

Uso:
    .\.venv\Scripts\python.exe implementacion/cloud_tool/launch_ngrok.py

Qué hace:
  1. Arranca uvicorn (implementacion.cloud_tool.api_server:app) en un thread de fondo.
  2. Abre un túnel ngrok HTTP apuntando a localhost:8000.
  3. Imprime la URL pública ngrok (https://xxxx.ngrok-free.app) y
     la URL exacta del OpenAPI JSON para copiar en Orchestrate.
  4. Actualiza openapi_tool.yaml con la URL pública.
  5. Permanece activo (CTRL+C para detener).

Requisitos:
  - fastapi, uvicorn, pyngrok instalados en .venv
  - (Opcional) cuenta ngrok gratuita: exportar NGROK_AUTHTOKEN=<tu-token> en .env
    Si no hay token, ngrok funciona igual pero con sesión de 2h.

Reglas IBM: cero secrets en código — el authtoken se lee desde .env.
"""

from __future__ import annotations

import os
import pathlib
import sys
import threading
import time

# ---------------------------------------------------------------------------
# Cargar .env para NGROK_AUTHTOKEN (opcional pero recomendado)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Asegurar sys.path
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_OPENAPI_YAML = pathlib.Path(__file__).parent / "openapi_tool.yaml"
PORT = 8000


def _start_uvicorn():
    """Inicia uvicorn en un thread de fondo (no bloqueante)."""
    import uvicorn
    # Cambiar al directorio raíz para que las rutas relativas de datos funcionen
    original_dir = os.getcwd()
    os.chdir(str(_ROOT))
    try:
        uvicorn.run(
            "implementacion.cloud_tool.api_server:app",
            host="127.0.0.1",
            port=PORT,
            log_level="warning",  # silencioso para no saturar consola
            app_dir=str(_ROOT),
        )
    finally:
        os.chdir(original_dir)


def _update_openapi_yaml(public_url: str) -> None:
    """Reemplaza la URL del servidor local en openapi_tool.yaml con la URL pública de ngrok."""
    if not _OPENAPI_YAML.exists():
        print(f"[launch_ngrok] AVISO: {_OPENAPI_YAML} no encontrado, no se pudo actualizar.")
        return

    content = _OPENAPI_YAML.read_text(encoding="utf-8")

    # Reemplazar la primera entrada de servers con la URL ngrok
    import re
    # Patrón para la URL del servidor ngrok anterior o localhost
    new_server_block = f'  - url: "{public_url}"\n    description: "Túnel ngrok activo (IBM watsonx Orchestrate)"\n'
    # Insertar al inicio del bloque servers (después de "servers:\n")
    content_new = re.sub(
        r'(servers:\n)(.*?)(  - url: "https://omnimorph-engine\.example\.com")',
        rf'\1{new_server_block}\3',
        content,
        flags=re.DOTALL,
    )
    if content_new == content:
        # Si el patrón de ejemplo no coincide, intentar reemplazar cualquier URL ngrok anterior
        content_new = re.sub(
            r'  - url: "https://[a-z0-9\-]+\.ngrok[^"]*"\n    description: "Túnel ngrok activo[^"]*"\n',
            new_server_block,
            content,
        )

    if content_new != content:
        _OPENAPI_YAML.write_text(content_new, encoding="utf-8")
        print(f"[launch_ngrok] openapi_tool.yaml actualizado con URL: {public_url}")
    else:
        print(f"[launch_ngrok] AVISO: No se pudo actualizar openapi_tool.yaml automáticamente.")
        print(f"               Edita manualmente 'servers[0].url' → '{public_url}'")


def main():
    print("=" * 65)
    print(" OMNIMORPH ENGINE — Servidor FastAPI + Túnel ngrok")
    print("=" * 65)

    # 1. Configurar ngrok auth token si está disponible
    ngrok_token = os.environ.get("NGROK_AUTHTOKEN", "").strip()

    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print("[launch_ngrok] ❌ pyngrok no instalado.")
        print("  Ejecuta: .venv/Scripts/pip.exe install pyngrok")
        sys.exit(1)

    if ngrok_token:
        conf.get_default().auth_token = ngrok_token
        print(f"[launch_ngrok] NGROK_AUTHTOKEN configurado ({ngrok_token[:8]}...)")
    else:
        print("[launch_ngrok] Sin NGROK_AUTHTOKEN — sesión ngrok de 2h (añade token en .env para sesión permanente)")

    # 2. Arrancar uvicorn en background
    print(f"\n[launch_ngrok] Iniciando uvicorn en localhost:{PORT} …")
    server_thread = threading.Thread(target=_start_uvicorn, daemon=True)
    server_thread.start()
    time.sleep(2)  # Dar tiempo a uvicorn para arrancar

    # Verificar que el servidor respondió
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
            print(f"[launch_ngrok] ✅ Servidor local OK: {r.read().decode()[:60]}")
    except Exception as exc:
        print(f"[launch_ngrok] ⚠️  Servidor local no responde aún: {exc}")
        print("  Esperando 3 segundos más …")
        time.sleep(3)

    # 3. Abrir túnel ngrok
    print("\n[launch_ngrok] Abriendo túnel ngrok …")
    try:
        tunnel = ngrok.connect(PORT, "http")
        public_url = tunnel.public_url
        # Forzar HTTPS
        if public_url.startswith("http://"):
            public_url = "https://" + public_url[7:]
        print(f"\n{'='*65}")
        print(f" ✅ TÚNEL ACTIVO")
        print(f"{'='*65}")
        print(f" URL pública: {public_url}")
        print(f" Endpoint   : {public_url}/process")
        print(f" OpenAPI JSON: {public_url}/openapi.json")
        print(f" Docs Swagger: {public_url}/docs")
        print(f"{'='*65}")
        print(f"\n📋 PASOS PARA IMPORTAR EN IBM WATSONX ORCHESTRATE:")
        print(f"  1. Abre: https://dl.watson-orchestrate.ibm.com")
        print(f"  2. Ve a: Skills & Tools → Add tool → Import from OpenAPI file")
        print(f"  3. Usa el archivo: implementacion/cloud_tool/openapi_tool.yaml")
        print(f"     (o la URL directa del JSON: {public_url}/openapi.json)")
        print(f"  4. Confirma que el server URL sea: {public_url}")
        print(f"  5. Añade la skill al agente y prueba en el chat:")
        print(f'     "Analiza el clip del Mundial 2014"')
        print(f"\n  CTRL+C para detener el servidor y cerrar el túnel.\n")

        # Actualizar openapi_tool.yaml con la URL real
        _update_openapi_yaml(public_url)

    except Exception as exc:
        print(f"[launch_ngrok] ❌ Error abriendo túnel: {exc}")
        print("  Verifica que ngrok esté disponible o añade NGROK_AUTHTOKEN en .env")
        print(f"\n  Sin ngrok, el servidor local sigue activo en http://localhost:{PORT}")
        print(f"  Para importar en Orchestrate necesitas una URL pública HTTPS.")
        public_url = f"http://localhost:{PORT}"

    # 4. Mantener activo
    print("[launch_ngrok] Servidor activo. Presiona CTRL+C para detener.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[launch_ngrok] Cerrando túnel y servidor …")
        try:
            ngrok.kill()
        except Exception:
            pass
        print("[launch_ngrok] ✅ Servidor detenido.")


if __name__ == "__main__":
    main()
