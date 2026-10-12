"""
Router: architecture
Endpoints de evaluación de proveedores, TCO y patrones arquitectónicos.
Tema #3: Consideraciones de costos
Tema #4: Patrones y escalabilidad
"""

from __future__ import annotations

import math
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


# ─────────────────────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────────────────────

class ProveedorRequest(BaseModel):
    pesos: dict[str, float] = Field(
        default={
            "costo": 0.25,
            "cumplimiento": 0.20,
            "latencia": 0.15,
            "ecosistema": 0.15,
            "privacidad": 0.10,
            "soporte_ti": 0.10,
            "soporte_esp": 0.05,
        },
        description="Pesos para cada criterio (deben sumar ≈1.0)",
    )
    caso_uso: Optional[str] = Field(
        None,
        description="Caso de uso predefinido (banco_brasil, ecommerce_mx, startup_ar, hospital_cl)",
    )


class TCORequest(BaseModel):
    escenario: str = Field(
        ...,
        description="api_publica | plataforma_gestionada | on_premise",
        pattern="^(api_publica|plataforma_gestionada|on_premise)$",
    )
    tokens_dia: int = Field(1_000_000, ge=1_000, le=1_000_000_000)
    horizonte_meses: int = Field(24, ge=6, le=60)
    tasa_descuento_anual: float = Field(0.10, ge=0.0, le=0.50)


class ScalingRequest(BaseModel):
    demanda_tps: int = Field(..., ge=100, le=500_000)
    estrategia: str = Field("horizontal", pattern="^(horizontal|vertical|mixta)$")
    presupuesto_hora_usd: Optional[float] = None


# ─────────────────────────────────────────────────────────────
# DATOS DE REFERENCIA
# ─────────────────────────────────────────────────────────────

PROVEEDORES_DB = [
    {
        "nombre": "OpenAI",
        "categoria": "FRONTIER",
        "latencia_p95_ms": 3500,
        "sla_uptime": 99.9,
        "soporte_espanol": False,
        "n_certificaciones": 3,
        "puntaje_eco": 5,
        "puntaje_privacidad": 3,
        "puntaje_soporte_ti": 3,
        "precio_mid_usd_M": (2.50 + 10.00) / 2,   # gpt-4o avg
        "notas": "Mejor ecosistema de integraciones. Datos en EE.UU.",
    },
    {
        "nombre": "Anthropic",
        "categoria": "FRONTIER",
        "latencia_p95_ms": 3200,
        "sla_uptime": 99.9,
        "soporte_espanol": False,
        "n_certificaciones": 2,
        "puntaje_eco": 4,
        "puntaje_privacidad": 4,
        "puntaje_soporte_ti": 3,
        "precio_mid_usd_M": (3.00 + 15.00) / 2,
        "notas": "Modelo constitucional. Fuerte en reasoning.",
    },
    {
        "nombre": "Google Gemini",
        "categoria": "FRONTIER",
        "latencia_p95_ms": 2800,
        "sla_uptime": 99.95,
        "soporte_espanol": True,
        "n_certificaciones": 4,
        "puntaje_eco": 5,
        "puntaje_privacidad": 4,
        "puntaje_soporte_ti": 4,
        "precio_mid_usd_M": (0.30 + 2.50) / 2,    # flash avg
        "notas": "Mejor costo/performance. Soporte en español.",
    },
    {
        "nombre": "Azure OpenAI",
        "categoria": "FRONTIER",
        "latencia_p95_ms": 3800,
        "sla_uptime": 99.9,
        "soporte_espanol": True,
        "n_certificaciones": 5,
        "puntaje_eco": 5,
        "puntaje_privacidad": 5,
        "puntaje_soporte_ti": 5,
        "precio_mid_usd_M": (2.50 + 10.00) / 2,
        "notas": "Residencia de datos en Brasil Sur. Ideal LGPD.",
    },
    {
        "nombre": "AWS Bedrock",
        "categoria": "FRONTIER",
        "latencia_p95_ms": 3100,
        "sla_uptime": 99.95,
        "soporte_espanol": True,
        "n_certificaciones": 5,
        "puntaje_eco": 5,
        "puntaje_privacidad": 5,
        "puntaje_soporte_ti": 5,
        "precio_mid_usd_M": (3.00 + 15.00) / 2,
        "notas": "Multi-proveedor bajo un contrato. Región sa-east-1.",
    },
    {
        "nombre": "HuggingFace Endpoints",
        "categoria": "OPEN_WEIGHT",
        "latencia_p95_ms": 4500,
        "sla_uptime": 99.5,
        "soporte_espanol": True,
        "n_certificaciones": 2,
        "puntaje_eco": 5,
        "puntaje_privacidad": 4,
        "puntaje_soporte_ti": 2,
        "precio_mid_usd_M": (0.60 + 0.60) / 2,
        "notas": "Open-weight, sin lock-in, comunidad enorme.",
    },
    {
        "nombre": "On-Premise (Ollama/vLLM)",
        "categoria": "ON_PREMISE",
        "latencia_p95_ms": 800,
        "sla_uptime": 0.0,
        "soporte_espanol": True,
        "n_certificaciones": 0,
        "puntaje_eco": 3,
        "puntaje_privacidad": 5,
        "puntaje_soporte_ti": 1,
        "precio_mid_usd_M": 0.0,
        "notas": "Control total. CAPEX alto, requiere MLOps.",
    },
]

