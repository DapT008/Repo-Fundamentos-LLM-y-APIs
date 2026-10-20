#!/usr/bin/env python3
"""
Lab 14 · Análisis de Costos — Tema 6
======================================
TCO (Total Cost of Ownership) del Proyecto Integrador TechCorp a 24 meses.

  Parte A: Componentes del costo de un proyecto LLM
  Parte B: Tres escenarios de despliegue
  Parte C: Análisis de sensibilidad (¿qué pasa si crecemos?)
  Parte D: Plantilla de estimación para el Proyecto Integrador
  Parte E: Recomendación y próximos pasos

No requiere Ollama ni API key.
"""

from dataclasses import dataclass, field
from typing import Literal

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# Datos de precios (aproximados, octubre 2026)
# ─────────────────────────────────────────────────────────────────────────────

# Precio por 1M tokens (input + output promediado)
LLM_PRICE_PER_1M_TOKENS = {
    "openai_gpt4o":     {"input": 2.50,  "output": 10.00, "nombre": "OpenAI GPT-4o"},
    "anthropic_claude": {"input": 3.00,  "output": 15.00, "nombre": "Claude 3.5 Sonnet"},
    "google_gemini":    {"input": 1.25,  "output": 5.00,  "nombre": "Gemini 1.5 Pro"},
    "ollama_local":     {"input": 0.00,  "output": 0.00,  "nombre": "Ollama + Llama 3.2 (local)"},
}

INFRA_MONTHLY = {
    "cloud_run":        {"costo": 25,   "nombre": "Cloud Run (serverless)"},
    "gke_autopilot":    {"costo": 150,  "nombre": "GKE Autopilot"},
    "vm_e2_standard":   {"costo": 90,   "nombre": "VM e2-standard-2 (GPU básica)"},
    "local_server":     {"costo": 10,   "nombre": "Servidor local (electricidad)"},
}

# Costo hora ingeniero LATAM (USD)
ENGINEER_HOURLY_USD = 35

# Tipo de cambio aproximado
FX_RATES = {"USD": 1, "COP": 4200, "MXN": 17.5, "BRL": 5.0}


# ─────────────────────────────────────────────────────────────────────────────
# PARTE A · Componentes del costo
# ─────────────────────────────────────────────────────────────────────────────

def parte_a_componentes():
    console.print(Panel.fit(
        "[bold cyan]PARTE A · Componentes del Costo de un Proyecto LLM[/bold cyan]",
        border_style="cyan",
    ))

    table = Table(title="Estructura de Costos — Proyecto LLM Empresarial")
    table.add_column("Categoría", style="cyan")
    table.add_column("Componentes", style="white")
    table.add_column("Tipo")
    table.add_column("% típico del TCO")

    table.add_row(
        "LLM API / Inferencia",
        "Tokens de input + output por llamada",
        "Variable",
        "30–60%",
    )
    table.add_row(
        "Infraestructura",
        "Servidor/Cloud Run/K8s, red, almacenamiento",
        "Fijo + Variable",
        "15–30%",
    )
    table.add_row(
        "Recursos Humanos",
        "Ingenieros: diseño, desarrollo, operación",
        "Fijo",
        "40–60% (total)",
    )
    table.add_row(
        "Herramientas SaaS",
        "Monitoring, CI/CD, gestión de secretos, APM",
        "Fijo",
        "5–10%",
    )
    table.add_row(
        "Licencias",
        "IDEs, frameworks enterprise, soporte",
        "Fijo",
        "2–5%",
    )
    table.add_row(
        "Seguridad & Compliance",
        "Auditorías, certificaciones, pen testing",
        "Variable",
        "3–8%",
    )

    console.print(table)
    console.print()

    console.print("""
[bold cyan]Nota para LATAM:[/bold cyan]
  · Los costos de infraestructura en nube son en USD → impacto cambiario importante
  · El costo de recurso humano en LATAM es ~3–5x menor que en EEUU/Europa
  · Esto hace que las soluciones con más ingeniería y menos API sean más rentables en LATAM
  · Ejemplo: Ollama (costo API $0) + más ingeniería puede ser más barato que OpenAI + menos ingeniería
""")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE B · Tres escenarios
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Scenario:
    nombre: str
    llamadas_mes: int
    tokens_por_llamada: int
    proveedor: str
    infra: str
    ingenieros: int
    horas_setup: int
    descripcion: str
    tags: list[str] = field(default_factory=list)


