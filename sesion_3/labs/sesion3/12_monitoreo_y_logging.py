#!/usr/bin/env python3
"""
Lab 12 · Monitoreo y Logging Estructurado — Tema 5
====================================================
Demostración de observabilidad en sistemas LLM:

  Parte A: Logging estructurado con structlog
  Parte B: Métricas de negocio y operaciones
  Parte C: Audit Trail con cadena de hash (integridad)
  Parte D: Alertas y umbrales
  Parte E: Ejercicio — leer el audit log del backend

No requiere Ollama ni API key.
"""

import asyncio
import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE A · Logging estructurado con structlog
# ─────────────────────────────────────────────────────────────────────────────

def parte_a_structlog():
    console.print(Panel.fit(
        "[bold cyan]PARTE A · Logging Estructurado con structlog[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
El logging tradicional produce texto plano difícil de procesar:
  [ERROR] 2026-10-19 14:23:11 - Chat request failed for user

El logging estructurado produce JSON consultable:
""")

    # Ejemplo de log tradicional vs estructurado
    traditional = "2026-10-19 14:23:11 ERROR Chat request failed for user dev@techcorp.com"
    structured = {
        "timestamp": "2026-10-19T14:23:11.234Z",
        "level": "error",
        "event": "chat_request_failed",
        "request_id": "a1b2c3d4",
        "user": "dev@techcorp.com",
        "model": "llama3.2",
        "latency_ms": 3247,
        "error": "ConnectionTimeout",
        "circuit_state": "SEMIABIERTO",
    }

    console.print("[dim]Tradicional:[/dim]")
    console.print(f"  [yellow]{traditional}[/yellow]\n")

    console.print("[dim]Estructurado (JSON):[/dim]")
    console.print(Syntax(json.dumps(structured, indent=2), "json", theme="monokai"))
    console.print()

    console.print("[bold cyan]Ventajas del log estructurado:[/bold cyan]")
    console.print("  · Cloud Logging / Datadog pueden filtrar por cualquier campo")
    console.print("  · Fácil de indexar, buscar y agregar")
    console.print("  · Correlación automática con request_id")
    console.print("  · Alertas basadas en valores (latency_ms > 5000)\n")

    console.print("[bold]Configuración en el backend:[/bold]")
    code = """\
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,     # request_id automático
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),          # salida JSON
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

# En el middleware de request:
structlog.contextvars.bind_contextvars(request_id=str(uuid.uuid4())[:8])

# En cualquier parte del código:
log = structlog.get_logger()
log.info("chat_request", user=user, model=model, tokens=512)"""

    console.print(Syntax(code, "python", theme="monokai"))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE B · Métricas de negocio
# ─────────────────────────────────────────────────────────────────────────────

def parte_b_metricas():
    console.print(Panel.fit(
        "[bold cyan]PARTE B · Métricas de Negocio y SLOs[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Para LLMs en producción hay tres capas de métricas:

  [bold]Infraestructura:[/bold] CPU, RAM, latencia de red, errores HTTP
  [bold]Modelo:[/bold]          tokens/s, TTFT (time to first token), tokens por request
  [bold]Negocio:[/bold]         consultas exitosas, tasa de rechazo WAF, costo/consulta
""")

    # Simulación de métricas de una hora
    metrics = {
        "total_requests": 847,
        "successful": 821,
        "waf_blocked": 18,
        "rate_limited": 8,
        "circuit_open_rejections": 0,
        "avg_latency_ms": 1247,
        "p95_latency_ms": 3102,
        "p99_latency_ms": 5844,
        "total_tokens_generated": 124_830,
        "avg_tokens_per_request": 152,
        "estimated_cost_usd": 0.0312,  # Ollama = 0 pero simulamos
    }

    table = Table(title="Métricas — Última hora (simuladas)")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", justify="right")
    table.add_column("SLO", justify="center")
    table.add_column("Estado")

    slos = [
        ("Tasa de éxito", f"{metrics['successful']/metrics['total_requests']*100:.1f}%",
         "> 99%", metrics['successful']/metrics['total_requests'] > 0.99),
        ("Latencia p95", f"{metrics['p95_latency_ms']} ms", "< 5000 ms",
         metrics['p95_latency_ms'] < 5000),
        ("Latencia p99", f"{metrics['p99_latency_ms']} ms", "< 10000 ms",
         metrics['p99_latency_ms'] < 10000),
        ("Bloqueos WAF", f"{metrics['waf_blocked']}", "< 50/h",
         metrics['waf_blocked'] < 50),
        ("Rate limited", f"{metrics['rate_limited']}", "< 20/h",
         metrics['rate_limited'] < 20),
        ("Tokens/request", f"{metrics['avg_tokens_per_request']}", "< 500",
         metrics['avg_tokens_per_request'] < 500),
    ]

    for name, val, slo, ok in slos:
        status = "[green]✅ OK[/green]" if ok else "[red]❌ VIOLADO[/red]"
        table.add_row(name, val, slo, status)

    console.print(table)
    console.print()

    console.print("[bold cyan]Prometheus metrics endpoint (GET /metrics):[/bold cyan]")
    prom = """\
# HELP llm_requests_total Total de peticiones al LLM
# TYPE llm_requests_total counter
llm_requests_total{status="success"} 821
llm_requests_total{status="waf_blocked"} 18
llm_requests_total{status="rate_limited"} 8

# HELP llm_latency_ms Latencia en milisegundos
# TYPE llm_latency_ms histogram
llm_latency_ms_bucket{le="500"} 312
llm_latency_ms_bucket{le="1000"} 589
llm_latency_ms_bucket{le="5000"} 820
llm_latency_ms_count 847"""

    console.print(f"[dim]{prom}[/dim]\n")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE C · Audit Trail con cadena de hash
