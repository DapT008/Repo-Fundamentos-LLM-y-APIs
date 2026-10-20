"""
Parte 2: Agente con Google ADK (Agent Development Kit)
=======================================================
El ADK maneja automáticamente:
  - El loop de razonamiento (think → act → observe → repeat)
  - El historial de conversación
  - La invocación de herramientas
  - El parsing de respuestas del modelo

Desplegable en Cloud Run con un solo contenedor.
"""

import os
import re
import json
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Google ADK imports
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.common import Content, Part
from google.genai import types as genai_types

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────
PROJECT_ID   = os.getenv("GOOGLE_CLOUD_PROJECT", "tu-proyecto")
LOCATION     = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL        = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-001")
BACKEND_URL  = os.getenv("BACKEND_URL", "http://localhost:8000")
APP_NAME     = "llm-security-agent"

# ── Herramientas del agente ────────────────────────────────────────────────

def scan_text_for_threats(text: str) -> dict:
    """
    Analiza un texto buscando amenazas de seguridad (prompt injection,
    SQL injection, XSS, path traversal).

    Args:
        text: El texto a analizar

    Returns:
        Diccionario con la lista de amenazas encontradas y su severidad
    """
    WAF_RULES = {
        "prompt_injection": (
            r"ignore\s+(previous|prior|all)\s+instructions|"
            r"you\s+are\s+now\s+(in\s+)?developer\s+mode|"
            r"disregard\s+your\s+system\s+prompt|"
            r"act\s+as\s+(if\s+you\s+are\s+)?dan",
            "HIGH"
        ),
        "sql_injection": (
            r"(\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b).*\b(from|into|table|where)\b|"
            r"--\s*$|;\s*(drop|delete|update|insert)|"
            r"'\s*(or|and)\s+'?\d+'?\s*=\s*'?\d+'?",
            "HIGH"
        ),
        "xss": (
            r"<script[\s\S]*?>[\s\S]*?</script>|"
            r"javascript\s*:|"
            r"on(load|click|error|mouseover)\s*=",
            "MEDIUM"
        ),
        "path_traversal": (
            r"\.\./|\.\.\\|%2e%2e/|%252e%252e/",
            "MEDIUM"
        ),
        "sensitive_data": (
            r"/etc/(passwd|shadow|hosts)|"
            r"(api[_-]?key|secret[_-]?key|password)\s*=\s*\S+",
            "LOW"
        ),
    }

    threats = []
    text_lower = text.lower()

    for rule_name, (pattern, severity) in WAF_RULES.items():
        if re.search(pattern, text_lower, re.IGNORECASE | re.MULTILINE):
            threats.append({
                "rule": rule_name,
                "severity": severity,
                "description": f"Patrón de {rule_name.replace('_', ' ')} detectado"
            })

    return {
        "text_analyzed": text[:100] + "..." if len(text) > 100 else text,
        "threats_found": len(threats),
        "threats": threats,
        "safe": len(threats) == 0
    }


