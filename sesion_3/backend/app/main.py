"""
Sesión 3 · LLM Security Lab — Aplicación principal FastAPI

Temas cubiertos:
  T5 · Seguridad y Alta Disponibilidad:
        JWT/OAuth2, rate limiting, WAF simulado, circuit breaker,
        audit log, structured logging, health checks
  T6 · Diseño y Documentación:
        Plantillas ADR/RFC/C4, análisis de costos TCO

Swagger UI  →  http://localhost:8000/docs
ReDoc       →  http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.request_logger import RequestLoggerMiddleware
from app.routers import auth, chat, audit, health, architecture, security
from app.services.audit_logger import AuditLogger
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: arranque y apagado limpio
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa recursos al arrancar y los libera al apagar."""
    await AuditLogger.initialize()
    logger.info(
        "LLM Security Lab iniciado",
        version=settings.VERSION,
        ollama_url=settings.OLLAMA_URL,
    )
    yield
    logger.info("Apagando LLM Security Lab…")


# ---------------------------------------------------------------------------
# Instancia FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Security Lab · Sesión 3",
    description=(
        "Backend de demostración para **Tema 5** (Seguridad y Alta Disponibilidad) "
        "y **Tema 6** (Diseño y Documentación). "
        "Incluye JWT/OAuth2, rate limiting, WAF simulado, circuit breaker, "
        "audit log y plantillas de documentación arquitectónica."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# Middleware  (el orden importa: el último registrado se ejecuta primero)
# ---------------------------------------------------------------------------

# 1. CORS — permite peticiones del frontend React en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Cabeceras de seguridad HTTP (HSTS, CSP, X-Frame-Options…)
app.add_middleware(SecurityHeadersMiddleware)

# 3. Logging estructurado de cada petición
app.add_middleware(RequestLoggerMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

# Autenticación JWT + OAuth2  (Tema 5)
app.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

# Chat con LLM via Ollama     (Tema 5 — verificación JWT en endpoint)
app.include_router(chat.router, prefix="/api", tags=["Chat LLM"])

# Audit log                   (Tema 5)
app.include_router(audit.router, prefix="/api", tags=["Auditoría"])

# Security scan / WAF         (Tema 5)
app.include_router(security.router, prefix="/api/security", tags=["Seguridad"])

# Health checks / circuit breaker  (Tema 5)
app.include_router(health.router, prefix="/api", tags=["Salud del Servicio"])

# Documentación arquitectónica + análisis de costos  (Tema 6)
app.include_router(architecture.router, prefix="/api/architecture", tags=["Arquitectura (T6)"])

# ---------------------------------------------------------------------------
# Manejador global de errores no capturados
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Error no capturado",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Consulte los logs para más detalles."},
    )


# ---------------------------------------------------------------------------
# Raíz
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root():
    return {
        "servicio": "LLM Security Lab",
        "sesion": 3,
        "temas": ["T5 — Seguridad y Alta Disponibilidad", "T6 — Diseño y Documentación"],
        "docs": "/docs",
        "health": "/api/health",
    }
