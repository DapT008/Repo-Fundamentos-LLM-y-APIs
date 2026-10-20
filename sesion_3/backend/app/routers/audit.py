"""
Audit Log Router — Tema 5: Monitoreo y Logging

GET /api/audit/logs      → últimas N entradas del log
GET /api/audit/integrity → verificar integridad de la cadena de hashes
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.routers.auth import require_scope, TokenData
from app.services.audit_logger import AuditLogger

router = APIRouter()


class IntegrityResult(BaseModel):
    ok: bool
    entries: int
    tampered_at: int | None = None
    message: str


@router.get(
    "/audit/logs",
    summary="Últimas entradas del audit log (requiere scope admin)",
)
async def get_audit_logs(
    n: int = Query(default=20, ge=1, le=200, description="Número de entradas a retornar"),
    current_user: TokenData = Depends(require_scope("admin")),
):
    """
    Retorna las últimas N entradas del audit log en orden cronológico descendente.

    **Requiere**: scope `admin`.

    Cada entrada incluye:
    - `timestamp`: fecha y hora UTC
    - `event`: tipo de evento (LOGIN_SUCCESS, WAF_BLOCK, etc.)
    - `severity`: INFO | WARNING | ERROR | CRITICAL
    - `user`: email del usuario (si aplica)
    - `ip`: dirección IP del cliente
    - `details`: datos adicionales del evento
    - `hash`: hash SHA-256 de esta entrada
    - `prev_hash`: hash de la entrada anterior (cadena de integridad)
    """
    audit = AuditLogger.get()
    entries = await audit.get_recent(n)
    return {"count": len(entries), "entries": entries}


@router.get(
    "/audit/integrity",
    response_model=IntegrityResult,
    summary="Verificar integridad de la cadena del audit log",
)
async def verify_integrity(
    current_user: TokenData = Depends(require_scope("admin")),
):
    """
    Verifica que el audit log no haya sido manipulado.

    Recorre toda la cadena de hashes SHA-256 y reporta:
    - `ok: true`: el log es íntegro (ninguna entrada fue modificada)
    - `ok: false, tampered_at: N`: la entrada N fue modificada o eliminada
    """
    audit = AuditLogger.get()
    result = await audit.verify_integrity()

    if result["ok"]:
        message = f"Log íntegro. {result['entries']} entradas verificadas."
    else:
        message = (
            f"¡ALERTA! Manipulación detectada en la entrada {result.get('tampered_at')}. "
            f"Notificar al equipo de seguridad de inmediato."
        )

    return IntegrityResult(
        ok=result["ok"],
        entries=result.get("entries", 0),
        tampered_at=result.get("tampered_at"),
        message=message,
    )
