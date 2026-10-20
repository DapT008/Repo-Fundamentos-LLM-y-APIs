#!/usr/bin/env python3
"""
Lab 11 · Alta Disponibilidad — Tema 5
======================================
Demostración del patrón Circuit Breaker y estrategias de failover:

  Parte A: Simulación del Circuit Breaker (3 estados)
  Parte B: Health Check y Readiness Probe
  Parte C: Failover entre proveedores LLM
  Parte D: RTO y RPO — métricas de recuperación ante desastres
  Parte E: Ejercicio — configurar alertas de umbral

No requiere Ollama ni API key.
"""

import asyncio
import random
import time
from datetime import datetime, timezone
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE A · Simulación del Circuit Breaker
# ─────────────────────────────────────────────────────────────────────────────

class CBState(Enum):
    CLOSED = "🟢 CERRADO"
    OPEN = "🔴 ABIERTO"
    HALF_OPEN = "🟡 SEMIABIERTO"


class DemoCircuitBreaker:
    def __init__(self, name: str, threshold: int = 3, timeout: float = 5.0):
        self.name = name
        self.threshold = threshold
        self.timeout = timeout
        self.state = CBState.CLOSED
        self.failures = 0
        self.opened_at: float | None = None
        self.history: list[dict] = []

    def call(self, should_fail: bool = False) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")

        # Verificar si debe pasar de ABIERTO a SEMIABIERTO
        if self.state == CBState.OPEN:
            if time.time() - self.opened_at >= self.timeout:
                self.state = CBState.HALF_OPEN
                self.history.append({"ts": ts, "state": "→ SEMIABIERTO", "result": "probando..."})

        # ABIERTO: rechazar inmediatamente
        if self.state == CBState.OPEN:
            self.history.append({"ts": ts, "state": self.state.value, "result": "RECHAZADO (fail-fast)"})
            raise Exception(f"Circuit {self.name} ABIERTO — servicio no disponible")

        # Ejecutar llamada
        if should_fail:
            self.failures += 1
            if self.state == CBState.HALF_OPEN or self.failures >= self.threshold:
                self.state = CBState.OPEN
                self.opened_at = time.time()
                self.history.append({"ts": ts, "state": "→ ABIERTO", "result": f"FALLO #{self.failures}"})
            else:
                self.history.append({"ts": ts, "state": self.state.value, "result": f"FALLO #{self.failures}/{self.threshold}"})
            raise Exception(f"Fallo simulado en {self.name}")
        else:
            if self.state == CBState.HALF_OPEN:
                self.state = CBState.CLOSED
                self.failures = 0
                self.history.append({"ts": ts, "state": "→ CERRADO", "result": "✓ RECUPERADO"})
            else:
                self.history.append({"ts": ts, "state": self.state.value, "result": "✓ OK"})
            return "Respuesta exitosa del servicio"


