"""
Configuración centralizada con Pydantic Settings.
Lee variables de entorno o del archivo backend/.env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Aplicación ──────────────────────────────────────────────────────────
    APP_NAME: str = "LLM Security Lab · Sesión 3"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── JWT (Tema 5) ─────────────────────────────────────────────────────────
    # IMPORTANTE: en producción usar un secreto aleatorio largo (256 bits):
    #   python -c "import secrets; print(secrets.token_hex(32))"
    JWT_SECRET_KEY: str = "CAMBIA_ESTE_SECRETO_EN_PRODUCCION_abc123xyz789"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Rate Limiting (Tema 5) ───────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60     # peticiones por IP por minuto
    RATE_LIMIT_CHAT_PER_MINUTE: int = 10  # límite más estricto para chat LLM

    # ── Circuit Breaker (Tema 5) ─────────────────────────────────────────────
    CB_FAILURE_THRESHOLD: int = 5    # fallos antes de abrir el circuito
    CB_RECOVERY_TIMEOUT: int = 30    # segundos en estado ABIERTO antes de probar

    # ── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT: int = 120         # segundos máximos por respuesta

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000", "http://localhost:8080"]
    )

    # ── Audit Log (Tema 5) ───────────────────────────────────────────────────
    AUDIT_LOG_PATH: str = "logs/audit.jsonl"
    AUDIT_LOG_MAX_ENTRIES: int = 10_000

    # ── Base de datos (SQLite en dev) ────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./llm_security_lab.db"

    # ── GCP / Vertex AI (Tema 6 — agent platform) ───────────────────────────
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    VERTEX_AI_ENDPOINT: str = ""


settings = Settings()