# ─────────────────────────────────────────────────────────────────────────────

async def parte_c_audit_trail():
    console.print(Panel.fit(
        "[bold cyan]PARTE C · Audit Trail con Cadena de Hash[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
El audit log del backend usa una cadena de hash (como una mini blockchain):

  · Cada entrada incluye el hash SHA-256 de su propio contenido
  · Y el hash de la entrada anterior (prev_hash)
  · Si alguien modifica una entrada, toda la cadena queda inválida
  · La primera entrada usa "GENESIS" como prev_hash

Esto garantiza:
  ✓ Integridad — no se puede modificar el pasado sin detectarlo
  ✓ Ordenamiento — las entradas mantienen orden causal
  ✓ No repudio — si el hash coincide, el evento ocurrió
""")

    # Simular una cadena de audit
    entries = []
    prev_hash = "GENESIS"

    events = [
        {"event": "LOGIN_SUCCESS", "user": "admin@techcorp.com", "ip": "10.0.0.5"},
        {"event": "CHAT_REQUEST", "user": "dev@techcorp.com", "ip": "10.0.0.7", "model": "llama3.2"},
        {"event": "WAF_BLOCK", "user": "anonymous", "ip": "45.33.32.156", "rule": "prompt_injection"},
        {"event": "RATE_LIMIT_HIT", "user": "dev@techcorp.com", "ip": "10.0.0.7"},
    ]

    for evt in events:
        entry = {
            **evt,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "entry_id": str(uuid.uuid4())[:8],
            "prev_hash": prev_hash,
        }
        # Calcular hash del contenido actual
        content = json.dumps({k: v for k, v in entry.items() if k != "hash"}, sort_keys=True)
        entry["hash"] = hashlib.sha256(content.encode()).hexdigest()[:16]
        entries.append(entry)
        prev_hash = entry["hash"]
        await asyncio.sleep(0.01)

    table = Table(title="Audit Trail (simulado)")
    table.add_column("ID", style="dim", min_width=8)
    table.add_column("Evento", style="yellow")
    table.add_column("Usuario/IP")
    table.add_column("prev_hash", style="dim", min_width=10)
    table.add_column("hash", style="cyan", min_width=10)

    for e in entries:
        who = f"{e.get('user','?')} / {e.get('ip','?')}"
        table.add_row(
            e["entry_id"],
            e["event"],
            who,
            e["prev_hash"][:10] + "…" if len(e["prev_hash"]) > 10 else e["prev_hash"],
            e["hash"],
        )

    console.print(table)
    console.print()

    # Verificar integridad
    console.print("[bold]Verificación de integridad:[/bold]")
    prev = "GENESIS"
    all_ok = True
    for e in entries:
        expected_content = json.dumps(
            {k: v for k, v in e.items() if k != "hash"}, sort_keys=True
        )
        expected_hash = hashlib.sha256(expected_content.encode()).hexdigest()[:16]
        ok = (e["prev_hash"] == prev) and (e["hash"] == expected_hash)
        status = "✅" if ok else "❌"
        console.print(f"  {status} Entrada [{e['entry_id']}] {e['event']}")
        prev = e["hash"]
        if not ok:
            all_ok = False

    console.print(f"\n[{'green' if all_ok else 'red'}]{'✅ Cadena íntegra' if all_ok else '❌ Cadena comprometida'}[/{'green' if all_ok else 'red'}]")
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE D · Alertas y umbrales
# ─────────────────────────────────────────────────────────────────────────────

def parte_d_alertas():
    console.print(Panel.fit(
        "[bold cyan]PARTE D · Alertas y Umbrales[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Las alertas notifican cuando los SLOs se violan. En GCP:

  · Cloud Monitoring → Alertas → Política de alertas
  · Filtro MQL (Monitoring Query Language):
""")

    mql_examples = [
        ("Latencia p95 > 5s", "fetch llm_latency_ms | percentile(0.95) | threshold(5000)"),
        ("WAF blocks > 50/h", "fetch llm_requests_total | filter status='waf_blocked' | rate(1h) | threshold(50)"),
        ("Circuit ABIERTO", "fetch circuit_state | filter state='ABIERTO' | condition(true)"),
        ("Error rate > 1%", "fetch llm_requests_total | (filter status='error' / filter status!='error') | threshold(0.01)"),
    ]

    table = Table(title="Políticas de alerta recomendadas")
    table.add_column("Alerta", style="yellow")
    table.add_column("Canal", justify="center")
    table.add_column("Severidad", justify="center")

    rows = [
        ("Circuit Breaker ABIERTO", "PagerDuty / SMS", "[red]CRÍTICA[/red]"),
        ("Error rate > 1%", "Slack #ops", "[red]ALTA[/red]"),
        ("Latencia p95 > 5s", "Slack #ops", "[yellow]MEDIA[/yellow]"),
        ("WAF blocks > 50/h", "Email equipo", "[yellow]MEDIA[/yellow]"),
        ("Costo diario > $50", "Email finanzas", "[cyan]BAJA[/cyan]"),
    ]
    for name, canal, sev in rows:
        table.add_row(name, canal, sev)

    console.print(table)
    console.print()

    console.print("[bold cyan]Runbook para cada alerta:[/bold cyan]")
    console.print("  Cada alerta debe tener un runbook que responda:")
    console.print("  1. ¿Qué significa esta alerta?")
    console.print("  2. ¿Qué verificar primero? (dashboard link)")
    console.print("  3. ¿Cuáles son las causas más comunes?")
    console.print("  4. ¿Cómo mitigar temporalmente?")
    console.print("  5. ¿Cómo escalar si no se resuelve en 30 min?\n")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE E · Ejercicio
# ─────────────────────────────────────────────────────────────────────────────

def parte_e_ejercicio():
    console.print(Panel.fit(
        "[bold green]PARTE E · Ejercicio[/bold green]",
        border_style="green",
    ))
    console.print("""
EJERCICIO: Con el backend corriendo (make backend), lee el audit trail:

  # Obtener token de admin:
  TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \\
    -d "username=admin@techcorp.com&password=admin123" | \\
    python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  # 1. Ver los últimos 20 eventos del audit log:
  curl -s -H "Authorization: Bearer $TOKEN" \\
    "http://localhost:8000/api/audit/logs?n=20" | python3 -m json.tool

  # 2. Verificar integridad de la cadena:
  curl -s -H "Authorization: Bearer $TOKEN" \\
    http://localhost:8000/api/audit/integrity

  # 3. Genera algunos eventos y vuelve a verificar:
  DEV_TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \\
    -d "username=dev@techcorp.com&password=dev123" | \\
    python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  curl -s -X POST http://localhost:8000/api/chat \\
    -H "Authorization: Bearer $DEV_TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"message": "Hola, ¿cómo estás?"}'

  # Repite el paso 1 y observa el nuevo evento en el log.
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main_async():
    console.print(Panel(
        "[bold white]Lab 12 · Monitoreo y Logging[/bold white]\n"
        "[dim]Tema 5 · Seguridad y Alta Disponibilidad[/dim]",
        style="blue",
    ))

    parte_a_structlog()
    parte_b_metricas()
    await parte_c_audit_trail()
    parte_d_alertas()
    parte_e_ejercicio()

    console.print(Panel.fit(
        "✅ Lab 12 completado. Siguiente: [bold]Lab 13 — Diseño Arquitectónico[/bold]",
        border_style="green",
    ))


if __name__ == "__main__":
    asyncio.run(main_async())