def calcular_tco(s: Scenario, meses: int = 24, moneda: str = "USD") -> dict:
    fx = FX_RATES[moneda]
    llm = LLM_PRICE_PER_1M_TOKENS[s.proveedor]
    infra = INFRA_MONTHLY[s.infra]

    # Tokens mensuales
    tokens_mes = s.llamadas_mes * s.tokens_por_llamada
    tokens_millones = tokens_mes / 1_000_000

    # Costo LLM mensual (60% input, 40% output)
    costo_llm_mes = (
        tokens_millones * 0.6 * llm["input"]
        + tokens_millones * 0.4 * llm["output"]
    )

    # Infraestructura mensual
    costo_infra_mes = infra["costo"]

    # Herramientas
    costo_tools_mes = 35  # monitoring, CI/CD

    # Costo operativo mensual (sin RRHH)
    costo_op_mes = costo_llm_mes + costo_infra_mes + costo_tools_mes

    # Setup (RRHH una vez)
    costo_setup = s.ingenieros * s.horas_setup * ENGINEER_HOURLY_USD

    # TCO
    tco = costo_setup + (costo_op_mes * meses)

    return {
        "scenario": s.nombre,
        "proveedor_llm": llm["nombre"],
        "infra": infra["nombre"],
        "llamadas_mes": s.llamadas_mes,
        "tokens_mes": f"{tokens_mes:,}",
        "costos": {
            "llm_mensual": round(costo_llm_mes * fx, 2),
            "infra_mensual": round(costo_infra_mes * fx, 2),
            "tools_mensual": round(costo_tools_mes * fx, 2),
            "total_mensual": round(costo_op_mes * fx, 2),
        },
        "setup_unico": round(costo_setup * fx, 2),
        "tco_total": round(tco * fx, 2),
        "costo_por_llamada_centavos": round(costo_op_mes * fx / s.llamadas_mes * 100, 4),
        "moneda": moneda,
        "tags": s.tags,
    }


