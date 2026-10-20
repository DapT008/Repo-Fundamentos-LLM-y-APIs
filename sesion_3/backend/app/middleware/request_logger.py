"""
Request Logger Middleware — Tema 5: Monitoreo y Logging

Structured logging de cada petición HTTP en formato JSON.
Facilita la búsqueda y análisis en herramientas como:
  · Cloud Logging (GCP)
  · CloudWatch (AWS)
  · Datadog, Grafana Loki, ELK Stack
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Registra cada petición HTTP con:
      · request_id único (para correlacionar logs en sistemas distribuidos)
      · método, ruta, código de estado
      · latencia en milisegundos
      · IP del cliente

    El formato JSON estructurado permite queries como:
      # Todas las peticiones con latencia > 1000ms
      jq '. | select(.latency_ms > 1000)' logs/app.jsonl
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generar un ID único para esta petición
        request_id = str(uuid.uuid4())[:8]

        start = time.time()

        # Propagar el request_id al contexto de los logs subsecuentes
        structlog.contextvars.bind_contextvars(request_id=request_id)

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request_error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error=str(exc),
                latency_ms=round((time.time() - start) * 1000, 1),
            )
            raise
        finally:
            structlog.contextvars.clear_contextvars()

        latency_ms = round((time.time() - start) * 1000, 1)

        # No loguear health checks en debug para evitar ruido
        is_health = request.url.path in ("/api/health", "/", "/docs", "/redoc", "/openapi.json")
        log_level = "debug" if is_health else "info"

        getattr(logger, log_level)(
            "http_request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_ms=latency_ms,
            ip=request.client.host if request.client else "unknown",
        )

        # Agregar el request_id a la respuesta para debugging
        response.headers["X-Request-ID"] = request_id
        return response
