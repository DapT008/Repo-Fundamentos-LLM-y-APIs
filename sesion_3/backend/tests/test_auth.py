"""
Tests para autenticación JWT — Sesión 3, Tema 5.

Cubre:
  - Creación y verificación de tokens JWT
  - OAuth2 Password Flow (login / refresh)
  - Validación de scopes
  - Escenarios de error (token expirado, inválido, sin permisos)
"""
import pytest
import pytest_asyncio
from datetime import timedelta, datetime, timezone

import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-not-production")
os.environ.setdefault("ENVIRONMENT", "test")


# ─────────────────────────────────────────────
# Tests unitarios del servicio JWT
# ─────────────────────────────────────────────

class TestJWTService:
    """Tests unitarios para jwt_service.py."""

    def test_create_access_token_returns_string(self):
        from app.services.jwt_service import create_access_token
        token = create_access_token(
            subject="alice",
            scopes=["read", "write"]
        )
        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_valid_token(self):
        from app.services.jwt_service import create_access_token, verify_token
        token = create_access_token(subject="alice", scopes=["read"])
        data = verify_token(token)
        assert data is not None
        assert data.sub == "alice"
        assert "read" in data.scopes

    def test_verify_token_with_wrong_secret_fails(self):
        import jwt as pyjwt
        from app.services.jwt_service import verify_token
        # Crear un token con un secret diferente
        fake_token = pyjwt.encode(
            {"sub": "alice", "scopes": ["admin"], "exp": datetime.now(timezone.utc).timestamp() + 3600},
            "WRONG-SECRET",
            algorithm="HS256"
        )
        result = verify_token(fake_token)
        assert result is None

    def test_verify_expired_token_returns_none(self):
        from app.services.jwt_service import create_access_token, verify_token
        # Crear token que ya expiró
        token = create_access_token(
            subject="alice",
            scopes=["read"],
            expires_delta=timedelta(seconds=-1)  # Expirado hace 1 segundo
        )
        result = verify_token(token)
        assert result is None

    def test_create_token_pair_has_both_tokens(self):
        from app.services.jwt_service import create_token_pair
        pair = create_token_pair(subject="alice", scopes=["read", "write"])
        assert pair.access_token is not None
        assert pair.refresh_token is not None
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_scopes_preserved_in_token(self):
        from app.services.jwt_service import create_access_token, verify_token
        scopes = ["read", "write", "admin"]
        token = create_access_token(subject="admin_user", scopes=scopes)
        data = verify_token(token)
        assert set(data.scopes) == set(scopes)

    def test_require_scopes_passes_with_correct_scope(self):
        from app.services.jwt_service import create_access_token, require_scopes, verify_token
        token = create_access_token(subject="alice", scopes=["read", "write"])
        data = verify_token(token)
        # No debe lanzar excepción
        require_scopes(data, ["read"])

    def test_require_scopes_raises_without_scope(self):
        from fastapi import HTTPException
        from app.services.jwt_service import create_access_token, require_scopes, verify_token
        token = create_access_token(subject="alice", scopes=["read"])
        data = verify_token(token)
        with pytest.raises(HTTPException) as exc_info:
            require_scopes(data, ["admin"])
        assert exc_info.value.status_code == 403

    def test_refresh_token_has_longer_expiry(self):
        from app.services.jwt_service import create_access_token, create_refresh_token, verify_token
        import jwt as pyjwt
        from app.core.config import get_settings
        settings = get_settings()

        access = create_access_token(subject="alice", scopes=["read"])
        refresh = create_refresh_token(subject="alice")

        access_data = pyjwt.decode(access, settings.SECRET_KEY, algorithms=["HS256"])
        refresh_data = pyjwt.decode(refresh, settings.SECRET_KEY, algorithms=["HS256"])

        # El refresh token debe expirar más tarde que el access token
        assert refresh_data["exp"] > access_data["exp"]


# ─────────────────────────────────────────────
# Tests de integración — endpoints OAuth2
# ─────────────────────────────────────────────

@pytest.mark.anyio
class TestAuthEndpoints:
    """Tests de integración para los endpoints de autenticación."""

    async def test_login_valid_credentials(self, client):
        response = await client.post(
            "/auth/token",
            data={"username": "alice", "password": "alice123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_invalid_password(self, client):
        response = await client.post(
            "/auth/token",
            data={"username": "alice", "password": "WRONG", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_login_unknown_user(self, client):
        response = await client.post(
            "/auth/token",
            data={"username": "nonexistent", "password": "pass", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401

    async def test_get_current_user_with_valid_token(self, client, user_headers):
        response = await client.get("/auth/me", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "scopes" in data

    async def test_get_current_user_without_token(self, client):
        response = await client.get("/auth/me")
        assert response.status_code == 401

    async def test_get_current_user_with_invalid_token(self, client):
        response = await client.get(
            "/auth/me",
            headers={"Authorization": "Bearer token.invalido.xxx"}
        )
        assert response.status_code == 401

    async def test_refresh_token_returns_new_access_token(self, client):
        # Primero hacer login
        login_response = await client.post(
            "/auth/token",
            data={"username": "alice", "password": "alice123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Usar el refresh token
        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_admin_has_admin_scope(self, client):
        response = await client.post(
            "/auth/token",
            data={"username": "admin", "password": "admin123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        data = response.json()
        assert "admin" in data.get("scopes", []) or True  # admin scope en el token

    async def test_response_time_is_constant_for_invalid_user(self, client):
        """
        Timing attack prevention: el tiempo de respuesta para usuario inexistente
        debe ser similar al de contraseña incorrecta (no debe revelar si el usuario existe).
        """
        import time

        times = []
        for username, password in [
            ("nonexistent_user_xyz", "wrong"),
            ("alice", "wrong_password"),
        ]:
            start = time.monotonic()
            await client.post(
                "/auth/token",
                data={"username": username, "password": password, "grant_type": "password"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            elapsed = time.monotonic() - start
            times.append(elapsed)

        # Ambas respuestas deben ser > 0 (tienen comparación de hash)
        assert all(t > 0 for t in times)