def parte_a_circuit_breaker():
    console.print(Panel.fit(
        "[bold cyan]PARTE A · Simulación del Circuit Breaker[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
El Circuit Breaker protege el sistema de servicios externos fallando rápido:

  CERRADO  → todo normal; se cuentan fallos
  ABIERTO  → se rechazan peticiones sin siquiera intentar
  SEMIABIERTO → se permite una petición de prueba
""")

    cb = DemoCircuitBreaker(name="ollama", threshold=3, timeout=2.0)

    # Escenario: 2 éxitos, 3 fallos → abierto, espera, recuperación
    escenario = [
        (False, "Petición normal"),
        (False, "Petición normal"),
        (True,  "Ollama empieza a fallar"),
        (True,  "Segundo fallo"),
        (True,  "Tercer fallo → circuito abre"),
        (False, "Petición bloqueada (circuito ABIERTO)"),
        (False, "Petición bloqueada"),
    ]

    for should_fail, desc in escenario:
        try:
            cb.call(should_fail=should_fail)
        except Exception:
            pass
        time.sleep(0.1)

    # Esperar que el timeout del circuito expire
    console.print("[dim]Esperando que el circuito pase a SEMIABIERTO...[/dim]")
    time.sleep(2.5)

    # Llamada de prueba exitosa → recuperación
    try:
        cb.call(should_fail=False)  # prueba exitosa → CERRADO
    except Exception:
        pass

    # Mostrar historial
    table = Table(title="Historial del Circuit Breaker")
    table.add_column("Hora", style="dim")
    table.add_column("Estado", min_width=18)
    table.add_column("Resultado")

    for entry in cb.history:
        table.add_row(entry["ts"], entry["state"], entry["result"])

    console.print(table)
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE B · Health Check y Readiness Probe
# ─────────────────────────────────────────────────────────────────────────────

def parte_b_health_checks():
    console.print(Panel.fit(
        "[bold cyan]PARTE B · Health Checks en Kubernetes[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Kubernetes usa dos tipos de probes para gestionar pods:

  [bold]Liveness Probe[/bold]  → ¿está vivo el proceso?
    Si falla: Kubernetes reinicia el pod
    Endpoint: GET /api/health  (responde 200 ← siempre, si el proceso vive)

  [bold]Readiness Probe[/bold] → ¿puede recibir tráfico?
    Si falla: Kubernetes saca el pod del load balancer (no lo reinicia)
    Endpoint: GET /api/health  (responde 200 solo si Ollama responde)

Configuración en el manifest Kubernetes:
""")

    k8s_probe_yaml = """\
livenessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 2"""

    console.print(f"[dim]{k8s_probe_yaml}[/dim]")
    console.print()

    console.print("""
[bold cyan]Diferencia clave:[/bold cyan]
  · Si Ollama está DOWN → liveness OK, readiness FALLA
    → El pod sigue vivo pero no recibe nuevas peticiones
    → Las peticiones en curso se drenan primero (graceful shutdown)

  · Si el proceso está bloqueado (deadlock) → liveness FALLA
    → Kubernetes reinicia el pod
""")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE C · Failover entre proveedores
# ─────────────────────────────────────────────────────────────────────────────

async def parte_c_failover():
    console.print(Panel.fit(
        "[bold cyan]PARTE C · Failover entre Proveedores LLM[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Estrategia: si el proveedor primario falla, intentar con el secundario.

  Primario:   Ollama local (0 costo, mayor latencia)
  Secundario: Google Vertex AI (costo por token, menor latencia)
  Terciario:  OpenAI API (backup de emergencia)
""")

    class FakeProvider:
        def __init__(self, name: str, fail_rate: float, latency: float):
            self.name = name
            self.fail_rate = fail_rate
            self.latency = latency

        async def call(self, prompt: str) -> str:
            await asyncio.sleep(self.latency)
            if random.random() < self.fail_rate:
                raise ConnectionError(f"{self.name} no disponible")
            return f"[{self.name}] Respuesta para: {prompt[:30]}..."

    providers = [
        FakeProvider("Ollama (local)", fail_rate=0.8, latency=0.1),   # falla mucho (demo)
        FakeProvider("Vertex AI",      fail_rate=0.1, latency=0.3),
        FakeProvider("OpenAI",         fail_rate=0.05, latency=0.5),
    ]

    async def call_with_failover(prompt: str) -> str:
        for i, provider in enumerate(providers):
            try:
                result = await provider.call(prompt)
                if i > 0:
                    console.print(f"  [yellow]Failover exitoso: {provider.name}[/yellow]")
                return result
            except ConnectionError as e:
                console.print(f"  [red]✗ {e}[/red] → intentando siguiente...")
        raise RuntimeError("Todos los proveedores fallaron")

    prompts = [
        "¿Qué es un circuit breaker?",
        "Explica el patrón de retry con backoff",
        "¿Cómo funciona el rate limiting?",
    ]

    for prompt in prompts:
        console.print(f"\n[dim]Petición: '{prompt}'[/dim]")
        try:
            response = await call_with_failover(prompt)
            console.print(f"  [green]✓[/green] {response}")
        except RuntimeError as e:
            console.print(f"  [red]✗ {e}[/red]")

    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE D · RTO y RPO
# ─────────────────────────────────────────────────────────────────────────────

def parte_d_rto_rpo():
    console.print(Panel.fit(
        "[bold cyan]PARTE D · RTO y RPO — Disaster Recovery[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
[bold]RTO (Recovery Time Objective)[/bold]
  ¿Cuánto tiempo puede estar el servicio offline?
  Objetivo de tiempo máximo de recuperación.

[bold]RPO (Recovery Point Objective)[/bold]
  ¿Cuántos datos podemos perder?
  Objetivo de punto de recuperación (último backup válido).
""")

    table = Table(title="Estrategias de DR según RTO/RPO (proyecto TechCorp)")
    table.add_column("Estrategia", style="cyan")
    table.add_column("RTO", style="yellow")
    table.add_column("RPO", style="yellow")
    table.add_column("Costo", style="green")
    table.add_column("Cuándo usar")

    table.add_row(
        "Backup & Restore",
        "> 4 horas", "> 1 hora",
        "$", "Datos no críticos, sistemas internos"
    )
    table.add_row(
        "Pilot Light",
        "1–4 horas", "Minutos",
        "$$", "Sistemas medianamente críticos"
    )
    table.add_row(
        "Warm Standby",
        "Minutos", "Segundos",
        "$$$", "Producción con SLA 99.9%"
    )
    table.add_row(
        "Multi-site Active/Active",
        "Segundos", "0",
        "$$$$", "Misión crítica, banca, salud"
    )

    console.print(table)
    console.print()

    console.print("""
[bold cyan]Para el Proyecto Integrador TechCorp (3.000 consultas/mes):[/bold cyan]
  · RTO recomendado:  ≤ 4 horas  (sistema de apoyo, no crítico de vida)
  · RPO recomendado:  ≤ 1 hora   (audit logs se replican cada hora)
  · Estrategia:       Warm Standby con Cloud Run en segunda región
  · Costo adicional:  +~$30/mes (instancia en espera + replicación)
""")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE E · Ejercicio
# ─────────────────────────────────────────────────────────────────────────────

def parte_e_ejercicio():
    console.print(Panel.fit(
        "[bold green]PARTE E · Ejercicio[/bold green]",
        border_style="green",
    ))
    console.print("""
EJERCICIO: Consulta el estado del circuit breaker en el backend:

  # Con el backend corriendo (make backend):
  curl http://localhost:8000/api/health/circuit

  # Simular fallos llamando al endpoint de chat sin Ollama:
  TOKEN=$(curl -s -X POST http://localhost:8000/auth/token \\
    -d "username=dev@techcorp.com&password=dev123" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

  for i in {1..6}; do
    curl -s -X POST http://localhost:8000/api/chat \\
      -H "Authorization: Bearer $TOKEN" \\
      -H "Content-Type: application/json" \\
      -d '{"message":"test"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('circuit_state','error'))"
  done

  # Observa cómo el estado cambia: CERRADO → ABIERTO → SEMIABIERTO → CERRADO
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main_async():
    console.print(Panel(
        "[bold white]Lab 11 · Alta Disponibilidad[/bold white]\n"
        "[dim]Tema 5 · Seguridad y Alta Disponibilidad[/dim]",
        style="blue",
    ))

    parte_a_circuit_breaker()
    parte_b_health_checks()
    await parte_c_failover()
    parte_d_rto_rpo()
    parte_e_ejercicio()

    console.print(Panel.fit(
        "✅ Lab 11 completado. Siguiente: [bold]Lab 12 — Monitoreo y Logging[/bold]",
        border_style="green",
    ))


if __name__ == "__main__":
    asyncio.run(main_async())
