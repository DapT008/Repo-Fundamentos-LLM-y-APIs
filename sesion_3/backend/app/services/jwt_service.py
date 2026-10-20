"""
Servicio JWT — Tema 5: Autenticación y Autorización

Cubre:
  · Creación de access tokens y refresh tokens
  · Verificación y decodificación de tokens
  · Scopes (permisos granulares): read, write, admin
  · Manejo de errores: token expirado, firma inválida, scopes insuficientes
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings


# ── Modelos ──────────────────────────────────────────────────────────────────

class TokenData(BaseModel):
    """Payload decodificado de un JWT."""
    sub: str                   # subject: user_id o email
    scopes: list[str] = []     # permisos otorgados
    exp: datetime | None = None
    token_type: str = "access"  # "access" | "refresh"


class TokenPair(BaseModel):
    """Par de tokens emitidos en el login."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int            # segundos hasta expiración del access token


# ── Funciones principales ─────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    scopes: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Crea un JWT de acceso de corta duración.

    Parámetros
    ----------
    subject : str
        Identificador del usuario (email o user_id).
    scopes : list[str]
        Permisos del token. Valores válidos: "read", "write", "admin".
    expires_delta : timedelta | None
        Duración del token. Por defecto usa ACCESS_TOKEN_EXPIRE_MINUTES.

    Retorna
    -------
    str
        Token JWT firmado.
    """
    if scopes is None:
        scopes = ["read"]
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta if expires_delta is not None else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    payload: dict[str, Any] = {
        "sub": subject,
        "scopes": scopes,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """
    Crea un JWT de refresco de larga duración.
    El refresh token solo contiene el subject (sin scopes)
    para minimizar el impacto si es comprometido.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(subject: str, scopes: list[str] | None = None) -> TokenPair:
    """Emite access token + refresh token en una sola llamada."""
    if scopes is None:
        scopes = ["read"]
    return TokenPair(
        access_token=create_access_token(subject, scopes),
        refresh_token=create_refresh_token(subject),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def verify_token(token: str, expected_type: str = "access") -> TokenData:
    """
    Verifica y decodifica un JWT.

    Lanza
    -----
    JWTError : si el token es inválido, expiró o tiene tipo incorrecto.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as e:
        raise JWTError(f"Token inválido: {e}") from e

    token_type = payload.get("type", "access")
    if token_type != expected_type:
        raise JWTError(f"Se esperaba token de tipo '{expected_type}', recibido '{token_type}'")

    return TokenData(
        sub=payload["sub"],
        scopes=payload.get("scopes", []),
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        token_type=token_type,
    )


def require_scopes(token_data: TokenData, required: list[str]) -> None:
    """
    Verifica que el token tenga todos los scopes requeridos.

    Lanza
    -----
    HTTPException 403 : si falta algún scope.
    """
    missing = [s for s in required if s not in token_data.scopes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Scopes insuficientes. Requeridos: {required}. "
                f"Faltantes: {missing}. Tienes: {token_data.scopes}"
            ),
        )