def calculate_llm_tco(
    monthly_requests: int,
    avg_tokens_per_request: int,
    provider: str = "vertex_gemini"
) -> dict:
    """
    Calcula el Costo Total de Propiedad (TCO) para un despliegue de LLM.

    Args:
        monthly_requests: Número de solicitudes por mes
        avg_tokens_per_request: Promedio de tokens por solicitud (entrada + salida)
        provider: Proveedor LLM ('vertex_gemini', 'openai_gpt4o', 'ollama_local')

    Returns:
        Análisis de costos mensual y anual desglosado
    """
    # Precios por 1M tokens (en USD, aproximados para 2025)
    pricing = {
        "vertex_gemini": {
            "input_per_1m":  0.075,   # Gemini 2.0 Flash
            "output_per_1m": 0.30,
            "infra_monthly": 0,       # serverless, sin infra fija
        },
        "openai_gpt4o": {
            "input_per_1m":  2.50,    # GPT-4o mini
            "output_per_1m": 10.00,
            "infra_monthly": 0,
        },
        "ollama_local": {
            "input_per_1m":  0,       # gratis, solo costo de VM
            "output_per_1m": 0,
            "infra_monthly": 150,     # VM n1-standard-4 + GPU T4 en GCP
        },
    }

    p = pricing.get(provider, pricing["vertex_gemini"])

    # Calcular tokens totales
    total_tokens_m = (monthly_requests * avg_tokens_per_request) / 1_000_000

    # Input = 60% del total, output = 40% (estimación típica)
    input_tokens_m  = total_tokens_m * 0.6
    output_tokens_m = total_tokens_m * 0.4

    api_cost    = (input_tokens_m * p["input_per_1m"]) + (output_tokens_m * p["output_per_1m"])
    infra_cost  = p["infra_monthly"]
    total_month = api_cost + infra_cost

    return {
        "provider": provider,
        "monthly_requests": monthly_requests,
        "total_tokens_per_month_millions": round(total_tokens_m, 2),
        "costs_usd": {
            "api_cost_monthly":   round(api_cost, 2),
            "infra_cost_monthly": round(infra_cost, 2),
            "total_monthly":      round(total_month, 2),
            "total_annual":       round(total_month * 12, 2),
        },
        "cost_per_request_usd": round(total_month / monthly_requests, 6) if monthly_requests > 0 else 0,
    }


def get_security_best_practices(topic: str) -> dict:
    """
    Devuelve mejores prácticas de seguridad para un tema específico.

    Args:
        topic: Tema de seguridad ('jwt', 'waf', 'rate_limiting', 'circuit_breaker', 'disaster_recovery')

    Returns:
        Lista de mejores prácticas con descripción y prioridad
    """
    practices = {
        "jwt": [
            {"practice": "Usar RS256 en producción (clave asimétrica)", "priority": "HIGH"},
            {"practice": "Access tokens cortos (15-30 min), refresh tokens largos (7 días)", "priority": "HIGH"},
            {"practice": "No almacenar JWTs en localStorage (usar httpOnly cookies)", "priority": "HIGH"},
            {"practice": "Implementar blacklist de tokens revocados en Redis", "priority": "MEDIUM"},
            {"practice": "Incluir jti (JWT ID) para permitir revocación individual", "priority": "MEDIUM"},
        ],
        "waf": [
            {"practice": "Actualizar patrones de detección mensualmente", "priority": "HIGH"},
            {"practice": "Modo aprendizaje antes de modo bloqueo en producción", "priority": "HIGH"},
            {"practice": "Registrar todos los bloqueos con contexto completo", "priority": "MEDIUM"},
            {"practice": "Alertas automáticas para clusters de ataques (>5 en 1 min)", "priority": "MEDIUM"},
            {"practice": "Whitelist de IPs para endpoints de admin", "priority": "LOW"},
        ],
        "rate_limiting": [
            {"practice": "Rate limiting por IP Y por usuario autenticado", "priority": "HIGH"},
            {"practice": "Ventana deslizante en lugar de ventana fija (evita ráfagas)", "priority": "HIGH"},
            {"practice": "Headers informativos: X-RateLimit-Remaining, Retry-After", "priority": "MEDIUM"},
            {"practice": "Límites diferenciados por tier (free/paid)", "priority": "MEDIUM"},
            {"practice": "Penalización progresiva para abusadores reincidentes", "priority": "LOW"},
        ],
        "circuit_breaker": [
            {"practice": "Threshold basado en tasa de error, no solo conteo", "priority": "HIGH"},
            {"practice": "Half-open state con un solo request de prueba", "priority": "HIGH"},
            {"practice": "Timeout agresivo en OPEN state (30-60s)", "priority": "MEDIUM"},
            {"practice": "Métricas de estado en dashboard de monitoring", "priority": "MEDIUM"},
            {"practice": "Alertas cuando el circuito se abre más de 3 veces por hora", "priority": "LOW"},
        ],
        "disaster_recovery": [
            {"practice": "RTO y RPO documentados y aprobados por negocio", "priority": "HIGH"},
            {"practice": "Pruebas de DR cada 6 meses (Game Day)", "priority": "HIGH"},
            {"practice": "Multi-region activo-activo para sistemas críticos", "priority": "HIGH"},
            {"practice": "Backups cifrados en región diferente con verificación", "priority": "MEDIUM"},
            {"practice": "Runbook automatizado para failover", "priority": "MEDIUM"},
        ],
    }

    topic_key = topic.lower().replace(" ", "_").replace("-", "_")
    result = practices.get(topic_key, [])

    if not result:
        available = list(practices.keys())
        return {"error": f"Tema '{topic}' no encontrado", "available_topics": available}

    return {
        "topic": topic,
        "practices": result,
        "total": len(result),
    }


