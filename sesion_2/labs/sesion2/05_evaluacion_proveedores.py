"""
Lab 05 – Evaluación de Proveedores LLM
========================================
Tema #3: Consideraciones de costos
Objetivo: Construir un framework sistemático para comparar proveedores
         (OpenAI, Anthropic, Google, Azure, HuggingFace, AWS Bedrock).

NO requiere claves de API — todos los datos son referenciales/didácticos.

Ejecutar:
    cd labs/sesion2
    python 05_evaluacion_proveedores.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Literal
import math

# ─────────────────────────────────────────────────────────────
# 1. MODELO DE DATOS: Proveedor y sus dimensiones de evaluación
# ─────────────────────────────────────────────────────────────

Categoria = Literal["FRONTIER", "MIDSIZED", "OPEN_WEIGHT", "ON_PREMISE"]


@dataclass
class PrecioModelo:
    """Precio de un modelo específico (por millón de tokens)."""
    nombre: str
    entrada_usd: float          # USD / M tokens input
    salida_usd: float           # USD / M tokens output
    contexto_max_k: int         # ventana de contexto en miles de tokens
    disponible_latam: bool = True
    notas: str = ""


@dataclass
class Proveedor:
    nombre: str
    categoria: Categoria
    region_datos: str           # Dónde se procesan los datos (GDPR/LGPD)
    sla_uptime: float           # % uptime garantizado en SLA
    cumplimiento: list[str]     # SOC2, ISO27001, HIPAA, etc.
    soporte_espanol: bool
    latencia_p95_ms: int        # P95 latencia típica
    modelos: list[PrecioModelo] = field(default_factory=list)
    # Puntuaciones 1-5 para criterios cualitativos
    puntaje_doc: int = 3         # Calidad de documentación
    puntaje_eco: int = 3         # Ecosistema / integraciones
    puntaje_privacidad: int = 3  # Opciones de privacidad/datos
    puntaje_soporte_ti: int = 3  # Soporte técnico
    notas: str = ""


# ─────────────────────────────────────────────────────────────
# 2. CATÁLOGO DE PROVEEDORES (datos ilustrativos, oct-2026)
# ─────────────────────────────────────────────────────────────

def catalogo_proveedores() -> list[Proveedor]:
    return [
        Proveedor(
            nombre="OpenAI",
            categoria="FRONTIER",
            region_datos="EE.UU. (Azure global)",
            sla_uptime=99.9,
            cumplimiento=["SOC2 Type II", "ISO 27001", "HIPAA BAA"],
            soporte_espanol=False,
            latencia_p95_ms=3500,
            puntaje_doc=5, puntaje_eco=5, puntaje_privacidad=3, puntaje_soporte_ti=3,
            modelos=[
                PrecioModelo("gpt-4o",        2.50, 10.00, 128),
                PrecioModelo("gpt-4o-mini",   0.15,  0.60, 128),
                PrecioModelo("o3",           10.00, 40.00,  32, notas="Razonamiento extendido"),
            ],
        ),
        Proveedor(
            nombre="Anthropic",
            categoria="FRONTIER",
            region_datos="EE.UU. / AWS",
            sla_uptime=99.9,
            cumplimiento=["SOC2 Type II", "HIPAA BAA"],
            soporte_espanol=False,
            latencia_p95_ms=3200,
            puntaje_doc=4, puntaje_eco=4, puntaje_privacidad=4, puntaje_soporte_ti=3,
            modelos=[
                PrecioModelo("claude-opus-5-5",    15.00, 75.00, 200),
                PrecioModelo("claude-sonnet-4-6",   3.00, 15.00, 200),
                PrecioModelo("claude-haiku-4-5",    1.00,  5.00, 200),
            ],
        ),
        Proveedor(
            nombre="Google (Gemini)",
            categoria="FRONTIER",
            region_datos="Global (multi-región elegible UE)",
            sla_uptime=99.95,
            cumplimiento=["SOC2", "ISO 27001", "GDPR", "FedRAMP High"],
            soporte_espanol=True,
            latencia_p95_ms=2800,
            puntaje_doc=4, puntaje_eco=5, puntaje_privacidad=4, puntaje_soporte_ti=4,
            modelos=[
                PrecioModelo("gemini-2.5-pro",   1.25, 10.00, 1000),
                PrecioModelo("gemini-2.5-flash", 0.30,  2.50,  500),
            ],
            notas="Mejor integración con GCP/BigQuery. Soporte en español disponible.",
        ),
        Proveedor(
            nombre="Azure OpenAI Service",
            categoria="FRONTIER",
            region_datos="Región elegida (Brasil, EE.UU., EU)",
            sla_uptime=99.9,
            cumplimiento=["SOC2", "ISO 27001", "HIPAA", "PCI DSS", "LGPD"],
            soporte_espanol=True,
            latencia_p95_ms=3800,
            puntaje_doc=4, puntaje_eco=5, puntaje_privacidad=5, puntaje_soporte_ti=5,
            modelos=[
                PrecioModelo("gpt-4o (Azure)",     2.50, 10.00, 128, notas="Datos en región elegida"),
                PrecioModelo("gpt-4o-mini (Azure)", 0.165, 0.66, 128),
            ],
            notas="Permite residencia de datos en Brasil Sur. Ideal cumplimiento LGPD.",
        ),
        Proveedor(
            nombre="AWS Bedrock",
            categoria="FRONTIER",
            region_datos="us-east-1 / sa-east-1 (São Paulo)",
            sla_uptime=99.95,
            cumplimiento=["SOC2", "ISO 27001", "HIPAA", "PCI DSS", "LGPD"],
            soporte_espanol=True,
            latencia_p95_ms=3100,
            puntaje_doc=4, puntaje_eco=5, puntaje_privacidad=5, puntaje_soporte_ti=5,
            modelos=[
                PrecioModelo("Claude Sonnet (Bedrock)", 3.00, 15.00, 200),
                PrecioModelo("Llama 3.1 70B (Bedrock)", 0.72,  0.72, 128),
                PrecioModelo("Titan Text Lite",          0.30,  0.40,  32),
            ],
            notas="Región sa-east-1 disponible. Multi-proveedor en un solo contrato AWS.",
        ),
        Proveedor(
            nombre="HuggingFace Inference Endpoints",
            categoria="OPEN_WEIGHT",
            region_datos="Multi-región (EU, EE.UU.)",
            sla_uptime=99.5,
            cumplimiento=["SOC2 Type I", "GDPR"],
            soporte_espanol=True,
            latencia_p95_ms=4500,
            puntaje_doc=5, puntaje_eco=5, puntaje_privacidad=4, puntaje_soporte_ti=2,
            modelos=[
                PrecioModelo("Llama 3.1 8B Instruct",  0.60, 0.60, 128),
                PrecioModelo("Mistral 7B Instruct v0.3", 0.40, 0.40, 32),
                PrecioModelo("Qwen2.5 72B Instruct",    2.80, 2.80, 128),
            ],
            notas="Modelos open-weight. Se puede descargar y hospedar on-premise.",
        ),
        Proveedor(
            nombre="On-Premise (Ollama/vLLM)",
            categoria="ON_PREMISE",
            region_datos="Instalaciones propias (total control)",
            sla_uptime=0.0,   # Depende de la infraestructura propia
            cumplimiento=["Según implementación interna"],
            soporte_espanol=True,
            latencia_p95_ms=800,   # GPU local ~A100
            puntaje_doc=3, puntaje_eco=3, puntaje_privacidad=5, puntaje_soporte_ti=1,
            modelos=[
                PrecioModelo("Llama 3.1 8B  (GPU local)", 0.00, 0.00, 128,
                             notas="Costo fijo infraestructura ≈ $2–6/hora GPU A100"),
                PrecioModelo("Mistral 7B (GPU local)",     0.00, 0.00, 32,
                             notas="Sin costo por token, latencia muy baja"),
            ],
            notas="Control total de datos. Requiere equipo de MLOps. CAPEX alto.",
        ),
    ]


# ─────────────────────────────────────────────────────────────
# 3. MATRIZ DE EVALUACIÓN PONDERADA
# ─────────────────────────────────────────────────────────────

@dataclass
class CriterioPeso:
    nombre: str
    peso: float   # suma debe ser 1.0
    descripcion: str


def criterios_latam() -> list[CriterioPeso]:
    """
    Pesos ajustados para el contexto LATAM con énfasis en:
    - cumplimiento (LGPD Brasil, Ley de Datos Chile, LFPDPPP México)
    - soporte en español
    - costo (presupuestos más ajustados que EE.UU./EU)
    """
    return [
        CriterioPeso("Costo / token",      0.25, "Precio entrada+salida por 1 M tokens"),
        CriterioPeso("Cumplimiento",        0.20, "Certificaciones y residencia de datos"),
        CriterioPeso("Latencia P95",        0.15, "Experiencia de usuario en tiempo real"),
        CriterioPeso("Ecosistema",          0.15, "Integraciones, SDKs, comunidad"),
        CriterioPeso("Privacidad",          0.10, "Control sobre datos del cliente"),
        CriterioPeso("Soporte técnico",     0.10, "Disponibilidad y calidad de soporte"),
        CriterioPeso("Soporte en español",  0.05, "Documentación y atención en español"),
    ]


def normalizar_costo(proveedores: list[Proveedor]) -> dict[str, float]:
    """Invierte la escala de costo: menor costo → mayor puntuación."""
    # Precio promedio del modelo mid-tier de cada proveedor
    def precio_mid(p: Proveedor) -> float:
        if not p.modelos:
            return 99.0
        precios = [(m.entrada_usd + m.salida_usd) / 2 for m in p.modelos]
        # Usar la mediana
        precios_sorted = sorted(precios)
        n = len(precios_sorted)
        return precios_sorted[n // 2]

    costos = {p.nombre: precio_mid(p) for p in proveedores}
    max_c = max(costos.values()) or 1
    # Escala invertida: 0 → 5 (menor costo = 5)
    return {k: round(5 * (1 - v / max_c) + 0.5, 2) for k, v in costos.items()}


def normalizar_latencia(proveedores: list[Proveedor]) -> dict[str, float]:
    max_lat = max(p.latencia_p95_ms for p in proveedores)
    return {p.nombre: round(5 * (1 - p.latencia_p95_ms / max_lat) + 0.5, 2)
            for p in proveedores}


def puntaje_cumplimiento(p: Proveedor) -> float:
    """Puntaje basado en nº de certificaciones relevantes."""
    puntos = len(p.cumplimiento)
    return min(5.0, round(1 + puntos * 0.7, 1))


def evaluar_proveedores(
    proveedores: list[Proveedor],
    criterios: list[CriterioPeso],
) -> list[dict]:
    costos_norm = normalizar_costo(proveedores)
    lat_norm    = normalizar_latencia(proveedores)

    resultados = []
    for p in proveedores:
        puntajes = {
            "Costo / token":     costos_norm[p.nombre],
            "Cumplimiento":      puntaje_cumplimiento(p),
            "Latencia P95":      lat_norm[p.nombre],
            "Ecosistema":        float(p.puntaje_eco),
            "Privacidad":        float(p.puntaje_privacidad),
            "Soporte técnico":   float(p.puntaje_soporte_ti),
            "Soporte en español": 5.0 if p.soporte_espanol else 1.0,
        }
        ponderado = sum(
            puntajes[c.nombre] * c.peso
            for c in criterios
            if c.nombre in puntajes
        )
        resultados.append({
            "proveedor": p.nombre,
            "categoria": p.categoria,
            "puntaje_total": round(ponderado, 3),
            "desglose": puntajes,
            "notas": p.notas,
        })

    return sorted(resultados, key=lambda r: r["puntaje_total"], reverse=True)


# ─────────────────────────────────────────────────────────────
# 4. ANÁLISIS DE CASOS DE USO LATAM
# ─────────────────────────────────────────────────────────────

CASOS_USO = {
    "Banco (regulado, Brasil)": {
        "criterios_ajustados": {
            "Cumplimiento":  0.35,    # LGPD, Bacen resolución 4.966
            "Privacidad":    0.25,
            "Costo / token": 0.15,
            "Soporte técnico": 0.15,
            "Latencia P95":  0.05,
            "Ecosistema":    0.03,
            "Soporte en español": 0.02,
        },
        "proveedores_recomendados": ["Azure OpenAI Service", "AWS Bedrock"],
        "razon": "Residencia de datos en BR-Sul, cumplimiento LGPD, SLA empresarial.",
    },
    "E-commerce (costo-eficiencia, MX)": {
        "criterios_ajustados": {
            "Costo / token": 0.35,
            "Latencia P95":  0.25,
            "Ecosistema":    0.20,
            "Cumplimiento":  0.10,
            "Privacidad":    0.05,
            "Soporte técnico": 0.03,
            "Soporte en español": 0.02,
        },
        "proveedores_recomendados": ["Google (Gemini)", "OpenAI"],
        "razon": "Alta concurrencia, costo por request crítico, latencia visible al usuario.",
    },
    "Startup IA (agilidad, AR)": {
        "criterios_ajustados": {
            "Ecosistema":    0.30,
            "Costo / token": 0.25,
            "Latencia P95":  0.20,
            "Soporte técnico": 0.10,
            "Cumplimiento":  0.08,
            "Privacidad":    0.05,
            "Soporte en español": 0.02,
        },
        "proveedores_recomendados": ["HuggingFace Inference Endpoints", "Anthropic"],
        "razon": "Acceso a modelos open-weight, comunidad activa, sin lock-in inicial.",
    },
    "Hospital (datos sensibles, CL)": {
        "criterios_ajustados": {
            "Privacidad":    0.40,
            "Cumplimiento":  0.30,
            "Soporte técnico": 0.15,
            "Latencia P95":  0.08,
            "Costo / token": 0.05,
            "Ecosistema":    0.01,
            "Soporte en español": 0.01,
        },
        "proveedores_recomendados": ["On-Premise (Ollama/vLLM)", "Azure OpenAI Service"],
        "razon": "Datos clínicos no pueden salir del recinto. On-premise con GPU local.",
    },
}


# ─────────────────────────────────────────────────────────────
# 5. IMPRESIÓN DE RESULTADOS
# ─────────────────────────────────────────────────────────────

COL = 26   # ancho columna nombre


def separador(char="-", ancho=80):
    print(char * ancho)


def imprimir_ranking(resultados: list[dict], titulo: str = "Ranking General LATAM"):
    print()
    separador("═")
    print(f"  {titulo}")
    separador("═")
    print(f"  {'#':>3}  {'Proveedor':<{COL}} {'Puntaje':>8}  {'Categoría':<15}")
    separador()
    for i, r in enumerate(resultados, 1):
        bar = "█" * int(r["puntaje_total"] * 4)
        print(f"  {i:>3}. {r['proveedor']:<{COL}} {r['puntaje_total']:>6.3f}  {r['categoria']:<15}  {bar}")
    separador()


def imprimir_desglose(resultado: dict):
    print(f"\n  Desglose: {resultado['proveedor']}")
    separador("-", 60)
    for criterio, puntos in resultado["desglose"].items():
        barra = "▓" * int(puntos)
        print(f"  {criterio:<25} {puntos:>4.1f}/5  {barra}")
    if resultado["notas"]:
        print(f"\n  ℹ  {resultado['notas']}")


def imprimir_casos_uso():
    print("\n")
    separador("═")
    print("  ANÁLISIS POR CASO DE USO LATAM")
    separador("═")
    for caso, datos in CASOS_USO.items():
        print(f"\n  ► {caso}")
        print(f"  Recomendados: {', '.join(datos['proveedores_recomendados'])}")
        print(f"  Razón:        {datos['razon']}")


# ─────────────────────────────────────────────────────────────
# 6. EXPORTAR RESULTADOS A JSON
# ─────────────────────────────────────────────────────────────

def exportar_json(resultados: list[dict], ruta: str = "resultados_proveedores.json"):
    payload = {
        "contexto": "Evaluación ilustrativa oct-2026 para mercado LATAM",
        "advertencia": "Precios y puntajes son REFERENCIALES. Verifique con proveedores.",
        "ranking": resultados,
        "casos_uso": CASOS_USO,
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\n  ✅  Resultados exportados → {ruta}")


# ─────────────────────────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  LAB 05 – EVALUACIÓN DE PROVEEDORES LLM PARA LATAM")
    print("  Curso: Fundamentos de Arquitectura LLM | Sesión 2 – Tema 3")
    print("=" * 80)

    print("""
  MARCO CONCEPTUAL: Estrategias de evaluación de proveedores
  ─────────────────────────────────────────────────────────────
  Evaluar un proveedor LLM no es solo comparar precios/token.
  Se trata de un análisis multidimensional que incluye:

    1. Criterios técnicos:  latencia, disponibilidad, contexto máximo
    2. Criterios legales:   certificaciones, residencia de datos
    3. Criterios económicos: precio/token, compromisos de volumen
    4. Criterios estratégicos: ecosistema, lock-in, roadmap del modelo

  En LATAM, el cumplimiento normativo (LGPD, Ley 25.326, LFPDPPP)
  y la soberanía de datos pesan más que en mercados anglófonos.
    """)

    proveedores = catalogo_proveedores()
    criterios   = criterios_latam()

    print("  Criterios y pesos utilizados:")
    separador()
    for c in criterios:
        barra = "█" * int(c.peso * 100 // 5)
        print(f"  {c.nombre:<25} {c.peso:.0%}  {barra}")
    separador()

    resultados = evaluar_proveedores(proveedores, criterios)
    imprimir_ranking(resultados, "Ranking General LATAM (criterios balanceados)")

    print("\n  TOP-3 Desglose detallado:")
    for r in resultados[:3]:
        imprimir_desglose(r)

    imprimir_casos_uso()

    exportar_json(resultados)

    print("""
  ─────────────────────────────────────────────────────────────
  CONCLUSIONES CLAVE:
  ─────────────────────────────────────────────────────────────
  • No existe un "mejor proveedor" universal — el ganador depende
    del perfil de riesgo y requisitos del proyecto.
  • Azure OpenAI y AWS Bedrock lideran en cumplimiento LATAM
    gracias a regiones en Brasil (sa-east-1 / br-south-1).
  • On-Premise gana en privacidad absoluta pero requiere equipo
    de MLOps y CAPEX significativo.
  • Para startups: HuggingFace + modelo open-weight evita lock-in
    y permite migrar a on-premise cuando el volumen lo justifique.
  ─────────────────────────────────────────────────────────────
    """)


if __name__ == "__main__":
    main()
