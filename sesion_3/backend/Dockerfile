# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Dependencias del sistema para compilar wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias primero (cache de Docker)
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Usuario no-root para seguridad
RUN useradd -m -u 1000 appuser

# Copiar dependencias del builder
COPY --from=builder /install /usr/local

# Copiar código de la aplicación
COPY app/ ./app/

# Directorio de logs con permisos correctos
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

USER appuser

# Variables de entorno por defecto (sobreescribir en docker-compose o Cloud Run)
ENV PORT=8000
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Health check para Kubernetes/Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