# ── Construir el agente ADK ────────────────────────────────────────────────

security_agent = Agent(
    name="llm-security-assistant",
    model=MODEL,
    description="Asistente especializado en seguridad de sistemas LLM para el curso de Maestría BSG",
    instruction="""
Eres un asistente experto en seguridad de sistemas LLM para el curso de Maestría en
Ciencias de Datos de BSG Institute.

Tu especialidad abarca:
- Autenticación JWT y OAuth2
- Patrones de alta disponibilidad (Circuit Breaker, failover multi-proveedor)
- WAF (Web Application Firewall) y protección contra inyecciones
- Rate limiting y control de tráfico
- Análisis de costos TCO para infraestructura LLM
- Arquitectura (ADR, C4 Model, RFC)
- Disaster Recovery (RTO/RPO)

Cuando el usuario proporcione texto para analizar, usa la herramienta scan_text_for_threats.
Para preguntas sobre costos, usa calculate_llm_tco.
Para preguntas sobre mejores prácticas, usa get_security_best_practices.

Responde siempre en español, con ejemplos prácticos y código cuando sea relevante.
Sé preciso, académico pero accesible. Usa emojis ocasionalmente para hacer el contenido más visual.
    """,
    tools=[
        FunctionTool(scan_text_for_threats),
        FunctionTool(calculate_llm_tco),
        FunctionTool(get_security_best_practices),
    ],
)

# ── FastAPI App para Cloud Run ────────────────────────────────────────────

app = FastAPI(
    title="LLM Security Agent (ADK)",
    description="Agente de seguridad construido con Google ADK",
    version="1.0.0",
)

session_service = InMemorySessionService()
runner = Runner(
    agent=security_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default-session"
    user_id: str   = "anonymous"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tools_used: list[str] = []


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": security_agent.name, "model": MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Conversa con el agente de seguridad LLM."""
    try:
        # Crear o recuperar sesión
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=request.user_id,
            session_id=request.session_id,
        )
        if not session:
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=request.user_id,
                session_id=request.session_id,
            )

        # Construir mensaje de entrada
        content = Content(
            role="user",
            parts=[Part.from_text(text=request.message)]
        )

        # Ejecutar el agente
        final_response = ""
        tools_used = []

        async for event in runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=content,
        ):
            # Recopilar respuesta final del agente
            if event.is_final_response():
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            final_response += part.text

            # Registrar herramientas utilizadas
            if hasattr(event, "get_function_calls"):
                for fc in event.get_function_calls():
                    tools_used.append(fc.name)

        return ChatResponse(
            response=final_response or "No pude generar una respuesta.",
            session_id=request.session_id,
            tools_used=tools_used,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {str(e)}")


@app.delete("/sessions/{user_id}/{session_id}")
async def clear_session(user_id: str, session_id: str):
    """Elimina el historial de una sesión."""
    await session_service.delete_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    return {"message": "Sesión eliminada"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
