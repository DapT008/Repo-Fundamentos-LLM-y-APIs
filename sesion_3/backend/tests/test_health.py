"""
Tests para los endpoints de health check — Sesión 3, Tema 5.

Cubre:
  - Liveness probe (el proceso está vivo)
  - Readiness probe (listo para recibir tráfico)
  - Estado del circuit breaker
"""
import pytest
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.mark.anyio
class TestHealthEndpoints:
    """Tests para los endpoints de salud."""

    async def test_health_endpoint_returns_200(self, client):
        """El health check debe responder 200 si el servicio está corriendo."""
        response = await client.get("/api/health")
        assert response.status_code == 200

    async def test_health_response_has_status_field(self, client):
        response = await client.get("/api/health")
        data = response.json()
        assert "status" in data

    async def test_health_shows_version(self, client):
        response = await client.get("/api/health")
        data = response.json()
        assert "version" in data or "app" in data

    async def test_circuit_breaker_status_endpoint(self, client):
        response = await client.get("/api/health/circuit")
        assert response.status_code == 200
        data = response.json()
        assert "state" in data or "circuit_breaker" in data or "status" in data

    async def test_health_is_accessible_without_auth(self, client):
        """El health check debe ser público (para load balancers)."""
        response = await client.get("/api/health")
        assert response.status_code != 401
        assert response.status_code != 403

    async def test_health_response_time_is_fast(self, client):
        """El health check debe responder en menos de 500ms."""
        import time
        start = time.monotonic()
        await client.get("/api/health")
        elapsed = time.monotonic() - start
        assert elapsed < 0.5, f"Health check tardó {elapsed:.3f}s (max: 0.5s)"
