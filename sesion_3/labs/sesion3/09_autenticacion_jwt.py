#!/usr/bin/env python3
"""
Lab 09 · Autenticación con JWT — Tema 5
========================================
Demostración completa de JSON Web Tokens:

  Parte A: Anatomía de un JWT (header, payload, signature)
  Parte B: Crear y verificar tokens con python-jose
  Parte C: OAuth2 Password Flow — simular el ciclo completo
  Parte D: Ataques comunes y cómo prevenirlos
  Parte E: Ejercicio guiado — crear tu propio token

Ejecutar:
  python labs/sesion3/09_autenticacion_jwt.py

No requiere Ollama ni API key.
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE A · Anatomía de un JWT
# ─────────────────────────────────────────────────────────────────────────────

def parte_a_anatomia():
    console.print(Panel.fit(
        "[bold cyan]PARTE A · Anatomía de un JWT[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Un JWT (JSON Web Token) tiene tres partes separadas por puntos:

  [yellow]HEADER[/yellow].[green]PAYLOAD[/green].[red]SIGNATURE[/red]

Cada parte es un objeto JSON codificado en Base64URL.
""")

    # ── Header ───────────────────────────────────────────────────────────────
    header = {
        "alg": "HS256",   # algoritmo de firma
        "typ": "JWT",     # tipo de token
    }
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    console.print("[yellow bold]HEADER[/yellow bold] — Algoritmo y tipo:")
    console.print_json(json.dumps(header, indent=2))
    console.print(f"  → Base64URL: [yellow]{header_b64}[/yellow]\n")

    # ── Payload ──────────────────────────────────────────────────────────────
    now = int(time.time())
    payload = {
        "sub": "admin@techcorp.com",         # subject: ¿quién eres?
        "name": "Administrador TechCorp",
        "scopes": ["read", "write", "admin"],
        "iat": now,                           # issued at: ¿cuándo se emitió?
        "exp": now + 1800,                    # expiration: válido 30 minutos
        "iss": "llm-security-lab",           # issuer: ¿quién lo emitió?
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()

    console.print("[green bold]PAYLOAD[/green bold] — Datos del usuario (claims):")
    console.print_json(json.dumps(payload, indent=2))
    console.print(f"  → Base64URL: [green]{payload_b64[:40]}...[/green]\n")

    # ── Signature ────────────────────────────────────────────────────────────
    secret = "mi-secreto-super-seguro"
    message = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(secret.encode(), message, hashlib.sha256).digest()
    signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

    console.print("[red bold]SIGNATURE[/red bold] — HMAC-SHA256 de header + payload:")
    console.print(f"  HMAC_SHA256(base64(header) + '.' + base64(payload), secreto)\n")
    console.print(f"  → Base64URL: [red]{signature_b64}[/red]\n")

    # ── Token completo ───────────────────────────────────────────────────────
    token = f"{header_b64}.{payload_b64}.{signature_b64}"
    console.print("[bold]Token completo:[/bold]")
    console.print(f"[dim]  (copia este token en https://jwt.io para inspeccionarlo)[/dim]")
    console.print(f"\n[yellow]{header_b64}[/yellow].[green]{payload_b64[:20]}...[/green].[red]{signature_b64[:20]}...[/red]\n")

    console.print("[bold cyan]Punto clave:[/bold cyan] El payload NO está cifrado — solo codificado.")
    console.print("Cualquiera puede decodificarlo con base64. Por eso NO pongas contraseñas en el payload.")
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE B · Crear y verificar con python-jose
# ─────────────────────────────────────────────────────────────────────────────

def parte_b_python_jose():
    console.print(Panel.fit(
        "[bold cyan]PARTE B · JWT con python-jose[/bold cyan]",
        border_style="cyan",
    ))

    try:
        from jose import jwt, JWTError
    except ImportError:
        console.print("[red]Instalar: pip install python-jose[cryptography][/red]")
        return

    SECRET = "clave-secreta-demo-bsg-2026"
    ALGORITHM = "HS256"

    # Crear token válido
    payload = {
        "sub": "dev@techcorp.com",
        "scopes": ["read", "write"],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
    console.print(f"[green]✓ Token creado[/green] (primeros 50 chars): {token[:50]}...\n")

    # Verificar token válido
    try:
        decoded = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        console.print("[green]✓ Token verificado exitosamente[/green]")
        console.print(f"  Usuario: {decoded['sub']}")
        console.print(f"  Scopes: {decoded['scopes']}\n")
    except JWTError as e:
        console.print(f"[red]✗ Error: {e}[/red]")

    # Token expirado
    expired_payload = {
        "sub": "hacker@evil.com",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # ya expiró
    }
    expired_token = jwt.encode(expired_payload, SECRET, algorithm=ALGORITHM)
    try:
        jwt.decode(expired_token, SECRET, algorithms=[ALGORITHM])
    except JWTError as e:
        console.print(f"[yellow]⚠ Token expirado (correcto):[/yellow] {e}")

    # Token con firma inválida
    tampered = token[:-5] + "XXXXX"
    try:
        jwt.decode(tampered, SECRET, algorithms=[ALGORITHM])
    except JWTError as e:
        console.print(f"[yellow]⚠ Token manipulado (correcto):[/yellow] {e}\n")

    console.print("[bold cyan]Punto clave:[/bold cyan] python-jose verifica automáticamente la firma y la expiración.")
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE C · OAuth2 Password Flow simulado
# ─────────────────────────────────────────────────────────────────────────────

def parte_c_oauth2_flow():
    console.print(Panel.fit(
        "[bold cyan]PARTE C · OAuth2 Password Flow[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Flujo OAuth2 Password Grant (RFC 6749, Section 4.3):

  1. Usuario → POST /auth/token  {username, password}
  2. Servidor verifica credenciales
  3. Servidor → {access_token, refresh_token, expires_in}
  4. Usuario usa: Authorization: Bearer <access_token>
  5. Al expirar: POST /auth/refresh {refresh_token}
""")

    table = Table(title="Comparación: Session Cookies vs JWT")
    table.add_column("Aspecto", style="cyan")
    table.add_column("Session Cookie", style="yellow")
    table.add_column("JWT (Bearer Token)", style="green")

    table.add_row("Estado en servidor", "Sí (sesión en BD/Redis)", "No (stateless)")
    table.add_row("Escalabilidad", "Necesita sticky sessions", "Fácil de escalar")
    table.add_row("Invalidación inmediata", "Sí (eliminar sesión)", "Difícil (hasta expirar)")
    table.add_row("Uso en microservicios", "Complicado", "Natural (self-contained)")
    table.add_row("Tamaño del token", "~20 bytes", "~200-500 bytes")
    table.add_row("Datos adicionales", "Requiere BD lookup", "En el payload (claims)")

    console.print(table)
    console.print()

    console.print("[bold cyan]Punto clave:[/bold cyan] JWT es ideal para microservicios y APIs.")
    console.print("Para aplicaciones web tradicionales, las session cookies siguen siendo válidas.")
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE D · Ataques comunes
# ─────────────────────────────────────────────────────────────────────────────

def parte_d_ataques():
    console.print(Panel.fit(
        "[bold cyan]PARTE D · Ataques comunes a JWT[/bold cyan]",
        border_style="cyan",
    ))

    attacks = [
        {
            "ataque": "Algorithm Confusion (alg:none)",
            "descripcion": 'Atacante cambia "alg":"HS256" a "alg":"none" → omite la firma',
            "prevencion": 'Nunca aceptar alg=none. Especificar explícitamente: algorithms=["HS256"]',
        },
        {
            "ataque": "Token Leakage",
            "descripcion": "Token interceptado en HTTP o almacenado en localStorage vulnerable",
            "prevencion": "Usar HTTPS siempre. Preferir cookies httpOnly para tokens de larga duración",
        },
        {
            "ataque": "Weak Secret",
            "descripcion": 'Secreto débil → fuerza bruta posible. "secret", "123456" son triviales',
            "prevencion": "Usar secreto aleatorio de ≥256 bits: python -c \"import secrets; print(secrets.token_hex(32))\"",
        },
        {
            "ataque": "JWT in URL",
            "descripcion": "Token en query string aparece en logs del servidor, historial del navegador",
            "prevencion": "Siempre en cabecera Authorization: Bearer, nunca en URL",
        },
        {
            "ataque": "No Expiration",
            "descripcion": "Token sin campo exp → válido para siempre si es comprometido",
            "prevencion": "Access token: 15-30 min. Refresh token: 7 días máximo",
        },
    ]

    for a in attacks:
        console.print(f"\n[red bold]⚠ {a['ataque']}[/red bold]")
        console.print(f"  Problema:    {a['descripcion']}")
        console.print(f"  [green]Prevención:  {a['prevencion']}[/green]")

    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE E · Ejercicio guiado
# ─────────────────────────────────────────────────────────────────────────────

def parte_e_ejercicio():
    console.print(Panel.fit(
        "[bold green]PARTE E · Ejercicio Guiado[/bold green]",
        border_style="green",
    ))
    console.print("""
EJERCICIO: Con el backend del lab corriendo (make backend), ejecuta:

  # 1. Obtener token
  curl -X POST http://localhost:8000/auth/token \\
    -d "username=dev@techcorp.com&password=dev123"

  # 2. Guardar el access_token y usarlo:
  TOKEN="<access_token del paso anterior>"

  curl -H "Authorization: Bearer $TOKEN" \\
    http://localhost:8000/auth/me

  # 3. Verificar que el scope 'admin' es requerido para el audit:
  curl -H "Authorization: Bearer $TOKEN" \\
    http://localhost:8000/api/audit/logs
  # → Deberías ver un error 403 Forbidden

  # 4. Obtener token de admin y repetir:
  curl -X POST http://localhost:8000/auth/token \\
    -d "username=admin@techcorp.com&password=admin123"

BONUS: Abre https://jwt.io y pega el token para inspeccionarlo.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold white]Lab 09 · Autenticación con JWT[/bold white]\n"
        "[dim]Tema 5 · Seguridad y Alta Disponibilidad[/dim]",
        style="blue",
    ))

    parte_a_anatomia()
    parte_b_python_jose()
    parte_c_oauth2_flow()
    parte_d_ataques()
    parte_e_ejercicio()

    console.print(Panel.fit(
        "✅ Lab 09 completado. Siguiente: [bold]Lab 10 — Rate Limiting y WAF[/bold]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
