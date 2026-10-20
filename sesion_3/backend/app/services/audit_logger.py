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
import os
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
    _lock = asyncio.Lock()

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = "GENESIS"   # primer bloque de la cadena

        # Leer último hash si el archivo ya existe
        if self.log_path.exists():
            self._last_hash = self._read_last_hash()

    # ── Inicialización singleton ─────────────────────────────────────────────

    @classmethod
    async def initialize(cls) -> "AuditLogger":
        async with cls._lock:
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

        async with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)
            self._last_hash = entry_hash

        logger.info(
            "Audit entry",
            event=event.value,
            user=user,
            ip=ip,
            severity=severity,
        )

    # ── Lectura ──────────────────────────────────────────────────────────────

    async def get_recent(self, n: int = 50) -> list[dict]:
        """Retorna las últimas N entradas del log."""
        if not self.log_path.exists():
            return []

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
        recent = lines[-n:] if len(lines) > n else lines
        return [json.loads(line) for line in reversed(recent)]

    async def verify_integrity(self) -> dict:
        """
        Verifica la integridad de la cadena de hashes.
        Retorna {'ok': True} o {'ok': False, 'tampered_at': index}.
        """
        if not self.log_path.exists():
            return {"ok": True, "entries": 0}

        lines = self.log_path.read_text(encoding="utf-8").strip().splitlines()
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
            # Leer el último hash del archivo existente
            with open(self.log_path, "rb") as f:
                # Buscar la última línea no vacía
                f.seek(0, os.SEEK_END)
                pos = f.tell()
                while pos > 0:
                    pos -= 1
                    f.seek(pos)
                    if f.read(1) == b"\n" and pos < f.seek(0, os.SEEK_END) - 1:
                        break
                last_line = f.readline().decode().strip()
                if last_line:
                    return json.loads(last_line).get("hash", "GENESIS")
        except Exception:
            pass
        return "GENESIS"
