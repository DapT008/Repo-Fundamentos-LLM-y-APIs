"""
Parte 3: Agente en Cloud Run sin ADK
=====================================
Control total sobre el ciclo de vida:
  - Sistema de prompts personalizado
  - Historial de conversación manual
  - Llamada directa a Vertex AI Generative AI
  - Sin dependencias del ADK

Ventajas sobre ADK:
  - Menor overhead (sin framework)
  - Control exacto del contexto y tokens
  - Más fácil de depurar y personalizar
  - Compatible con cualquier modelo de Vertex AI

Cuándo preferir este enfoque:
  - Pipelines simples de Q&A
  - Cuando el loop de razonamiento no es necesario
  - Sistemas con herramientas muy específicas y controladas
"""

import os
import re
import time
import logging
import json
from typing import Optional
from dotenv import load_dotenv

import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession, Part, Content
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL      = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","msg":%(message)s}'
)
logger = logging.getLogger(__name__)

# ── Inicializar Vertex AI ──────────────────────────────────────────────────
if PROJECT_ID:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    model = GenerativeModel(
        model_name=MODEL,
        system_instruction="""
Eres un asistente experto en seguridad de sistemas LLM para el curso de Maestría
en Ciencias de Datos de BSG Institute.

Temas de especialización:
- Autenticación JWT y OAuth2 (RFC 6749)
- Patrones de alta disponibilidad: Circuit Breaker, failover multi-proveedor
- WAF: detección de prompt injection, SQL injection, XSS, path traversal
- Rate limiting: sliding window, token bucket
- Análisis de costos TCO para infraestructura LLM
- Arquitectura con ADR, C4 Model, RFC, PRD
- Disaster Recovery: estrategias RTO/RPO

Responde siempre en español con ejemplos prácticos.
Para código, usa Python o bash cuando sea relevante.
Sé preciso y académico pero accesible para estudiantes de maestría.
""",
    )
    logger.info('"Vertex AI inicializado"')
else:
    model = None
    logger.warning('"PROJECT_ID no configurado, modo demo activo"')

# ── Almacén de sesiones en memoria ────────────────────────────────────────
# En producción: usar Redis o Firestore
sessions: dict[str, list[dict]] = {}


# ── FastAPI App ────────────────────────────────────────────────────────────

app = FastAPI(
    title="LLM Security Agent (sin ADK)",
    description="Agente de seguridad con control directo sobre Vertex AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096)
    session_id: str = Field(default="default", max_length=64)


class ChatResponse(BaseModel):
    response: str
    session_id: str
    model: str
    latency_ms: int
    history_turns: int


class SessionInfo(BaseModel):
    session_id: str
    turns: int
    tokens_estimated: int


# ── Helpers ────────────────────────────────────────────────────────────────

def get_session_history(session_id: str) -> list[dict]:
    """Recupera el historial de una sesión, limitado a MAX_HISTORY_TURNS."""
    history = sessions.get(session_id, [])
    # Mantener solo los últimos N turnos para controlar el contexto
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-(MAX_HISTORY_TURNS * 2):]
        sessions[session_id] = history
    return history


def history_to_vertex_contents(history: list[dict]) -> list[Content]:
    """Convierte el historial de la sesión al formato de Vertex AI."""
    contents = []
    for turn in history:
        role = turn["role"]  # "user" o "model"
        contents.append(
            Content(
                role=role,
                parts=[Part.from_text(turn["content"])]
            )
        )
    return contents


def demo_response(message: str) -> str:
    """Respuesta demo cuando Vertex AI no está configurado."""
    msg_lower = message.lower()
    if "jwt" in msg_lower:
        return (
            "**JWT (JSON Web Token)** es un estándar (RFC 7519) para transmitir "
            "información de forma segura entre partes como un objeto JSON firmado.\n\n"
            "Estructura: `header.payload.signature`\n\n"
            "Ejemplo en Python:\n```python\nimport jwt\ntoken = jwt.encode("
            "{'sub': 'user1', 'exp': ...}, 'secret', algorithm='HS256')\n```"
        )
    if "circuit breaker" in msg_lower or "circuit_breaker" in msg_lower:
        return (
            "**Circuit Breaker** es un patrón que previene fallos en cascada.\n\n"
            "Estados: CERRADO → ABIERTO → SEMIABIERTO\n\n"
            "- **CERRADO**: operación normal, contando fallos\n"
            "- **ABIERTO**: rechaza requests, espera timeout de recuperación\n"
            "- **SEMIABIERTO**: prueba con un request para ver si el servicio se recuperó"
        )
    return (
        f"[MODO DEMO - configure GOOGLE_CLOUD_PROJECT para respuestas reales]\n\n"
        f"Tu pregunta: '{message}'\n\n"
        f"Temas disponibles: JWT, Circuit Breaker, WAF, Rate Limiting, TCO, ADR, C4"
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": MODEL,
        "vertex_configured": model is not None,
        "active_sessions": len(sessions),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Conversa con el agente de seguridad LLM."""
    start = time.time()

    if not model:
        # Modo demo sin Vertex AI
        response_text = demo_response(request.message)
        latency = int((time.time() - start) * 1000)
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            model="demo-mode",
            latency_ms=latency,
            history_turns=0,
        )

    try:
        # Recuperar historial de la sesión
        history = get_session_history(request.session_id)
        vertex_history = history_to_vertex_contents(history)

        # Iniciar chat con historial existente
        chat_session: ChatSession = model.start_chat(history=vertex_history)

        # Enviar mensaje
        response = await chat_session.send_message_async(
            request.message,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 2048,
                "top_p": 0.95,
            },
        )

        response_text = response.text

        # Actualizar historial
        if request.session_id not in sessions:
            sessions[request.session_id] = []
        sessions[request.session_id].extend([
            {"role": "user",  "content": request.message},
            {"role": "model", "content": response_text},
        ])

        latency = int((time.time() - start) * 1000)
        logger.info(
            f'"chat","session_id":"{request.session_id}",'
            f'"latency_ms":{latency},"history_turns":{len(history)//2}'
        )

        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            model=MODEL,
            latency_ms=latency,
            history_turns=len(sessions[request.session_id]) // 2,
        )

    except Exception as e:
        logger.error(f'"chat_error","error":"{str(e)}"')
        raise HTTPException(status_code=500, detail=f"Error al procesar: {str(e)}")


@app.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """Lista las sesiones activas con estadísticas."""
    result = []
    for sid, history in sessions.items():
        total_chars = sum(len(h["content"]) for h in history)
        result.append(SessionInfo(
            session_id=sid,
            turns=len(history) // 2,
            tokens_estimated=total_chars // 4,  # ~4 chars por token
        ))
    return result


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Elimina el historial de una sesión."""
    sessions.pop(session_id, None)
    return {"message": f"Sesión '{session_id}' eliminada"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
