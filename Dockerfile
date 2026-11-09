# Dockerfile — Omnimorph Engine API Server
# Para despliegue en IBM Cloud Code Engine
#
# Build local (opcional):
#   docker build -t omnimorph-engine .
#   docker run -p 8000:8000 --env-file .env omnimorph-engine
#
# IBM Code Engine usa este Dockerfile automáticamente
# si está en la raíz del repositorio o en el context path.

FROM python:3.12-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=8000

WORKDIR /app

# Instalar dependencias del sistema (scipy necesita compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# Copiar el código del proyecto
# Solo los módulos necesarios para la API (sin datos pesados ni .venv)
COPY implementacion/ ./implementacion/
COPY data/raw/ ./data/raw/
# Configuración del partido activo (fps, equipos, sentido de ataque) que lee el engine
COPY data/partidos/ ./data/partidos/

# Puerto expuesto
EXPOSE 8000

# Comando de inicio
# CODE ENGINE: inyecta automáticamente la variable PORT
CMD ["sh", "-c", "uvicorn implementacion.cloud_tool.api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
