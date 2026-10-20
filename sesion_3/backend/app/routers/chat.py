"""
Chat Router — Tema 5: Seguridad en el despliegue de LLM

Demuestra cómo proteger un endpoint de chat con:
  · Autenticación JWT (scope 'read')
  · Rate limiting estricto (10 req/min por usuario)
  · Circuit breaker (Ollama)
  · Detección básica de prompt injection
  · Audit log de cada petición
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

import re

import httpx
import structlog

from app.routers.auth import get_current_user, TokenData
from app.routers.security import WAF_RULES
from app.services.circuit_breaker import ollama_cb, CircuitBreakerOpenError
from app.services.audit_logger import AuditLogger, AuditEvent
from app.core.config import settings

router = APIRouter()
logger = structlog.get_logger(__name__)


# ── Modelos ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mensaje del usuario para el LLM",
        examples=["¿Qué es un circuit breaker?"],
    )
    model: str = Field(
        default="llama3.2:3b",
        description="Modelo Ollama a usar",
        examples=["llama3.2", "mistral", "phi3"],
    )
    max_tokens: int = Field(default=500, ge=50, le=2000)


class ChatResponse(BaseModel):
    response: str
    model: str
    tokens_used: int | None = None
    circuit_state: str


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat con LLM local (Ollama) — protegido con JWT",
)
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Envía un mensaje al LLM local (Ollama) y retorna la respuesta.

    **Requiere**: Bearer token (scope `read` como mínimo).

    **Protecciones activas:**
    - 🔐 JWT: solo usuarios autenticados
    - 🛡️ WAF básico: detección de prompt injection
    - ⚡ Circuit breaker: si Ollama falla, retorna error inmediato
    - 📋 Audit log: toda petición queda registrada
    """
    audit = AuditLogger.get()
    ip = request.client.host if request.client else "unknown"

    # 1. WAF: detectar amenazas de alta severidad antes de enviar al LLM
    for rule_name, rule in WAF_RULES.items():
        if rule["severity"] != "HIGH":
            continue
        for pattern in rule["patterns"]:
            if re.search(pattern, body.message, re.IGNORECASE):
                await audit.log(
                    AuditEvent.WAF_BLOCK,
                    user=current_user.sub,
                    ip=ip,
                    severity="WARNING",
                    details={
                        "rule": rule_name,
                        "pattern_matched": pattern,
                        "message_preview": body.message[:100],
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mensaje rechazado por políticas de seguridad.",
                )

    # 2. Registrar petición en audit log
    await audit.log(
        AuditEvent.CHAT_REQUEST,
        user=current_user.sub,
        ip=ip,
        details={"model": body.model, "message_length": len(body.message)},
    )

    # 3. Llamar a Ollama con protección del circuit breaker
    try:
        response_text = await ollama_cb.call(
            _call_ollama,
            message=body.message,
            model=body.model,
            max_tokens=body.max_tokens,
        )
    except CircuitBreakerOpenError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Ollama no respondió a tiempo. Intenta con un mensaje más corto.",
        )
    except Exception as e:
        logger.error("Error llamando a Ollama", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error del servicio LLM. Consulte los logs para más detalles.",
        )

    return ChatResponse(
        response=response_text,
        model=body.model,
        circuit_state=ollama_cb.state.value,
    )


# ── Función de llamada a Ollama ───────────────────────────────────────────────

async def _call_ollama(message: str, model: str, max_tokens: int) -> str:
    """
    Llama a la API de Ollama.
    Esta función es la que el circuit breaker envuelve.
    """
    async with httpx.AsyncClient(timeout=settings.OLLAMA_TIMEOUT) as client:
        payload = {
            "model": model,
            "prompt": message,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        resp = await client.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