def parte_b_escenarios():
    console.print(Panel.fit(
        "[bold cyan]PARTE B · TCO a 24 Meses — Tres Escenarios[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Caso de estudio: TechCorp Latinoamérica
  Producto: Asistente de IA para soporte técnico interno
  Volumen: 3.000 consultas/mes
  Usuarios: 150 empleados en 5 países LATAM
""")

    scenarios = [
        Scenario(
            nombre="A · Gestión Cloud (OpenAI)",
            llamadas_mes=3000,
            tokens_por_llamada=1500,
            proveedor="openai_gpt4o",
            infra="cloud_run",
            ingenieros=2,
            horas_setup=120,
            descripcion="OpenAI API + Cloud Run. Rápido de desplegar, mayor costo por token.",
            tags=["🚀 rápido", "💰 mayor costo"],
        ),
        Scenario(
            nombre="B · Google Vertex AI",
            llamadas_mes=3000,
            tokens_por_llamada=1500,
            proveedor="google_gemini",
            infra="cloud_run",
            ingenieros=2,
            horas_setup=160,
            descripcion="Gemini 1.5 Pro en Vertex AI. Datos en LATAM, integración GCP.",
            tags=["🔒 privacidad LATAM", "⚡ buen precio"],
        ),
        Scenario(
            nombre="C · Ollama Self-Hosted",
            llamadas_mes=3000,
            tokens_por_llamada=1500,
            proveedor="ollama_local",
            infra="vm_e2_standard",
            ingenieros=2,
            horas_setup=200,
            descripcion="Llama 3.2 en VM propia. Cero costo API, mayor inversión en ingeniería.",
            tags=["🔒 100% privado", "💻 más ingeniería"],
        ),
    ]

    results = [calcular_tco(s) for s in scenarios]

    # Tabla resumen
    table = Table(title="Comparación TCO — TechCorp (USD, 24 meses)")
    table.add_column("Escenario", style="cyan", min_width=28)
    table.add_column("LLM/mes", justify="right")
    table.add_column("Infra/mes", justify="right")
    table.add_column("Total/mes", justify="right", style="yellow")
    table.add_column("Setup", justify="right")
    table.add_column("TCO 24m", justify="right", style="bold green")
    table.add_column("¢/llamada", justify="right")

    min_tco = min(r["tco_total"] for r in results)

    for r in results:
        marker = " ✓ menor" if r["tco_total"] == min_tco else ""
        table.add_row(
            r["scenario"],
            f"${r['costos']['llm_mensual']:,.0f}",
            f"${r['costos']['infra_mensual']:,.0f}",
            f"${r['costos']['total_mensual']:,.0f}",
            f"${r['setup_unico']:,.0f}",
            f"${r['tco_total']:,.0f}{marker}",
            f"{r['costo_por_llamada_centavos']:.2f}¢",
        )

    console.print(table)
    console.print()

    # Análisis por escenario
    for r in results:
        console.print(f"[bold]{r['scenario']}[/bold]  {' · '.join(r['tags'])}")
        console.print(f"  Proveedor: {r['proveedor_llm']} | Infra: {r['infra']}")
        console.print(f"  Mensual operativo: ${r['costos']['total_mensual']:,.0f} | TCO 24m: ${r['tco_total']:,.0f}")
        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE C · Análisis de sensibilidad
# ─────────────────────────────────────────────────────────────────────────────

def parte_c_sensibilidad():
    console.print(Panel.fit(
        "[bold cyan]PARTE C · Análisis de Sensibilidad[/bold cyan]",
        border_style="cyan",
    ))

    console.print("¿Qué pasa con el TCO si el volumen cambia?\n")

    volumenes = [500, 1_000, 3_000, 10_000, 50_000]
    proveedores = [
        ("openai_gpt4o", "cloud_run"),
        ("google_gemini", "cloud_run"),
        ("ollama_local", "vm_e2_standard"),
    ]
    nombres = ["OpenAI+CR", "Gemini+CR", "Ollama+VM"]

    table = Table(title="TCO 24m en USD según volumen mensual")
    table.add_column("Llamadas/mes", style="cyan", justify="right")
    for n in nombres:
        table.add_column(n, justify="right")
    table.add_column("Más barato", style="green")

    for vol in volumenes:
        row_values = []
        for proveedor, infra in proveedores:
            s = Scenario(
                nombre=proveedor, llamadas_mes=vol, tokens_por_llamada=1500,
                proveedor=proveedor, infra=infra, ingenieros=2,
                horas_setup=160, descripcion=""
            )
            r = calcular_tco(s)
            row_values.append(r["tco_total"])

        min_val = min(row_values)
        min_idx = row_values.index(min_val)

        table.add_row(
            f"{vol:,}",
            *[f"${v:,.0f}" for v in row_values],
            nombres[min_idx],
        )

    console.print(table)
    console.print()

    console.print("""
[bold cyan]Conclusión del análisis de sensibilidad:[/bold cyan]
  · A [yellow]bajo volumen[/yellow] (<1.000 llamadas/mes):  OpenAI o Gemini ganan — setup mínimo
  · A [yellow]volumen medio[/yellow] (1.000–10.000/mes):    Gemini + Cloud Run es competitivo
  · A [yellow]alto volumen[/yellow] (>10.000 llamadas/mes): Ollama self-hosted gana claramente
  → El "crossover" depende del costo de la VM y del precio de tokens del proveedor cloud
""")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE D · Plantilla del Proyecto Integrador
# ─────────────────────────────────────────────────────────────────────────────

def parte_d_plantilla():
    console.print(Panel.fit(
        "[bold cyan]PARTE D · Plantilla — Análisis de Costos del Proyecto Integrador[/bold cyan]",
        border_style="cyan",
    ))

    plantilla = """
ANÁLISIS DE COSTOS — PROYECTO INTEGRADOR
=========================================
Proyecto:     ____________________________________
Equipo:       ____________________________________
Fecha:        ____________________________________

1. SUPUESTOS DE NEGOCIO
   Usuarios activos/mes:     ______
   Consultas por usuario/mes: ______
   Volumen total/mes:        ______
   Crecimiento esperado:     ______% anual

2. COSTOS DE INFRAESTRUCTURA
   Proveedor LLM elegido:    ______________________
   Modelo:                   ______________________
   Costo por 1M tokens (in): $ ______
   Costo por 1M tokens (out): $ ______
   Tokens promedio/consulta:  ______
   COSTO LLM/mes:            $ ______

   Infraestructura:           ______________________
   COSTO INFRA/mes:           $ ______

   Herramientas y SaaS:       ______________________
   COSTO TOOLS/mes:           $ ______

   TOTAL OPERATIVO/mes:       $ ______

3. COSTOS DE RECURSOS HUMANOS (Setup inicial)
   N° ingenieros:             ______
   Horas estimadas setup:     ______
   Tarifa hora (USD):         $ ______
   TOTAL SETUP RRRHH:         $ ______

4. TCO A 24 MESES
   Setup inicial:             $ ______
   Operativo × 24 meses:      $ ______
   TOTAL TCO 24m:             $ ______
   TOTAL TCO 24m (COP/MXN):  $ ______ (TC: ______)

5. COSTO POR CONSULTA
   (TCO 24m) / (consultas totales 24m) = $ ______ / consulta

6. ESCENARIOS DE RIESGO
   +50% volumen → TCO = $ ______
   -30% volumen → TCO = $ ______
   Migración a otro proveedor → costo estimado: $ ______

7. RECOMENDACIÓN
   Proveedor recomendado:     ______________________
   Justificación:             ______________________
   Revisión de precios:       Cada ______ meses
"""
    console.print(f"[dim]{plantilla}[/dim]")


# ─────────────────────────────────────────────────────────────────────────────
# PARTE E · Recomendación y próximos pasos
# ─────────────────────────────────────────────────────────────────────────────

def parte_e_recomendacion():
    console.print(Panel.fit(
        "[bold green]PARTE E · Recomendación y Próximos Pasos[/bold green]",
        border_style="green",
    ))

    console.print("""
RECOMENDACIÓN PARA TECHCORP (3.000 consultas/mes)
==================================================

[bold green]Escenario recomendado: B — Google Vertex AI + Cloud Run[/bold green]

Razones:
  ✓ Datos procesados en región southamerica-east1 (São Paulo) → cumple con
    requisitos de privacidad de datos en LATAM
  ✓ TCO 24m competitivo vs OpenAI (~25% más barato)
  ✓ Integración nativa con el ecosistema GCP (Cloud Run, Logging, IAM)
  ✓ Sin necesidad de gestionar servidores GPU propios
  ✓ Escalabilidad automática — pago por uso real

Plan de migración si el volumen supera 10.000 llamadas/mes:
  → Evaluar Ollama self-hosted en GKE Autopilot
  → El "crossover" ocurre aproximadamente a los 8.000 llamadas/mes
  → Tiempo de migración estimado: 3–4 semanas de ingeniería

PRÓXIMOS PASOS (Proyecto Integrador)
=====================================
  1. Completar el ADR-001 con esta decisión (ver Lab 13)
  2. Crear cuenta de prueba en GCP ($300 de crédito gratuito)
  3. Desplegar la Parte 2 del ejemplo de Agent Platform (ver gcp-agent-platform/)
  4. Medir latencia y costo real en 1 semana de prueba
  5. Presentar análisis comparativo al equipo en la próxima sesión

EJERCICIO: Usa el endpoint /api/architecture/costs del backend para
calcular el TCO de tu propio proyecto:

  curl -X POST http://localhost:8000/api/architecture/costs \\
    -H "Authorization: Bearer $TOKEN" \\
    -H "Content-Type: application/json" \\
    -d '{"project_name": "Mi Proyecto", "currency": "COP",
         "scenarios": [{"name": "Prueba", "monthly_llm_calls": 500,
                        "provider": "google", "infrastructure": "cloud_run"}]}'
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold white]Lab 14 · Análisis de Costos — Proyecto Integrador[/bold white]\n"
        "[dim]Tema 6 · Diseño y Documentación[/dim]",
        style="blue",
    ))

    parte_a_componentes()
    parte_b_escenarios()
    parte_c_sensibilidad()
    parte_d_plantilla()
    parte_e_recomendacion()

    console.print(Panel.fit(
        "✅ Lab 14 completado — ¡Todos los labs de la Sesión 3 terminados!",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
