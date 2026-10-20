"""
Audit Logger — Tema 5: Monitoreo y Logging

Registro inmutable de eventos de seguridad:
  · Cada entrada es una línea JSON (JSONL) con hash de integridad SHA-256
  · El hash encadena cada entrada con la anterior (como una cadena de bloques simple)
  · Permite detectar si el log fue manipulado después del hecho

Eventos registrados:
  LOGIN_SUCCESS, LOGIN_FAILURE, TOKEN_REFRESH, TOKEN_INVALID,
  RATE_LIMIT_HIT, WAF_BLOCK, CHAT_REQUEST, PERMISSION_DENIED,
  CIRCUIT_OPEN, CIRCUIT_CLOSE
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class AuditEvent(str, Enum):
    LOGIN_SUCCESS    = "LOGIN_SUCCESS"
    LOGIN_FAILURE    = "LOGIN_FAILURE"
    TOKEN_REFRESH    = "TOKEN_REFRESH"
    TOKEN_INVALID    = "TOKEN_INVALID"
    RATE_LIMIT_HIT   = "RATE_LIMIT_HIT"
    WAF_BLOCK        = "WAF_BLOCK"
    CHAT_REQUEST     = "CHAT_REQUEST"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CIRCUIT_OPEN     = "CIRCUIT_OPEN"
    CIRCUIT_CLOSE    = "CIRCUIT_CLOSE"
    HEALTH_CHECK     = "HEALTH_CHECK"
    COST_ANALYSIS    = "COST_ANALYSIS"


class AuditLogger:
    """
    Logger de auditoría append-only con hashing encadenado.

    El archivo .jsonl nunca se sobreescribe; solo se agregan líneas.
    Cada entrada incluye el hash SHA-256 de la entrada anterior,
    formando una cadena que detecta manipulaciones.
    """

    _instance: "AuditLogger | None" = None
    _class_lock = asyncio.Lock()  # protege la creación del singleton

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = "GENESIS"   # primer bloque de la cadena
        self._write_lock = asyncio.Lock()  # protege las escrituras al archivo

        # Leer último hash si el archivo ya existe
        if self.log_path.exists():
            self._last_hash = self._read_last_hash()

    # ── Inicialización singleton ─────────────────────────────────────────────

    @classmethod
    async def initialize(cls) -> "AuditLogger":
        async with cls._class_lock:
            if cls._instance is None:
                cls._instance = cls(settings.AUDIT_LOG_PATH)
                logger.info("Audit logger inicializado", path=settings.AUDIT_LOG_PATH)
        return cls._instance

    @classmethod
    def get(cls) -> "AuditLogger":
        if cls._instance is None:
            raise RuntimeError("AuditLogger no inicializado. Llama initialize() primero.")
        return cls._instance

    # ── Escritura ────────────────────────────────────────────────────────────

    async def log(
        self,
        event: AuditEvent,
        user: str | None = None,
        ip: str | None = None,
        details: dict | None = None,
        severity: str = "INFO",   # INFO | WARNING | ERROR | CRITICAL
    ) -> None:
        """Registra un evento de auditoría de forma asíncrona."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event.value,
            "severity": severity,
            "user": user,
            "ip": ip,
            "details": details or {},
            "prev_hash": self._last_hash,
        }

        # Calcular hash de esta entrada (sin el campo "hash" todavía)
        entry_json = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()
        entry["hash"] = entry_hash

        line = json.dumps(entry, ensure_ascii=False) + "\n"

        async with self._write_lock:
            await asyncio.to_thread(self._append_line, line)
            self._last_hash = entry_hash

        logger.info(
            "audit_entry",
            audit_event=event.value,
            user=user,
            ip=ip,
            severity=severity,
        )

    # ── Lectura ──────────────────────────────────────────────────────────────

    def _append_line(self, line: str) -> None:
        """Escribe una línea al archivo de log (operación bloqueante, ejecutar en thread)."""
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    def _read_lines(self) -> list[str]:
        """Lee todas las líneas del archivo (operación bloqueante, ejecutar en thread)."""
        return self.log_path.read_text(encoding="utf-8").strip().splitlines()

    async def get_recent(self, n: int = 50) -> list[dict]:
        """Retorna las últimas N entradas del log."""
        if not self.log_path.exists():
            return []

        lines = await asyncio.to_thread(self._read_lines)
        recent = lines[-n:] if len(lines) > n else lines
        return [json.loads(line) for line in reversed(recent)]

    async def verify_integrity(self) -> dict:
        """
        Verifica la integridad de la cadena de hashes.
        Retorna {'ok': True} o {'ok': False, 'tampered_at': index}.
        """
        if not self.log_path.exists():
            return {"ok": True, "entries": 0}

        lines = await asyncio.to_thread(self._read_lines)
        prev_hash = "GENESIS"

        for i, line in enumerate(lines):
            entry = json.loads(line)
            stored_hash = entry.pop("hash")
            stored_prev = entry.get("prev_hash")

            if stored_prev != prev_hash:
                return {"ok": False, "tampered_at": i, "entries": len(lines)}

            computed = hashlib.sha256(
                json.dumps(entry, ensure_ascii=False, separators=(",", ":")).encode()
            ).hexdigest()

            if computed != stored_hash:
                return {"ok": False, "tampered_at": i, "entries": len(lines)}

            prev_hash = stored_hash

        return {"ok": True, "entries": len(lines)}

    # ── Helpers privados ─────────────────────────────────────────────────────

    def _read_last_hash(self) -> str:
        try:
            text = self.log_path.read_text(encoding="utf-8")
            lines = [line for line in text.splitlines() if line.strip()]
            if lines:
                return json.loads(lines[-1]).get("hash", "GENESIS")
        except Exception:
            pass
        return "GENESIS"