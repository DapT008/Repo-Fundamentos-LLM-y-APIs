"""
Security Headers Middleware — Tema 5: Seguridad en el Despliegue

Agrega cabeceras HTTP de seguridad a todas las respuestas.
Estas cabeceras son una defensa en profundidad que el servidor
debe enviar independientemente del framework del frontend.

Referencia: https://owasp.org/www-project-secure-headers/
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Agrega cabeceras de seguridad estándar a todas las respuestas HTTP.

    Cabeceras incluidas:
    ─────────────────────────────────────────────────────────────────────
    X-Content-Type-Options: nosniff
      → Evita que el navegador "adivine" el tipo MIME (MIME sniffing).
        Sin esta cabecera, un atacante puede subir HTML disfrazado de imagen.

    X-Frame-Options: DENY
      → Evita que la app sea embebida en un <iframe> (clickjacking).

    X-XSS-Protection: 1; mode=block
      → Activa el filtro XSS del navegador (legado, complementa CSP).

    Strict-Transport-Security (HSTS): max-age=31536000
      → Fuerza HTTPS por 1 año. Después del primer acceso HTTPS,
        el navegador nunca más intentará HTTP.
      → SOLO activar en producción con HTTPS real.

    Referrer-Policy: strict-origin-when-cross-origin
      → Controla qué URL se envía en el header Referer.
        Evita filtrar tokens o IDs internos en URLs a terceros.

    Permissions-Policy
      → Desactiva APIs del navegador no necesarias (cámara, micrófono,
        geolocalización) — reduce superficie de ataque.

    Content-Security-Policy (CSP)
      → Define desde dónde puede cargar recursos el navegador.
        En dev/demo usamos 'unsafe-inline' para facilidad; en producción
        hay que ser más restrictivo y usar nonces.
    ─────────────────────────────────────────────────────────────────────
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Prevención de MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Anti-clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Filtro XSS legado (complementa CSP)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS — solo en producción con HTTPS
        # En desarrollo esta cabecera se ignora sobre HTTP
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

        # Política de referentes
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Desactivar APIs del navegador innecesarias
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # CSP básico para la API REST (el frontend tiene su propio CSP)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "frame-ancestors 'none';"
        )

        return response