CASOS_USO_PESOS = {
    "banco_brasil": {
        "costo": 0.15, "cumplimiento": 0.35, "latencia": 0.05,
        "ecosistema": 0.03, "privacidad": 0.25, "soporte_ti": 0.15, "soporte_esp": 0.02,
    },
    "ecommerce_mx": {
        "costo": 0.35, "cumplimiento": 0.10, "latencia": 0.25,
        "ecosistema": 0.20, "privacidad": 0.05, "soporte_ti": 0.03, "soporte_esp": 0.02,
    },
    "startup_ar": {
        "costo": 0.25, "cumplimiento": 0.08, "latencia": 0.20,
        "ecosistema": 0.30, "privacidad": 0.05, "soporte_ti": 0.10, "soporte_esp": 0.02,
    },
    "hospital_cl": {
        "costo": 0.05, "cumplimiento": 0.30, "latencia": 0.08,
        "ecosistema": 0.01, "privacidad": 0.40, "soporte_ti": 0.15, "soporte_esp": 0.01,
    },
}

ESCENARIOS_TCO = {
    "api_publica": {
        "nombre": "API Pública (GPT-4o-mini / Gemini Flash)",
        "costo_inicial_usd": 10_000,
        "costo_api_por_millon_tokens": 0.30,
        "costo_infra_mensual": 150,
        "costo_personal_mensual": 500,
        "costo_mant_mensual": 100,
        "ahorro_mensual_base": 6_000,
        "prob_fallo": 0.10,
    },
    "plataforma_gestionada": {
        "nombre": "Plataforma Gestionada (Azure OpenAI / AWS Bedrock)",
        "costo_inicial_usd": 28_000,
        "costo_api_por_millon_tokens": 1.25,
        "costo_infra_mensual": 600,
        "costo_personal_mensual": 1_200,
        "costo_mant_mensual": 200,
        "ahorro_mensual_base": 9_700,
        "prob_fallo": 0.12,
    },
    "on_premise": {
        "nombre": "On-Premise (GPU A100 + Ollama/vLLM)",
        "costo_inicial_usd": 54_000,
        "costo_api_por_millon_tokens": 0.0,
        "costo_infra_mensual": 1_800,
        "costo_personal_mensual": 3_500,
        "costo_mant_mensual": 400,
        "ahorro_mensual_base": 14_500,
        "prob_fallo": 0.20,
    },
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _normalizar(valores: dict[str, float], invertir: bool = False) -> dict[str, float]:
    min_v = min(valores.values())
    max_v = max(valores.values())
    rango = max_v - min_v or 1.0
    if invertir:
        return {k: round(4.0 * (1 - (v - min_v) / rango) + 1.0, 2) for k, v in valores.items()}
    return {k: round(4.0 * (v - min_v) / rango + 1.0, 2) for k, v in valores.items()}


def _evaluar(pesos: dict[str, float]) -> list[dict]:
    latencias  = {p["nombre"]: p["latencia_p95_ms"] for p in PROVEEDORES_DB}
    precios    = {p["nombre"]: p["precio_mid_usd_M"] for p in PROVEEDORES_DB}
    certifs    = {p["nombre"]: float(p["n_certificaciones"]) for p in PROVEEDORES_DB}

    lat_norm   = _normalizar(latencias, invertir=True)
    precio_norm = _normalizar(precios, invertir=True)
    cert_norm  = _normalizar(certifs)

    resultados = []
    for p in PROVEEDORES_DB:
        n = p["nombre"]
        puntos = {
            "costo":       precio_norm[n],
            "cumplimiento": cert_norm[n],
            "latencia":    lat_norm[n],
            "ecosistema":  float(p["puntaje_eco"]),
            "privacidad":  float(p["puntaje_privacidad"]),
            "soporte_ti":  float(p["puntaje_soporte_ti"]),
            "soporte_esp": 5.0 if p["soporte_espanol"] else 1.0,
        }
        total = sum(puntos.get(k, 3.0) * v for k, v in pesos.items())
        resultados.append({
            "nombre": n,
            "categoria": p["categoria"],
            "puntaje_total": round(total, 3),
            "puntajes_detalle": puntos,
            "notas": p["notas"],
        })

    return sorted(resultados, key=lambda r: r["puntaje_total"], reverse=True)


# ─────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/proveedores/evaluar")
async def evaluar_proveedores(req: ProveedorRequest):
    """
    Ranking de proveedores LLM con pesos personalizados.
    Si se especifica caso_uso, se sobreescriben los pesos.
    """
    pesos = req.pesos
    if req.caso_uso:
        if req.caso_uso not in CASOS_USO_PESOS:
            raise HTTPException(
                400,
                detail=f"caso_uso desconocido. Válidos: {list(CASOS_USO_PESOS.keys())}",
            )
        pesos = CASOS_USO_PESOS[req.caso_uso]

    ranking = _evaluar(pesos)
    return {
        "pesos_usados": pesos,
        "ranking": ranking,
        "advertencia": (
            "Datos ilustrativos (oct-2026). Verifique precios con cada proveedor."
        ),
    }


@router.get("/proveedores/lista")
async def listar_proveedores():
    """Catálogo de proveedores con datos de referencia."""
    return {"proveedores": PROVEEDORES_DB}


@router.get("/proveedores/casos-uso")
async def listar_casos_uso():
    """Casos de uso predefinidos para el mercado LATAM."""
    return {"casos_uso": list(CASOS_USO_PESOS.keys()), "pesos": CASOS_USO_PESOS}


@router.post("/tco/calcular")
async def calcular_tco(req: TCORequest):
    """
    Calcula TCO, ROI y VAN para un escenario de despliegue LLM.
    """
    if req.escenario not in ESCENARIOS_TCO:
        raise HTTPException(400, detail=f"Escenario inválido. Usar: {list(ESCENARIOS_TCO.keys())}")

    e = ESCENARIOS_TCO[req.escenario]
    tasa_mensual = (1 + req.tasa_descuento_anual) ** (1 / 12) - 1

    # Tokens mensuales en millones
    tokens_M_mes = (req.tokens_dia * 30) / 1_000_000
    crecimiento = 0.02   # 2%/mes asumido

    costo_inicial = e["costo_inicial_usd"]
    costos_vp = 0.0
    beneficios_vp = 0.0
    tabla = []
    flujo_acum = -costo_inicial

    for mes in range(1, req.horizonte_meses + 1):
        factor_uso = (1 + crecimiento) ** (mes - 1)
        costo_op = (
            e["costo_api_por_millon_tokens"] * tokens_M_mes * factor_uso
            + e["costo_infra_mensual"] * factor_uso
            + e["costo_personal_mensual"]
            + e["costo_mant_mensual"]
        )
        beneficio = e["ahorro_mensual_base"] * (1 + crecimiento * (mes - 1) * 0.5)
        fd = (1 + tasa_mensual) ** mes
        costos_vp += costo_op / fd
        beneficios_vp += beneficio / fd
        flujo_acum += beneficio - costo_op
        tabla.append({
            "mes": mes,
            "costo_op": round(costo_op, 2),
            "beneficio": round(beneficio, 2),
            "flujo_acum": round(flujo_acum, 2),
        })

    tco = costo_inicial + costos_vp
    beneficio_neto = beneficios_vp - tco
    roi = (beneficio_neto / tco * 100) if tco > 0 else 0
    van = beneficios_vp - tco

    # Payback
    payback_meses = None
    prev = -costo_inicial
    for row in tabla:
        if prev < 0 <= row["flujo_acum"]:
            frac = -prev / (row["flujo_acum"] - prev)
            payback_meses = round(row["mes"] - 1 + frac, 1)
            break
        prev = row["flujo_acum"]

    roi_riesgo = roi * (1 - e["prob_fallo"]) - (e["prob_fallo"] * costo_inicial * 0.6 / tco * 100)

    return {
        "escenario": req.escenario,
        "nombre": e["nombre"],
        "parametros": {
            "tokens_dia": req.tokens_dia,
            "horizonte_meses": req.horizonte_meses,
            "tasa_descuento_anual_pct": req.tasa_descuento_anual * 100,
        },
        "resultados": {
            "costo_inicial_usd": round(costo_inicial, 2),
            "vp_costos_operativos_usd": round(costos_vp, 2),
            "tco_usd": round(tco, 2),
            "vp_beneficios_usd": round(beneficios_vp, 2),
            "beneficio_neto_usd": round(beneficio_neto, 2),
            "roi_bruto_pct": round(roi, 1),
            "roi_ajustado_riesgo_pct": round(roi_riesgo, 1),
            "van_usd": round(van, 2),
            "payback_meses": payback_meses,
            "prob_fallo": e["prob_fallo"],
        },
        "tabla_flujo": tabla,
    }


@router.post("/scaling/analizar")
async def analizar_scaling(req: ScalingRequest):
    """
    Recomienda estrategia de escalado y estima costo para una demanda dada.
    """
    # Capacidades de instancias base (tokens/seg)
    instancia_cpu  = {"vcpus": 4,  "ram_gb": 8,   "gpu_gb": 0,  "tps": 2_000,  "costo_h": 0.19}
    instancia_gpu  = {"vcpus": 8,  "ram_gb": 16,  "gpu_gb": 16, "tps": 12_000, "costo_h": 2.80}
    instancia_a100 = {"vcpus": 16, "ram_gb": 32,  "gpu_gb": 40, "tps": 35_000, "costo_h": 5.80}
    instancia_xl   = {"vcpus": 64, "ram_gb": 128, "gpu_gb": 80, "tps": 80_000, "costo_h": 12.50}

    def calcular_h(tipo, demanda) -> dict:
        n = math.ceil(demanda / tipo["tps"])
        costo = n * tipo["costo_h"]
        return {"instancias": n, "costo_hora_usd": round(costo, 2), "throughput_total": n * tipo["tps"]}

    horizontal = calcular_h(instancia_gpu, req.demanda_tps)
    vertical_ok = instancia_xl["tps"] >= req.demanda_tps
    vertical = {
        "instancias": 1 if vertical_ok else None,
        "costo_hora_usd": instancia_xl["costo_h"] if vertical_ok else None,
        "throughput_total": instancia_xl["tps"] if vertical_ok else None,
        "posible": vertical_ok,
    }

    recomendacion = "horizontal"
    razon = "Escalado horizontal más económico y con mayor disponibilidad."
    if not vertical_ok:
        recomendacion = "horizontal"
        razon = f"Demanda ({req.demanda_tps:,} TPS) supera la mayor instancia disponible ({instancia_xl['tps']:,} TPS). Solo escala horizontal."
    elif req.demanda_tps < 5_000:
        recomendacion = "vertical"
        razon = "Baja demanda: una sola instancia grande es más sencilla de operar."

    return {
        "demanda_tps": req.demanda_tps,
        "opciones": {
            "horizontal": horizontal,
            "vertical": vertical,
        },
        "recomendacion": recomendacion,
        "razon": razon,
        "kubernetes_manifest_hint": {
            "minReplicas": 1,
            "maxReplicas": horizontal["instancias"] * 2,
            "targetCPUUtilizationPct": 70,
            "keda_queue_threshold": 500,
        },
    }


@router.get("/patrones")
async def listar_patrones():
    """Catálogo de patrones arquitectónicos para soluciones LLM."""
    return {
        "patrones": [
            {
                "nombre": "API Gateway",
                "problema": "Los clientes no deben conocer la topología interna.",
                "solucion": "Punto único de entrada: auth, rate-limit, routing, logging.",
                "cuando_usar": "Siempre en producción con más de 1 servicio LLM.",
                "herramientas": ["Kong", "AWS API Gateway", "nginx", "Traefik"],
            },
            {
                "nombre": "Circuit Breaker",
                "problema": "Fallo en cascada cuando el LLM está lento o caído.",
                "solucion": "Abre el circuito tras N errores, rechaza requests rápido.",
                "cuando_usar": "Integraciones con LLMs externos de terceros.",
                "herramientas": ["Hystrix", "Resilience4j", "tenacity (Python)"],
            },
            {
                "nombre": "Sidecar",
                "problema": "Añadir logging/metrics/mTLS sin modificar el servicio principal.",
                "solucion": "Contenedor auxiliar en el mismo pod con acceso a red/volúmenes.",
                "cuando_usar": "Kubernetes con Istio/Envoy o Dapr.",
                "herramientas": ["Envoy", "Dapr", "Fluentd"],
            },
            {
                "nombre": "CQRS + Queue",
                "problema": "Inferencia LLM es lenta; respuestas sincrónicas degradan UX.",
                "solucion": "Producer devuelve job_id; consumer (worker) procesa async.",
                "cuando_usar": "Generación de documentos, resúmenes largos, batch.",
                "herramientas": ["Kafka", "RabbitMQ", "AWS SQS", "Redis Streams"],
            },
            {
                "nombre": "Cache Semántico",
                "problema": "Mismas preguntas frecuentes generan costo repetido.",
                "solucion": "Embeddings de queries → búsqueda por similitud en caché.",
                "cuando_usar": "FAQ bots, asistentes de soporte con queries repetitivas.",
                "herramientas": ["Redis + pgvector", "Qdrant", "GPTCache"],
            },
        ]
    }
