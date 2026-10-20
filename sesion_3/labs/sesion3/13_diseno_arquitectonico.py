#!/usr/bin/env python3
"""
Lab 13 · Diseño Arquitectónico y Documentación — Tema 6
=========================================================
Demostración de artefactos de documentación de arquitectura:

  Parte A: ADR (Architecture Decision Record)
  Parte B: C4 Model — niveles de abstracción
  Parte C: RFC — proceso de revisión técnica
  Parte D: Generador automático de plantillas
  Parte E: Ejercicio — documentar tu decisión arquitectónica

No requiere Ollama ni API key.
"""

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()

# ─────────────────────────────────────────────────────────────────────────────
# PARTE A · ADR — Architecture Decision Record
# ─────────────────────────────────────────────────────────────────────────────

def parte_a_adr():
    console.print(Panel.fit(
        "[bold cyan]PARTE A · ADR — Architecture Decision Record[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Un ADR documenta UNA decisión arquitectónica importante:
  · ¿Qué alternativas se evaluaron?
  · ¿Por qué se tomó esta decisión?
  · ¿Cuáles son las consecuencias?

Los ADRs viven junto al código (docs/adr/) — son el historial de "por qué"
que evita que el equipo repita debates o deshaga decisiones sin contexto.

Referencia: Michael Nygard (2011) "Documenting Architecture Decisions"
""")

    adr_ejemplo = """\
# ADR-001: Selección de Proveedor LLM para Fase 1

**Estado:** Aceptado
**Fecha:** 2026-10-19
**Autores:** Equipo TechCorp

## Contexto

El proyecto requiere integrar capacidades de LLM para análisis de documentos.
Evaluamos tres enfoques para la Fase 1 (MVP con 3.000 consultas/mes).

## Alternativas Evaluadas

| Opción | Costo/mes | Latencia | Privacidad | Complejidad |
|--------|-----------|----------|------------|-------------|
| Ollama local | $0 | Alta | ✅ Total | Alta (GPU) |
| Google Gemini | ~$37 | Baja | ⚠ GCP | Baja |
| OpenAI GPT-4o | ~$75 | Baja | ⚠ OpenAI | Baja |

## Decisión

**Usar Ollama en desarrollo + Gemini Flash en producción.**

- Ollama permite desarrollo offline sin costo ni fuga de datos
- Gemini Flash tiene la mejor relación calidad/precio en producción
- La abstracción del servicio permite cambiar de proveedor sin cambiar lógica

## Consecuencias

**Positivas:**
- Desarrollo sin dependencia de red ni costo de tokens
- Circuit Breaker puede hacer failover a OpenAI si Gemini falla

**Negativas:**
- Calidad diferente en dev vs prod (Ollama usa modelos más pequeños)
- Dos configuraciones de infraestructura que mantener

**Revisión:** En 6 meses, si el volumen supera 20.000 consultas/mes,
evaluar fine-tuning o modelo dedicado.
"""

    console.print(Panel(adr_ejemplo, title="ADR-001 (extracto)", border_style="dim"))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE B · C4 Model
# ─────────────────────────────────────────────────────────────────────────────

def parte_b_c4():
    console.print(Panel.fit(
        "[bold cyan]PARTE B · C4 Model — 4 Niveles de Abstracción[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
El C4 Model (Simon Brown) describe la arquitectura en 4 niveles:

  L1 · System Context  → ¿Quién usa el sistema y con qué interactúa?
  L2 · Containers      → ¿Cuáles son los componentes desplegables?
  L3 · Components      → ¿Qué hay dentro de cada contenedor?
  L4 · Code            → ¿Cómo está implementado cada componente?

Para un equipo de maestría, L1 y L2 son los más importantes.
""")

    # L1 — System Context (en texto ASCII)
    console.print("[bold]L1 — System Context:[/bold]")
    l1 = """\
  ┌─────────────────────────────────────────────────────────┐
  │                     TechCorp LLM Lab                     │
  │  (análisis de documentos internos con IA)                │
  └─────────────────────────────────────────────────────────┘
          │                      │                  │
    [Empleado]           [Sistema HR]         [Auditor]
    (consultas)          (documentos)         (logs)
"""
    console.print(Panel(l1, border_style="dim"))

    # L2 — Containers
    console.print("[bold]L2 — Containers:[/bold]")
    l2 = """\
  ┌────────────────────────────────────────────────────────────────┐
  │                       TechCorp LLM Lab                         │
  │                                                                 │
  │  ┌──────────────┐   HTTP    ┌──────────────┐   HTTP            │
  │  │  React SPA   │ ───────►  │  FastAPI     │ ──────►  Ollama   │
  │  │  (Vite 6)    │           │  (Backend)   │          (LLM)    │
  │  │  puerto 5173 │           │  puerto 8000 │                   │
  │  └──────────────┘           └──────┬───────┘                   │
  │                                    │                            │
  │                             ┌──────▼───────┐                   │
  │                             │  SQLite DB   │                   │
  │                             │  Audit JSONL │                   │
  │                             └──────────────┘                   │
  └────────────────────────────────────────────────────────────────┘
"""
    console.print(Panel(l2, border_style="dim"))

    table = Table(title="Descripción de Containers (L2)")
    table.add_column("Container", style="cyan")
    table.add_column("Tecnología")
    table.add_column("Responsabilidad")

    table.add_row("React SPA", "React 18, Vite 6", "UI para chat y visualización de logs")
    table.add_row("FastAPI Backend", "Python 3.12, FastAPI", "Auth, WAF, lógica de negocio, audit")
    table.add_row("Ollama", "Go, llama.cpp", "Inferencia LLM local (modelos cuantizados)")
    table.add_row("SQLite/JSONL", "SQLite, filesystem", "Estado de usuarios, audit trail")

    console.print(table)
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE C · RFC
# ─────────────────────────────────────────────────────────────────────────────

def parte_c_rfc():
    console.print(Panel.fit(
        "[bold cyan]PARTE C · RFC — Request For Comments[/bold cyan]",
        border_style="cyan",
    ))

    console.print("""
Un RFC propone un cambio significativo antes de implementarlo:
  · Cualquiera del equipo puede comentar
  · Se incorporan objeciones o mejoras
  · El autor responde a cada comentario
  · Se "acepta" o "rechaza" con consenso

Diferencia con ADR:
  · RFC: propuesta ANTES de decidir (proceso colaborativo)
  · ADR: registro DESPUÉS de decidir (memoria del equipo)
""")

    rfc_extracto = """\
# RFC-003: Migrar Audit Log de JSONL a PostgreSQL

**Estado:** En revisión
**Fecha:** 2026-10-19
**Autor:** dev@techcorp.com
**Revisores:** @arch-team, @security-team

## Propuesta

Migrar el audit trail actual (JSONL append-only) a PostgreSQL con
particionado por mes, para soportar búsqueda y análisis a escala.

## Motivación

- JSONL no permite búsquedas eficientes (grep O(n))
- Sin transacciones: riesgo de entradas truncadas bajo carga
- No soporta queries de negocio (¿cuántos WAF blocks por usuario esta semana?)

## Diseño Propuesto

```sql
CREATE TABLE audit_events (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp  TIMESTAMPTZ NOT NULL,
  event      TEXT NOT NULL,
  user_id    TEXT,
  ip         TEXT,
  details    JSONB,
  prev_hash  TEXT NOT NULL,
  hash       TEXT NOT NULL
) PARTITION BY RANGE (timestamp);
```

## Alternativas No Adoptadas

- BigQuery: excelente para analytics pero costo por query
- Elasticsearch: potente pero operacionalmente complejo para este volumen

## Comentarios Abiertos

- [ ] @arch-team: ¿el hash chain sigue siendo verificable con particionado?
- [ ] @security-team: ¿cumple requisitos de retención de 7 años?
"""

    console.print(Panel(rfc_extracto, title="RFC-003 (extracto)", border_style="dim"))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# PARTE D · Generador de plantillas
# ─────────────────────────────────────────────────────────────────────────────

def parte_d_generador():
    console.print(Panel.fit(
        "[bold cyan]PARTE D · Generador de Plantillas de Documentación[/bold cyan]",
        border_style="cyan",
    ))

    templates = {
        "adr": {
            "filename": "ADR-{number:03d}-{slug}.md",
            "content": """\
# ADR-{number:03d}: {title}

**Estado:** [Propuesto | En revisión | Aceptado | Deprecado | Supersedido por ADR-XXX]
**Fecha:** {date}
**Autores:** {authors}

## Contexto

[Describe el problema o situación que requiere una decisión. ¿Qué fuerzas están en juego?]

## Alternativas Evaluadas

| Opción | Pros | Contras | Costo | Complejidad |
|--------|------|---------|-------|-------------|
| Opción A | ... | ... | $ | Baja |
| Opción B | ... | ... | $$ | Media |

## Decisión

[Explica la opción seleccionada y por qué. Usa voz activa: "Decidimos usar X porque Y."]

## Consecuencias

**Positivas:**
- ...

**Negativas:**
- ...

**Deuda técnica generada:** [Ninguna / lista de trade-offs a resolver después]

**Próxima revisión:** [Fecha o hito para reevaluar esta decisión]
""",
        },
        "prd": {
            "filename": "PRD-{number:03d}-{slug}.md",
            "content": """\
# PRD-{number:03d}: {title}

**Estado:** [Draft | En revisión | Aprobado | En desarrollo | Lanzado]
**Fecha:** {date}
**Product Owner:** {authors}

## Resumen Ejecutivo

[Una párrafo: ¿qué se está construyendo, para quién y qué problema resuelve?]

## Problema

**Usuario objetivo:** [Quién]
**Pain point:** [Qué problema tienen hoy]
**Impacto si no se resuelve:** [Consecuencias de no hacer nada]

## Solución Propuesta

[Describe la funcionalidad a alto nivel. No entra en detalles técnicos.]

## Criterios de Éxito (KPIs)

| Métrica | Baseline hoy | Meta en 3 meses |
|---------|-------------|-----------------|
| ... | ... | ... |

## Casos de Uso

1. **[Nombre del caso]:** Como [rol], quiero [acción] para [beneficio].
2. ...

## Fuera de Alcance

[Qué NO incluye este PRD para evitar scope creep]

## Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|-----------|
| ... | Media | Alto | ... |
""",
        },
    }

    for name, tmpl in templates.items():
        console.print(f"[bold]Plantilla: {name.upper()}[/bold]")
        filled = tmpl["content"].format(
            number=1,
            slug="seleccion-llm-proveedor",
            title="Selección de Proveedor LLM",
            date=datetime.now().strftime("%Y-%m-%d"),
            authors="Equipo TechCorp",
        )
        # Solo mostrar las primeras 15 líneas
        preview = "\n".join(filled.splitlines()[:15]) + "\n  ..."
        console.print(Panel(preview, border_style="dim", title=tmpl["filename"].format(
            number=1, slug="ejemplo"
        )))

    console.print("""
[bold cyan]Tip:[/bold cyan] El backend expone las plantillas en:
  GET /api/architecture/templates   → lista todas las plantillas disponibles
  GET /api/architecture/canvas      → retorna el ADR interactivo del proyecto
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
EJERCICIO: Documenta una decisión de tu Proyecto Integrador.

PASO 1: Consulta el canvas arquitectónico del backend:
  curl -s http://localhost:8000/api/architecture/canvas | python3 -m json.tool

PASO 2: Ejecuta un análisis de costos para tu escenario:
  curl -s -X POST http://localhost:8000/api/architecture/costs \\
    -H "Content-Type: application/json" \\
    -d '{
      "scenarios": [
        {
          "name": "Mi escenario",
          "llamadas_mes": 5000,
          "tokens_por_llamada": 200,
          "proveedor": "google",
          "infra_mensual_usd": 30,
          "ingenieros": 1,
          "horas_setup": 40
        }
      ],
      "meses": 24
    }' | python3 -m json.tool

PASO 3: Elige la decisión más importante de tu proyecto y escribe un ADR:
  · ¿Qué proveedor de LLM usarás y por qué?
  · ¿Qué base de datos? ¿SQLite, PostgreSQL, Firestore?
  · ¿Despliegue en Cloud Run, GKE, o VM?

El ADR debe tener:
  - Al menos 2 alternativas evaluadas en tabla comparativa
  - Una decisión clara con justificación
  - Al menos una consecuencia positiva y una negativa
""")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    console.print(Panel(
        "[bold white]Lab 13 · Diseño Arquitectónico[/bold white]\n"
        "[dim]Tema 6 · Diseño y Documentación[/dim]",
        style="blue",
    ))

    parte_a_adr()
    parte_b_c4()
    parte_c_rfc()
    parte_d_generador()
    parte_e_ejercicio()

    console.print(Panel.fit(
        "✅ Lab 13 completado. Siguiente: [bold]Lab 14 — Análisis de Costos[/bold]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
