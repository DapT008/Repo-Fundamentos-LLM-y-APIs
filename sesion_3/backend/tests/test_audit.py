"""
Tests para el sistema de Audit Log con hash chain — Sesión 3, Tema 5.

Cubre:
  - Registro de eventos en el log
  - Verificación de integridad de la cadena de hashes SHA-256
  - Detección de manipulación del log
  - Acceso de solo lectura para usuarios no admin
"""
import pytest
import hashlib
import json
import tempfile
import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENVIRONMENT", "test")


# ─────────────────────────────────────────────
# Tests unitarios del AuditLogger
# ─────────────────────────────────────────────

@pytest.mark.anyio
class TestAuditLogger:
    """Tests unitarios para el servicio de audit log con hash chain."""

    async def _make_logger(self, tmp_path):
        """Crea un AuditLogger fresco apuntando a un archivo temporal."""
        from app.services.audit_logger import AuditLogger
        instance = AuditLogger.__new__(AuditLogger)
        instance.log_path = tmp_path
        instance.log_path.parent.mkdir(parents=True, exist_ok=True)
        instance._last_hash = "GENESIS"
        instance._write_lock = __import__("asyncio").Lock()
        return instance

    async def test_log_creates_entry(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={"ip": "127.0.0.1"})
        entries = await logger.get_recent(10)
        assert len(entries) == 1

    async def test_log_entry_has_required_fields(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={})
        entry = (await logger.get_recent(1))[0]
        assert "event" in entry
        assert "user" in entry
        assert "timestamp" in entry
        assert "hash" in entry
        assert "prev_hash" in entry

    async def test_first_entry_prev_hash_is_genesis(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={})
        # get_recent returns newest first, so [0] is the only/last entry
        entries = await logger.get_recent(10)
        assert entries[0]["prev_hash"] == "GENESIS"

    async def test_second_entry_prev_hash_matches_first(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={})
        await logger.log(event=AuditEvent.CHAT_REQUEST, user="alice", details={})

        entries = await logger.get_recent(10)
        # get_recent returns newest first
        second = entries[0]
        first = entries[1]
        assert second["prev_hash"] == first["hash"]

    async def test_hash_is_sha256(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={"ip": "127.0.0.1"})
        entry = (await logger.get_recent(1))[0]
        assert len(entry["hash"]) == 64
        assert all(c in "0123456789abcdef" for c in entry["hash"])

    async def test_integrity_check_passes_on_clean_log(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        for i in range(5):
            await logger.log(event=AuditEvent.LOGIN_SUCCESS, user=f"user{i}", details={})
        result = await logger.verify_integrity()
        assert result["ok"] is True
        assert result["entries"] == 5

    async def test_integrity_check_detects_tampering(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        log_file = tmp_path / "audit.jsonl"
        logger = await self._make_logger(log_file)
        await logger.log(event=AuditEvent.LOGIN_SUCCESS, user="alice", details={})
        await logger.log(event=AuditEvent.LOGIN_FAILURE, user="bob", details={})

        # Manipular el archivo directamente
        lines = log_file.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["user"] = "HACKED"
        lines[0] = json.dumps(entry)
        log_file.write_text("\n".join(lines) + "\n")

        result = await logger.verify_integrity()
        assert result["ok"] is False

    async def test_get_recent_limits_results(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        for i in range(20):
            await logger.log(event=AuditEvent.CHAT_REQUEST, user="alice", details={"msg_num": i})
        entries = await logger.get_recent(5)
        assert len(entries) == 5

    async def test_empty_log_integrity_check(self, tmp_path):
        from app.services.audit_logger import AuditLogger
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        result = await logger.verify_integrity()
        assert result["ok"] is True
        assert result["entries"] == 0

    async def test_waf_block_event_logged(self, tmp_path):
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        await logger.log(
            event=AuditEvent.WAF_BLOCK,
            user="attacker",
            details={"threats": ["sql_injection"], "severity": "HIGH"}
        )
        entries = await logger.get_recent(1)
        assert entries[0]["event"] == AuditEvent.WAF_BLOCK.value

    async def test_hash_chain_with_100_entries(self, tmp_path):
        """Test de rendimiento: 100 entradas deben mantener integridad."""
        from app.services.audit_logger import AuditLogger, AuditEvent
        logger = await self._make_logger(tmp_path / "audit.jsonl")
        for i in range(100):
            await logger.log(event=AuditEvent.CHAT_REQUEST, user="load-tester", details={"request_num": i})
        result = await logger.verify_integrity()
        assert result["ok"] is True
        assert result["entries"] == 100


# ─────────────────────────────────────────────
# Tests de integración — endpoints de audit
# ─────────────────────────────────────────────

@pytest.mark.anyio
class TestAuditEndpoints:
    """Tests de integración para los endpoints de audit."""

    async def test_audit_logs_requires_authentication(self, client):
        response = await client.get("/api/audit/logs")
        assert response.status_code == 401

    async def test_audit_logs_requires_admin_scope(self, client, user_headers):
        """Un usuario sin scope 'admin' no puede ver los logs."""
        response = await client.get("/api/audit/logs", headers=user_headers)
        assert response.status_code == 403

    async def test_audit_logs_accessible_with_admin_scope(self, client, admin_headers):
        response = await client.get("/api/audit/logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "entries" in data
        assert isinstance(data["entries"], list)

    async def test_audit_integrity_endpoint(self, client, admin_headers):
        response = await client.get("/api/audit/integrity", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert "entries" in data

    async def test_audit_logs_have_correct_structure(self, client, admin_headers):
        response = await client.get("/api/audit/logs", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        entries = data.get("entries", [])
        if entries:
            entry = entries[0]
            assert "event" in entry
            assert "timestamp" in entry
            assert "hash" in entry


# ─────────────────────────────────────────────
# Tests de la propiedad de hash chain
# ─────────────────────────────────────────────

class TestHashChainProperty:
    """
    Tests de propiedades matemáticas del hash chain.
    Verifica que SHA-256 se usa correctamente.
    """

    def test_hash_computation_is_deterministic(self):
        """El mismo contenido siempre produce el mismo hash."""
        content = {"event": "LOGIN_SUCCESS", "user": "alice", "prev_hash": "GENESIS"}
        content_str = json.dumps(content, sort_keys=True, default=str)

        hash1 = hashlib.sha256(content_str.encode()).hexdigest()
        hash2 = hashlib.sha256(content_str.encode()).hexdigest()

        assert hash1 == hash2

    def test_different_content_produces_different_hash(self):
        """Contenidos distintos producen hashes distintos (avalanche effect)."""
        content1 = '{"event": "LOGIN_SUCCESS", "user": "alice"}'
        content2 = '{"event": "LOGIN_SUCCESS", "user": "ALICE"}'

        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()

        assert hash1 != hash2

    def test_sha256_output_length(self):
        """SHA-256 siempre produce 256 bits = 64 caracteres hex."""
        for content in ["a", "hello world", "x" * 10000]:
            h = hashlib.sha256(content.encode()).hexdigest()
            assert len(h) == 64
