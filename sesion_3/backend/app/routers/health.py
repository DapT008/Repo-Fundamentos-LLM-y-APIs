"""
Health Check Router — Tema 5: Alta Disponibilidad

Estándar de health checks en microservicios:
  GET /api/health          → estado general (liveness + readiness)
  GET /api/health/detailed → detalles de cada dependencia
  GET /api/health/circuit  → estado del circuit breaker Ollama
"""

import asyncio
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.circuit_breaker import ollama_cb

router = APIRouter()

# Tiempo de inicio (para calcular uptime)
START_TIME = time.time()


# ── Modelos ──────────────────────────────────────────────────────────────────

class DependencyStatus(BaseModel):
    name: str
    status: str       # "ok" | "degraded" | "down"
    latency_ms: float | None = None
    details: dict = {}


class HealthResponse(BaseModel):
    status: str       # "healthy" | "degraded" | "unhealthy"
    timestamp: str
    version: str
    uptime_seconds: float
    dependencies: list[DependencyStatus]
    circuit_breaker: dict


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check completo del servicio",
)
async def health_check():
    """
    Verifica el estado de todos los componentes del servicio.

    Retorna:
      - **healthy**: todos los componentes funcionan
      - **degraded**: el servicio funciona pero algún componente está lento o fallando
      - **unhealthy**: el servicio no puede atender peticiones correctamente

    Kubernetes usa este endpoint para:
      - **liveness**: si unhealthy → reiniciar el pod
      - **readiness**: si degraded → quitar del load balancer temporalmente
    """
    deps = await asyncio.gather(
        _check_ollama(),
        _check_disk(),
        return_exceptions=True,
    )

    dependency_list: list[DependencyStatus] = []
    for dep in deps:
        if isinstance(dep, Exception):
            dependency_list.append(DependencyStatus(
                name="unknown", status="down", details={"error": str(dep)}
            ))
        else:
            dependency_list.append(dep)

    # Estado general
    statuses = {d.status for d in dependency_list}
    if "down" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.VERSION,
        uptime_seconds=round(time.time() - START_TIME, 1),
        dependencies=dependency_list,
        circuit_breaker=ollama_cb.status_dict(),
    )


@router.get(
    "/health/circuit",
    summary="Estado del circuit breaker de Ollama",
)
async def circuit_status():
    """
    Detalle del estado del circuit breaker que protege las llamadas a Ollama.

    Estados posibles:
      - **CERRADO**: Ollama responde con normalidad
      - **SEMIABIERTO**: probando si Ollama se recuperó
      - **ABIERTO**: Ollama no responde; peticiones rechazadas con fail-fast
    """
    return ollama_cb.status_dict()


# ── Verificaciones internas ───────────────────────────────────────────────────

async def _check_ollama() -> DependencyStatus:
    """Ping a Ollama con timeout estricto."""
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
        latency = (time.time() - start) * 1000

        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return DependencyStatus(
                name="ollama",
                status="ok",
                latency_ms=round(latency, 1),
                details={"models_disponibles": models[:5]},
            )
        return DependencyStatus(
            name="ollama",
            status="degraded",
            latency_ms=round(latency, 1),
            details={"http_status": resp.status_code},
        )
    except Exception as e:
        return DependencyStatus(
            name="ollama",
            status="down",
            details={
                "error": str(e),
                "hint": "¿Está Ollama corriendo? → ollama serve",
            },
        )


async def _check_disk() -> DependencyStatus:
    """Verifica que hay espacio suficiente en disco para el audit log."""
    import shutil
    from pathlib import Path
    check_path = str(Path(settings.AUDIT_LOG_PATH).parent.resolve())
    usage = shutil.disk_usage(check_path)
    free_pct = (usage.free / usage.total) * 100
    disk_status = "ok" if free_pct > 10 else "degraded"
    return DependencyStatus(
        name="disk",
        status=disk_status,
        details={
            "free_pct": round(free_pct, 1),
            "free_gb": round(usage.free / 1e9, 2),
            "path": check_path,
        },
    )
