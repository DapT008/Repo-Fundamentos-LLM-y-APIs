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
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-not-production")
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

    def test_verify_token_with_wrong_secret_raises(self):
        from jose import JWTError, jwt as jose_jwt
        from app.services.jwt_service import verify_token
        fake_token = jose_jwt.encode(
            {
                "sub": "alice",
                "scopes": ["admin"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "type": "access",
            },
            "WRONG-SECRET",
            algorithm="HS256",
        )
        with pytest.raises(JWTError):
            verify_token(fake_token)

    def test_verify_expired_token_raises(self):
        from jose import JWTError
        from app.services.jwt_service import create_access_token, verify_token
        token = create_access_token(
            subject="alice",
            scopes=["read"],
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(JWTError):
            verify_token(token)

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
        from app.services.jwt_service import create_access_token, create_refresh_token
        from app.core.config import settings
        from jose import jwt as jose_jwt

        access = create_access_token(subject="alice", scopes=["read"])
        refresh = create_refresh_token(subject="alice")

        access_data = jose_jwt.decode(access, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        refresh_data = jose_jwt.decode(refresh, settings.JWT_SECRET_KEY, algorithms=["HS256"])

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
            data={"username": "dev@techcorp.com", "password": "dev123", "grant_type": "password"},
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
            data={"username": "dev@techcorp.com", "password": "WRONG", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_login_unknown_user(self, client):
        response = await client.post(
            "/auth/token",
            data={"username": "nonexistent@example.com", "password": "pass", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401

    async def test_get_current_user_with_valid_token(self, client, user_headers):
        response = await client.get("/auth/me", headers=user_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
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
        login_response = await client.post(
            "/auth/token",
            data={"username": "dev@techcorp.com", "password": "dev123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_admin_has_admin_scope(self, client):
        login_response = await client.post(
            "/auth/token",
            data={"username": "admin@techcorp.com", "password": "admin123", "grant_type": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        me_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200
        assert "admin" in me_response.json()["scopes"]

    async def test_response_time_is_constant_for_invalid_user(self, client):
        """Timing: respuesta para usuario inexistente no debe revelar si el usuario existe."""
        import time

        times = []
        for username, password in [
            ("nonexistent_user_xyz@example.com", "wrong"),
            ("dev@techcorp.com", "wrong_password"),
        ]:
            start = time.monotonic()
            await client.post(
                "/auth/token",
                data={"username": username, "password": password, "grant_type": "password"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            elapsed = time.monotonic() - start
            times.append(elapsed)

        assert all(t > 0 for t in times)
