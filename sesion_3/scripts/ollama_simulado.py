#!/usr/bin/env python3
"""
Ollama Simulado — Plan B para clases sin GPU
=============================================
Levanta un servidor HTTP en el puerto 11434 que imita la API de Ollama.
Útil cuando:
  · La máquina no tiene GPU
  · No se puede instalar Ollama
  · Se quiere demostrar la app sin esperar a que cargue el modelo

Uso:
  python scripts/ollama_simulado.py
  # En otro terminal: export OLLAMA_URL=http://localhost:11434

Endpoints implementados:
  GET  /api/tags           → lista de modelos disponibles
  POST /api/generate       → generación simulada con stream
  GET  /                   → health check
"""

import asyncio
import json
import time
import random
from datetime import datetime
from aiohttp import web

PORT = 11434

# Respuestas simuladas por palabras clave
RESPONSES = {
    "jwt": (
        "Un JWT (JSON Web Token) es un estándar abierto (RFC 7519) para transmitir "
        "información de forma segura entre partes como un objeto JSON. "
        "Se compone de tres partes: Header, Payload y Signature, separadas por puntos. "
        "El Header especifica el algoritmo de firma (generalmente HS256 o RS256). "
        "El Payload contiene los 'claims' — afirmaciones sobre el usuario. "
        "La Signature garantiza que el token no fue modificado. "
        "Son ideales para autenticación stateless en microservicios."
    ),
    "circuit": (
        "El patrón Circuit Breaker (Martín Fowler, 2014) protege un sistema "
        "de fallos en cascada cuando un servicio externo falla repetidamente. "
        "Tiene tres estados: CERRADO (todo funciona normalmente), "
        "ABIERTO (se rechazan peticiones sin intentarlas — fail fast), "
        "y SEMIABIERTO (se permite una petición de prueba para verificar recuperación). "
        "El umbral típico es 5 fallos consecutivos para abrir, "
        "y 30 segundos de espera antes de pasar a SEMIABIERTO."
    ),
    "waf": (
        "Un WAF (Web Application Firewall) analiza el tráfico HTTP/HTTPS "
        "buscando patrones maliciosos antes de que lleguen a la aplicación. "
        "Para aplicaciones LLM, el WAF agrega protección contra prompt injection — "
        "el OWASP Top 10 para LLMs lo lista como LLM01. "
        "Los patrones más comunes incluyen: 'ignore previous instructions', "
        "inyección de delimitadores de sistema, y jailbreaks conocidos. "
        "Se implementa como middleware entre el cliente y el LLM."
    ),
    "arquitectura": (
        "La arquitectura de un sistema LLM en producción típicamente incluye: "
        "1) Una capa de API Gateway para autenticación y rate limiting, "
        "2) Un servicio de orquestación que gestiona el contexto de la conversación, "
        "3) El LLM (local con Ollama o remoto con Vertex AI / OpenAI), "
        "4) Un sistema de caché para respuestas frecuentes (Redis), "
        "5) Almacenamiento para el historial de conversaciones, "
        "y 6) Un sistema de observabilidad para monitorear latencia y costos."
    ),
    "costo": (
        "El análisis de costos TCO (Total Cost of Ownership) para un LLM en 24 meses "
        "debe incluir: costos de setup (horas de ingeniería × tarifa), "
        "costos de tokens LLM (precio por millón de tokens de entrada y salida), "
        "costos de infraestructura (Cloud Run, VMs, o Kubernetes), "
        "y costos de herramientas (monitoreo, CI/CD, vectorDB). "
        "Para 3.000 consultas/mes con 200 tokens promedio, "
        "Gemini Flash cuesta aproximadamente $37/mes, "
        "mientras que Ollama en una VM e2-standard-2 cuesta ~$30/mes."
    ),
}

DEFAULT_RESPONSE = (
    "Esta es una respuesta simulada del servidor Ollama de demostración. "
    "El servidor real de Ollama requiere GPU o una CPU potente para inferencia. "
    "En producción, reemplaza esta URL con tu instancia real de Ollama, "
    "o con un proveedor de API como Google Vertex AI o OpenAI. "
    "Para el laboratorio, puedo responder preguntas sobre: "
    "JWT, Circuit Breaker, WAF, arquitectura LLM, y análisis de costos. "
    "¡Intenta preguntarme sobre alguno de estos temas!"
)


def get_response(prompt: str) -> str:
    prompt_lower = prompt.lower()
    for keyword, response in RESPONSES.items():
        if keyword in prompt_lower:
            return response
    return DEFAULT_RESPONSE


async def handle_root(request: web.Request) -> web.Response:
    return web.Response(text="Ollama simulado v0.5.0 (demo)", status=200)


async def handle_tags(request: web.Request) -> web.Response:
    data = {
        "models": [
            {
                "name": "llama3.2:latest",
                "model": "llama3.2:latest",
                "modified_at": datetime.utcnow().isoformat() + "Z",
                "size": 2_019_375_000,
                "digest": "sha256:demo",
                "details": {
                    "format": "gguf",
                    "family": "llama",
                    "families": ["llama"],
                    "parameter_size": "3.2B",
                    "quantization_level": "Q4_K_M",
                },
            }
        ]
    }
    return web.json_response(data)


async def handle_generate(request: web.Request) -> web.StreamResponse:
    try:
        body = await request.json()
    except Exception:
        return web.Response(status=400, text="Invalid JSON")

    prompt = body.get("prompt", "")
    model = body.get("model", "llama3.2")
    stream = body.get("stream", True)

    response_text = get_response(prompt)

    if not stream:
        data = {
            "model": model,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "response": response_text,
            "done": True,
            "total_duration": random.randint(500_000_000, 2_000_000_000),
            "load_duration": random.randint(10_000_000, 50_000_000),
            "eval_count": len(response_text.split()),
        }
        return web.json_response(data)

    # Streaming: enviar token por token con pequeño delay
    resp = web.StreamResponse(
        status=200,
        headers={"Content-Type": "application/x-ndjson"},
    )
    await resp.prepare(request)

    words = response_text.split()
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        chunk = {
            "model": model,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "response": token,
            "done": False,
        }
        await resp.write((json.dumps(chunk) + "\n").encode())
        await asyncio.sleep(0.02)  # simular latencia de inferencia

    # Chunk final
    final = {
        "model": model,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "response": "",
        "done": True,
        "total_duration": random.randint(500_000_000, 2_000_000_000),
        "eval_count": len(words),
    }
    await resp.write((json.dumps(final) + "\n").encode())
    await resp.write_eof()
    return resp


def main():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/api/tags", handle_tags)
    app.router.add_post("/api/generate", handle_generate)

    print(f"🤖 Ollama Simulado iniciado en http://localhost:{PORT}")
    print(f"   Modelos disponibles: llama3.2:latest")
    print(f"   Endpoints: GET /api/tags, POST /api/generate")
    print(f"   Ctrl+C para detener\n")
    print(f"   Para usar con el backend:")
    print(f"   export OLLAMA_URL=http://localhost:{PORT}")
    print(f"   make backend\n")

    web.run_app(app, host="0.0.0.0", port=PORT, access_log=None)


if __name__ == "__main__":
    main()
