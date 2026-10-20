"""
Architecture Router — Tema 6: Diseño y Documentación

GET  /api/architecture/canvas    → plantilla ADR vacía para rellenar
POST /api/architecture/costs     → análisis TCO a 24 meses (3 escenarios)
GET  /api/architecture/templates → listado de plantillas disponibles
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Literal

from app.routers.auth import get_current_user, TokenData

router = APIRouter()


# ── Modelos ──────────────────────────────────────────────────────────────────

class CostScenario(BaseModel):
    name: str
    monthly_llm_calls: int = Field(..., ge=100, description="Llamadas LLM por mes")
    avg_tokens_per_call: int = Field(default=1500)
    provider: Literal["openai", "anthropic", "google", "ollama_local"] = "openai"
    team_engineers: int = Field(default=1, ge=1, le=20)
    infrastructure: Literal["cloud_run", "kubernetes", "vm", "local"] = "cloud_run"


class CostAnalysisRequest(BaseModel):
    project_name: str = Field(default="Proyecto Integrador TechCorp")
    currency: Literal["USD", "COP", "MXN", "BRL"] = "USD"
    scenarios: list[CostScenario] = Field(
        default=[
            CostScenario(
                name="Conservador", monthly_llm_calls=500,
                provider="openai", infrastructure="cloud_run"
            ),
            CostScenario(
                name="Realista", monthly_llm_calls=3000,
                provider="openai", infrastructure="cloud_run"
            ),
            CostScenario(
                name="Optimista (Ollama)", monthly_llm_calls=3000,
                provider="ollama_local", infrastructure="vm"
            ),
        ]
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/canvas",
    summary="Plantilla ADR — Architecture Decision Record",
)
async def get_adr_template(
    current_user: TokenData = Depends(get_current_user),
):
    """
    Retorna una plantilla de Architecture Decision Record (ADR) lista para rellenar.

    Un ADR documenta una decisión arquitectónica importante:
    - **Contexto**: ¿qué problema queremos resolver?
    - **Decisión**: ¿qué elegimos y por qué?
    - **Consecuencias**: ¿qué ventajas y desventajas trae esta decisión?

    Referencia: https://adr.github.io/
    """
    return {
        "template": "Architecture Decision Record (ADR)",
        "version": "1.0",
        "structure": {
            "ADR-NNN": {
                "titulo": "Elección del motor LLM para TechCorp IA Assistant",
                "estado": "Propuesto | Aceptado | Rechazado | Deprecado | Supersedido",
                "fecha": "YYYY-MM-DD",
                "autores": ["nombre@techcorp.com"],
                "revision": ["arquitecto@techcorp.com"],
            },
            "contexto": {
                "descripcion": "Describe el problema de arquitectura que motiva esta decisión.",
                "factores": [
                    "Volumen esperado: 3.000 consultas/mes",
                    "Presupuesto máximo: USD 500/mes en infraestructura",
                    "Requisito de privacidad: datos de clientes no pueden salir de LATAM",
                    "Tiempo de respuesta máximo: 3 segundos P95",
                ],
                "alternativas_evaluadas": [
                    "OpenAI GPT-4o via API",
                    "Google Gemini 1.5 Pro via Vertex AI",
                    "Ollama + Llama 3.2 en VM propia",
                ],
            },
            "decision": {
                "elegida": "DESCRIBE LA OPCIÓN ELEGIDA",
                "justificacion": "EXPLICA POR QUÉ",
                "criterios_de_evaluacion": {
                    "costo_mensual": "USD/mes a 3.000 llamadas",
                    "latencia_p95": "segundos",
                    "privacidad_datos": "sí/no",
                    "madurez_api": "alta/media/baja",
                    "soporte_latam": "sí/no",
                },
                "matriz_decision": [
                    {
                        "opcion": "OpenAI GPT-4o",
                        "costo": "$285/mes",
                        "latencia": "1.5s",
                        "privacidad": "No (datos en EEUU)",
                        "madurez": "Alta",
                    },
                    {
                        "opcion": "Google Gemini 1.5 Pro",
                        "costo": "$180/mes",
                        "latencia": "1.8s",
                        "privacidad": "Sí (región southamerica-east1)",
                        "madurez": "Alta",
                    },
                    {
                        "opcion": "Ollama + Llama 3.2",
                        "costo": "$95/mes (VM)",
                        "latencia": "2.5s",
                        "privacidad": "Sí (local)",
                        "madurez": "Media",
                    },
                ],
            },
            "consecuencias": {
                "positivas": [
                    "VENTAJA 1",
                    "VENTAJA 2",
                ],
                "negativas": [
                    "DESVENTAJA 1 — Plan de mitigación",
                ],
                "neutrales": [
                    "ASPECTO NEUTRO",
                ],
            },
            "referencias": [
                "https://adr.github.io/",
                "https://cloud.google.com/vertex-ai/pricing",
            ],
        },
    }


@router.post(
    "/costs",
    summary="Análisis de costos TCO — Proyecto Integrador (Tema 6)",
)
async def analyze_costs(
    body: CostAnalysisRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """
    Estima el **Total Cost of Ownership (TCO)** del Proyecto Integrador a 24 meses.

    Componentes del costo:
    - **LLM API**: costo por token según proveedor
    - **Infraestructura**: Cloud Run, Kubernetes, VM o local
    - **Recursos humanos**: horas de ingeniería estimadas
    - **Licencias**: herramientas de monitoreo, CI/CD, etc.

    Los precios son aproximados (octubre 2026) y varían según volumen y acuerdos.
    """
    # Precios aproximados por 1M tokens de input + output (USD)
    LLM_COSTS_PER_1M = {
        "openai":       {"input": 2.50, "output": 10.00, "name": "OpenAI GPT-4o"},
        "anthropic":    {"input": 3.00, "output": 15.00, "name": "Claude 3.5 Sonnet"},
        "google":       {"input": 1.25, "output": 5.00,  "name": "Gemini 1.5 Pro"},
        "ollama_local": {"input": 0.00, "output": 0.00,  "name": "Ollama (local)"},
    }

    # Costo mensual de infraestructura (USD)
    INFRA_COSTS = {
        "cloud_run":  {"monthly": 25,  "name": "Google Cloud Run"},
        "kubernetes": {"monthly": 150, "name": "GKE Autopilot"},
        "vm":         {"monthly": 90,  "name": "VM e2-standard-2 (GPU mínima)"},
        "local":      {"monthly": 10,  "name": "Servidor propio (electricidad)"},
    }

    # Costo hora de ingeniero (estimado LATAM, USD)
    ENGINEER_HOURLY = 35

    results = []

    for scenario in body.scenarios:
        llm = LLM_COSTS_PER_1M[scenario.provider]
        infra = INFRA_COSTS[scenario.infrastructure]

        # Costo mensual LLM
        total_tokens_per_month = (
            scenario.monthly_llm_calls * scenario.avg_tokens_per_call
        )
        tokens_in_million = total_tokens_per_month / 1_000_000
        # Asumimos 60% input, 40% output
        monthly_llm_cost = (
            tokens_in_million * 0.6 * llm["input"]
            + tokens_in_million * 0.4 * llm["output"]
        )

        # Horas de ingeniería estimadas: 20h/semana primer mes, 10h/semana después
        monthly_engineering_cost = scenario.team_engineers * (
            ENGINEER_HOURLY * 80  # ~80h primer mes
        )

        # Licencias y herramientas (monitoreo, CI/CD, alertas)
        monthly_tools_cost = 30

        # Total mensual
        monthly_total = (
            monthly_llm_cost
            + infra["monthly"]
            + monthly_tools_cost
        )

        # TCO 24 meses: primer mes incluye setup (horas ingeniería)
        setup_cost = monthly_engineering_cost
        operational_24m = monthly_total * 24
        tco_24m = setup_cost + operational_24m

        # Conversión de moneda (aproximada)
        FX = {"USD": 1, "COP": 4200, "MXN": 17.5, "BRL": 5.0}
        fx_rate = FX[body.currency]

        results.append({
            "escenario": scenario.name,
            "proveedor_llm": llm["name"],
            "infraestructura": infra["name"],
            "llamadas_mes": scenario.monthly_llm_calls,
            "tokens_mes": f"{total_tokens_per_month:,}",
            "costos_mensuales": {
                "llm_api": round(monthly_llm_cost * fx_rate, 2),
                "infraestructura": round(infra["monthly"] * fx_rate, 2),
                "herramientas": round(monthly_tools_cost * fx_rate, 2),
                "total": round(monthly_total * fx_rate, 2),
            },
            "setup_inicial": round(setup_cost * fx_rate, 2),
            "tco_24_meses": round(tco_24m * fx_rate, 2),
            "moneda": body.currency,
        })

    # Escenario de menor TCO
    cheapest = min(results, key=lambda x: x["tco_24_meses"])

    return {
        "proyecto": body.project_name,
        "horizonte_meses": 24,
        "moneda": body.currency,
        "escenarios": results,
        "recomendacion": {
            "menor_tco": cheapest["escenario"],
            "tco": cheapest["tco_24_meses"],
            "nota": (
                "El análisis incluye costos de API, infraestructura y herramientas. "
                "Los costos de recursos humanos se calculan como setup inicial. "
                "Revisar con el equipo de finanzas antes de comprometer presupuesto."
            ),
        },
    }


@router.get(
    "/templates",
    summary="Listado de plantillas de documentación disponibles",
)
async def list_templates(
    current_user: TokenData = Depends(get_current_user),
):
    """
    Lista las plantillas de documentación arquitectónica disponibles en el repositorio.
    Ver `docs/plantillas/` para los archivos Markdown completos.
    """
    return {
        "plantillas": [
            {
                "id": "adr",
                "nombre": "Architecture Decision Record (ADR)",
                "descripcion": "Documenta una decisión arquitectónica con contexto, alternativas y consecuencias",
                "path": "docs/plantillas/adr_template.md",
                "referencia": "https://adr.github.io/",
            },
            {
                "id": "rfc",
                "nombre": "Request for Comments (RFC)",
                "descripcion": "Propuesta técnica para revisión del equipo antes de implementar",
                "path": "docs/plantillas/rfc_template.md",
                "referencia": "Proceso RFC interno adaptado de IETF RFC",
            },
            {
                "id": "c4",
                "nombre": "Diagrama C4",
                "descripcion": "Arquitectura en 4 niveles: Contexto, Contenedores, Componentes, Código",
                "path": "docs/plantillas/c4_template.md",
                "referencia": "https://c4model.com/",
            },
            {
                "id": "prd",
                "nombre": "Product Requirements Document (PRD)",
                "descripcion": "Define el alcance, objetivos y requisitos del producto",
                "path": "docs/plantillas/prd_template.md",
            },
        ]
    }
