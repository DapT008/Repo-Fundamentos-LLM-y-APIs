"""
Configuración compartida de pytest para Sesión 3.
Define fixtures reutilizables: cliente HTTP de test, tokens JWT, etc.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

# Configurar entorno de test ANTES de importar la app
import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-not-production"
os.environ["ENVIRONMENT"] = "test"
os.environ["OLLAMA_URL"] = "http://localhost:11434"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP async para tests de integración."""
    from app.main import app
    from app.services.audit_logger import AuditLogger

    # El lifespan de la app no se ejecuta con ASGITransport, así que
    # inicializamos el AuditLogger manualmente.
    await AuditLogger.initialize()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Resetear el singleton entre tests para evitar estado compartido
    AuditLogger._instance = None


@pytest_asyncio.fixture
async def admin_token(client):
    """Obtener token JWT de administrador para tests."""
    response = await client.post(
        "/auth/token",
        data={
            "username": "admin@techcorp.com",
            "password": "admin123",
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def user_token(client):
    """Obtener token JWT de usuario normal para tests."""
    response = await client.post(
        "/auth/token",
        data={
            "username": "dev@techcorp.com",
            "password": "dev123",
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest_asyncio.fixture
async def admin_headers(admin_token):
    """Headers con token de administrador."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token):
    """Headers con token de usuario."""
    return {"Authorization": f"Bearer {user_token}"}
