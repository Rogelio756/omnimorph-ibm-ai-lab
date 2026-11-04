"""
deploy_code_engine.py
=====================
Despliega el Omnimorph Engine API Server en IBM Cloud Code Engine
usando la API REST de IBM Cloud directamente (sin Docker local ni ibmcloud CLI).

Estrategia: Code Engine "Source-to-Image" desde un repositorio GitHub público.
El build ocurre 100% en la nube IBM -- no requiere Docker instalado localmente.

Uso:
    .\.venv\Scripts\python.exe deploy_code_engine.py

Qué hace:
  1. Autentica con IBM Cloud usando IBM_CLOUD_API_KEY del .env
  2. Lista los proyectos de Code Engine disponibles en tu cuenta
  3. Crea (o reutiliza) la app "omnimorph-engine" en Code Engine
  4. Dispara un build desde el repositorio GitHub
  5. Espera a que el build y el deploy terminen
  6. Imprime la URL pública HTTPS de la app
  7. Actualiza openapi_tool.yaml con la URL real

Pre-requisitos:
  - IBM_CLOUD_API_KEY en .env
  - El código subido a un repositorio GitHub público (o privado con token)
  - GITHUB_REPO_URL en .env (ej: https://github.com/tu-usuario/omnimorph-ibm-ai-lab)

Reglas IBM: cero secrets en código -- todo desde .env.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Forzar UTF-8 en stdout para Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
_ROOT = pathlib.Path(__file__).parent
_OPENAPI_YAML = _ROOT / "implementacion" / "cloud_tool" / "openapi_tool.yaml"

APP_NAME       = "omnimorph-engine"
APP_PORT       = 8000
IBM_IAM_URL    = "https://iam.cloud.ibm.com/identity/token"
CE_API_BASE    = "https://api.{region}.codeengine.cloud.ibm.com/v2"
CE_REGION      = os.environ.get("CE_REGION", "eu-gb")   # Londres (donde está tu Orchestrate)

# Rama y ruta del Dockerfile en el repo
GITHUB_REPO    = os.environ.get("GITHUB_REPO_URL", "").strip()
GITHUB_BRANCH  = os.environ.get("GITHUB_BRANCH", "main").strip()
GITHUB_TOKEN   = os.environ.get("GITHUB_TOKEN", "").strip()  # solo si repo privado
DOCKERFILE_PATH = "Dockerfile"

# ---------------------------------------------------------------------------
# 1. Obtener token IAM
# ---------------------------------------------------------------------------

def get_iam_token(api_key: str) -> str:
    resp = requests.post(
        IBM_IAM_URL,
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print(f"[deploy] [OK] Token IAM obtenido")
    return token


# ---------------------------------------------------------------------------
# 2. Listar proyectos Code Engine
# ---------------------------------------------------------------------------

def list_ce_projects(token: str, region: str) -> list:
    url = CE_API_BASE.format(region=region) + "/projects"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("projects", [])


# ---------------------------------------------------------------------------
# 3. Crear o reutilizar proyecto Code Engine
# ---------------------------------------------------------------------------

def get_or_create_project(token: str, region: str, project_name: str = "omnimorph-project") -> str:
    projects = list_ce_projects(token, region)
    for p in projects:
        if p.get("name") == project_name:
            pid = p["id"]
            print(f"[deploy] Proyecto existente: {project_name} (id={pid[:8]}...)")
            return pid

    # Crear nuevo proyecto
    url = CE_API_BASE.format(region=region) + "/projects"
    resp = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"name": project_name},
        timeout=30,
    )
    resp.raise_for_status()
    pid = resp.json()["id"]
    print(f"[deploy] [OK] Proyecto creado: {project_name} (id={pid[:8]}...)")
    # Esperar a que el proyecto esté listo
    _wait_project_ready(token, region, pid)
    return pid


def _wait_project_ready(token: str, region: str, project_id: str, max_wait: int = 120) -> None:
    url = CE_API_BASE.format(region=region) + f"/projects/{project_id}"
    for _ in range(max_wait // 5):
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
        if resp.ok:
            status = resp.json().get("status", "")
            if status == "active":
                print(f"[deploy] [OK] Proyecto activo")
                return
        print(f"[deploy] Esperando proyecto... ({status})")
        time.sleep(5)
    print(f"[deploy] [!!] Timeout esperando proyecto -- continuando de todas formas")


# ---------------------------------------------------------------------------
# 4. Crear o actualizar la app en Code Engine
# ---------------------------------------------------------------------------

def deploy_app(token: str, region: str, project_id: str, image_ref: str | None = None) -> dict:
    """
    Crea o actualiza la app 'omnimorph-engine' en Code Engine.
    Si image_ref es None, usa build desde Dockerfile.
    """
    base = CE_API_BASE.format(region=region) + f"/projects/{project_id}/apps"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    app_payload = {
        "name": APP_NAME,
        "image_port": APP_PORT,
        "scale_min_instances": 0,   # scale-to-zero para ahorrar recursos del trial
        "scale_max_instances": 1,
        "scale_concurrency": 10,
        "run_env_variables": [
            # Las variables de entorno se inyectan desde el .env del CE secret
            # (configuradas manualmente en la consola o via API)
        ],
    }

    if image_ref:
        app_payload["image_reference"] = image_ref

    # Verificar si ya existe
    check = requests.get(f"{base}/{APP_NAME}", headers=headers, timeout=15)
    if check.status_code == 200:
        # Actualizar (PATCH)
        resp = requests.patch(
            f"{base}/{APP_NAME}",
            headers={**headers, "If-Match": check.headers.get("Etag", "*")},
            json=app_payload,
            timeout=30,
        )
        action = "actualizada"
    else:
        # Crear (POST)
        resp = requests.post(base, headers=headers, json=app_payload, timeout=30)
        action = "creada"

    resp.raise_for_status()
    app = resp.json()
    print(f"[deploy] [OK] App {action}: {APP_NAME}")
    return app


# ---------------------------------------------------------------------------
# 5. Crear un build desde el repositorio GitHub
# ---------------------------------------------------------------------------

def create_build(token: str, region: str, project_id: str, repo_url: str, branch: str) -> str:
    """Crea un build config en Code Engine apuntando al repo GitHub."""
    url = CE_API_BASE.format(region=region) + f"/projects/{project_id}/builds"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    build_name = f"{APP_NAME}-build"
    output_image = f"private.icr.io/omnimorph/{APP_NAME}:latest"

    payload = {
        "name": build_name,
        "strategy_type": "dockerfile",
        "strategy_size": "medium",
        "source_url": repo_url,
        "source_revision": branch,
        "source_context_dir": ".",
        "strategy_spec_file": DOCKERFILE_PATH,
        "output_image": output_image,
    }

    # Añadir token GitHub si es repo privado
    if GITHUB_TOKEN:
        payload["source_secret"] = "github-secret"

    # Verificar si ya existe el build config
    check = requests.get(f"{url}/{build_name}", headers=headers, timeout=15)
    if check.status_code == 200:
        resp = requests.patch(
            f"{url}/{build_name}",
            headers={**headers, "If-Match": check.headers.get("Etag", "*")},
            json=payload,
            timeout=30,
        )
    else:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)

    resp.raise_for_status()
    print(f"[deploy] [OK] Build config creado: {build_name}")
    return build_name


def trigger_build_run(token: str, region: str, project_id: str, build_name: str) -> str:
    """Dispara una ejecución del build y retorna el buildrun_name."""
    url = CE_API_BASE.format(region=region) + f"/projects/{project_id}/build_runs"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        url,
        headers=headers,
        json={"build_name": build_name},
        timeout=30,
    )
    resp.raise_for_status()
    run_name = resp.json()["name"]
    print(f"[deploy] [OK] Build disparado: {run_name}")
    return run_name


def wait_build_run(token: str, region: str, project_id: str, run_name: str, max_wait: int = 600) -> bool:
    """Espera hasta que el build termine (succeeded o failed)."""
    url = CE_API_BASE.format(region=region) + f"/projects/{project_id}/build_runs/{run_name}"
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[deploy] Esperando build... (puede tomar 3-5 minutos)")
    for i in range(max_wait // 10):
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.ok:
            status = resp.json().get("status", "")
            elapsed = i * 10
            print(f"[deploy]   {elapsed}s -- status: {status}", end="\r")
            if status == "succeeded":
                print(f"\n[deploy] [OK] Build completado exitosamente")
                return True
            if status in ("failed", "cancelled"):
                print(f"\n[deploy] [FAIL] Build falló: {status}")
                return False
        time.sleep(10)
    print(f"\n[deploy] [!!] Timeout esperando build")
    return False


# ---------------------------------------------------------------------------
# 6. Obtener la URL pública de la app
# ---------------------------------------------------------------------------

def get_app_url(token: str, region: str, project_id: str) -> str | None:
    url = CE_API_BASE.format(region=region) + f"/projects/{project_id}/apps/{APP_NAME}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if resp.ok:
        # URL pública está en el campo "endpoint"
        endpoint = resp.json().get("endpoint", "")
        if endpoint:
            return endpoint
    return None


# ---------------------------------------------------------------------------
# 7. Actualizar openapi_tool.yaml con la URL real
# ---------------------------------------------------------------------------

def update_openapi_yaml(public_url: str) -> None:
    if not _OPENAPI_YAML.exists():
        print(f"[deploy] AVISO: {_OPENAPI_YAML} no encontrado")
        return

    import re
    content = _OPENAPI_YAML.read_text(encoding="utf-8")
    new_server = f'  - url: "{public_url}"\n    description: "IBM Cloud Code Engine (produccion)"\n'

    # Reemplazar el placeholder ngrok o cualquier URL de CE anterior
    content_new = re.sub(
        r'  - url: "https://[a-z0-9\-]+\.ngrok[^"]*"\n    description: "[^"]*"\n',
        new_server,
        content,
    )
    if content_new == content:
        # Reemplazar el placeholder genérico
        content_new = content.replace(
            '  - url: "https://REEMPLAZAR-CON-URL-NGROK.ngrok-free.app"\n'
            '    description: "Túnel ngrok activo (IBM watsonx Orchestrate) -- ejecuta launch_ngrok.py para obtener la URL real"\n',
            new_server,
        )

    if content_new != content:
        _OPENAPI_YAML.write_text(content_new, encoding="utf-8")
        print(f"[deploy] [OK] openapi_tool.yaml actualizado: {public_url}")
    else:
        print(f"[deploy] [!!] No se pudo actualizar openapi_tool.yaml automáticamente")
        print(f"         Edita manualmente servers[0].url → '{public_url}'")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print(" OMNIMORPH -- Deploy en IBM Cloud Code Engine")
    print("=" * 60)

    # Verificar credenciales
    api_key = os.environ.get("IBM_CLOUD_API_KEY", "").strip()
    if not api_key:
        print("[FAIL] IBM_CLOUD_API_KEY no configurado en .env")
        sys.exit(1)

    if not GITHUB_REPO:
        print("\n[!!]  GITHUB_REPO_URL no configurado en .env")
        print("   Code Engine necesita el código en un repositorio Git para hacer el build.")
        print("   Agrega en .env:")
        print("   GITHUB_REPO_URL=https://github.com/tu-usuario/omnimorph-ibm-ai-lab")
        print("\n   Alternativa: subir el YAML directamente en Orchestrate UI")
        print("   (sin servidor activo, solo para registrar la skill)")
        _show_manual_instructions()
        sys.exit(0)

    print(f"\n[deploy] Región Code Engine: {CE_REGION}")
    print(f"[deploy] Repo GitHub: {GITHUB_REPO}")
    print(f"[deploy] Rama: {GITHUB_BRANCH}")

    # Paso 1: IAM token
    token = get_iam_token(api_key)

    # Paso 2: Proyecto
    project_id = get_or_create_project(token, CE_REGION)

    # Paso 3: Build config
    build_name = create_build(token, CE_REGION, project_id, GITHUB_REPO, GITHUB_BRANCH)

    # Paso 4: Disparar build
    run_name = trigger_build_run(token, CE_REGION, project_id, build_name)

    # Paso 5: Esperar build
    success = wait_build_run(token, CE_REGION, project_id, run_name)
    if not success:
        print("[FAIL] El build falló. Revisa los logs en IBM Cloud Console → Code Engine → Builds")
        sys.exit(1)

    # Paso 6: Desplegar app
    deploy_app(token, CE_REGION, project_id)

    # Paso 7: Obtener URL
    print("\n[deploy] Esperando URL de la app...")
    for _ in range(12):
        url = get_app_url(token, CE_REGION, project_id)
        if url:
            break
        time.sleep(10)

    if url:
        print(f"\n{'='*60}")
        print(f" [OK] DEPLOY COMPLETADO")
        print(f"{'='*60}")
        print(f" URL pública: {url}")
        print(f" Endpoint   : {url}/process")
        print(f" Health     : {url}/health")
        print(f" OpenAPI    : {url}/openapi.json")
        print(f"{'='*60}")
        update_openapi_yaml(url)
        print(f"\n Siguiente paso: importar openapi_tool.yaml en Orchestrate UI")
        print(f" -> Skills & Tools -> Add tool -> Import from OpenAPI file")
    else:
        print("[deploy] [!!] URL no disponible aún -- verifica en IBM Cloud Console")
        print("         https://cloud.ibm.com/codeengine/projects")


def _show_manual_instructions():
    print("\n" + "=" * 60)
    print(" INSTRUCCIONES ALTERNATIVAS -- Sin repo Git")
    print("=" * 60)
    print("""
 Para importar la herramienta en Orchestrate SIN servidor activo:

 1. Abre: https://dl.watson-orchestrate.ibm.com
 2. Skills & Tools → Add tool → Import from OpenAPI file
 3. Sube: implementacion/cloud_tool/openapi_tool.yaml
    (Orchestrate registrará la skill aunque la URL sea placeholder)
 4. La skill aparecerá como disponible para añadir a agentes
 5. Para ejecutarla, necesitas el servidor activo (Code Engine o ngrok)

 Para subir el código a GitHub y usar Code Engine:
   git init
   git add implementacion/ Dockerfile requirements-api.txt
   git remote add origin https://github.com/tu-usuario/omnimorph-ibm-ai-lab
   git push -u origin main
   Luego añade GITHUB_REPO_URL en .env y re-ejecuta este script.
""")


if __name__ == "__main__":
    main()
