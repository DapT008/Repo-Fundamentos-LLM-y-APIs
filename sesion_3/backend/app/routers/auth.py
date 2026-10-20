"""
Router de Autenticación — Tema 5: Autenticación y Autorización

Endpoints:
  POST /auth/token    → login → JWT access + refresh token
  POST /auth/refresh  → renovar access token
  GET  /auth/me       → perfil del usuario autenticado
  POST /auth/logout   → registrar cierre de sesión (audit log)

Flujo OAuth2 Password Grant (RFC 6749, Section 4.3):
  1. Cliente envía username + password
  2. Servidor verifica credenciales
  3. Servidor retorna {access_token, refresh_token, token_type, expires_in}
  4. Cliente usa access_token en cabecera: Authorization: Bearer <token>
  5. Cuando expira, cliente usa refresh_token para renovar sin re-login
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError
from pydantic import BaseModel

from app.services.jwt_service import (
    TokenPair,
    TokenData,
    create_token_pair,
    verify_token,
)
from app.services.audit_logger import AuditLogger, AuditEvent
from app.core.config import settings

router = APIRouter()

# Esquema OAuth2 — le dice a Swagger dónde pedir el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# ── Base de usuarios en memoria (para demo — en prod: base de datos) ─────────
# Contraseñas en texto plano SOLO para facilidad de demo.
# En producción: hashear con passlib bcrypt.
DEMO_USERS = {
    "admin@techcorp.com": {
        "password": "admin123",
        "name": "Administrador TechCorp",
        "scopes": ["read", "write", "admin"],
    },
    "dev@techcorp.com": {
        "password": "dev123",
        "name": "Desarrollador TechCorp",
        "scopes": ["read", "write"],
    },
    "readonly@techcorp.com": {
        "password": "readonly123",
        "name": "Usuario Solo Lectura",
        "scopes": ["read"],
    },
}


# ── Modelos de respuesta ──────────────────────────────────────────────────────

class UserProfile(BaseModel):
    email: str
    name: str
    scopes: list[str]
    token_expires_in_seconds: int


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Dependencia reutilizable: extraer usuario del JWT ────────────────────────

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """
    Dependencia FastAPI: valida el Bearer token y retorna los datos del usuario.

    Uso en cualquier endpoint protegido:
        @router.get("/protegido")
        async def endpoint(user: TokenData = Depends(get_current_user)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token_data = verify_token(token, expected_type="access")
    except JWTError:
        raise credentials_exception

    if token_data.sub not in DEMO_USERS:
        raise credentials_exception

    return token_data


def require_scope(scope: str):
    """
    Fábrica de dependencias para verificar scopes.

    Uso:
        @router.delete("/recurso")
        async def eliminar(user: TokenData = Depends(require_scope("admin"))):
            ...
    """
    async def dependency(token_data: TokenData = Depends(get_current_user)) -> TokenData:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere scope '{scope}'. Tienes: {token_data.scopes}",
            )
        return token_data
    return dependency


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/token",
    response_model=TokenPair,
    summary="Login — obtener JWT access + refresh token",
)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Autenticación con usuario y contraseña (OAuth2 Password Flow).

    **Usuarios de demostración:**
    | Email | Contraseña | Scopes |
    |-------|-----------|--------|
    | admin@techcorp.com | admin123 | read, write, admin |
    | dev@techcorp.com | dev123 | read, write |
    | readonly@techcorp.com | readonly123 | read |
    """
    audit = AuditLogger.get()
    ip = request.client.host if request.client else "unknown"

    user = DEMO_USERS.get(form_data.username)
    if not user or user["password"] != form_data.password:
        await audit.log(
            AuditEvent.LOGIN_FAILURE,
            user=form_data.username,
            ip=ip,
            severity="WARNING",
            details={"reason": "credenciales_incorrectas"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = create_token_pair(subject=form_data.username, scopes=user["scopes"])

    await audit.log(
        AuditEvent.LOGIN_SUCCESS,
        user=form_data.username,
        ip=ip,
        details={"scopes": user["scopes"]},
    )

    return tokens


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Renovar access token usando refresh token",
)
async def refresh_token(
    request: Request,
    body: RefreshRequest,
):
    """
    Renueva el access token sin re-autenticación.
    Requiere un refresh token válido.
    """
    audit = AuditLogger.get()
    ip = request.client.host if request.client else "unknown"

    try:
        token_data = verify_token(body.refresh_token, expected_type="refresh")
    except JWTError as e:
        await audit.log(
            AuditEvent.TOKEN_INVALID,
            ip=ip,
            severity="WARNING",
            details={"token_type": "refresh", "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )

    user = DEMO_USERS.get(token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    tokens = create_token_pair(subject=token_data.sub, scopes=user["scopes"])

    await audit.log(
        AuditEvent.TOKEN_REFRESH,
        user=token_data.sub,
        ip=ip,
        details={"new_scopes": user["scopes"]},
    )

    return tokens


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Perfil del usuario autenticado",
)
async def me(token_data: TokenData = Depends(get_current_user)):
    """
    Retorna el perfil del usuario cuyo JWT se envía en la cabecera.
    Requiere scope: read (mínimo).
    """
    user = DEMO_USERS[token_data.sub]
    remaining = (
        int((token_data.exp - datetime.now(timezone.utc)).total_seconds())
        if token_data.exp
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return UserProfile(
        email=token_data.sub,
        name=user["name"],
        scopes=token_data.scopes,
        token_expires_in_seconds=max(0, remaining),
    )
