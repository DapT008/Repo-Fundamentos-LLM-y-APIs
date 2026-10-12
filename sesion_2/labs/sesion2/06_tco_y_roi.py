"""
Lab 06 – TCO y ROI para Implementaciones LLM
==============================================
Tema #3: Consideraciones de costos
Objetivo: Calcular el Costo Total de Propiedad (TCO) y el Retorno
         de Inversión (ROI) para tres escenarios de despliegue LLM.

NO requiere claves de API — cálculos financieros ilustrativos.

Ejecutar:
    cd labs/sesion2
    python 06_tco_y_roi.py
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# 1. MODELOS DE COSTOS
# ─────────────────────────────────────────────────────────────

@dataclass
class EscenarioDespliegue:
    """Represent un escenario completo de despliegue LLM."""
    nombre: str
    descripcion: str

    # ── Costos de adopción (one-time) ──────────────────────
    costo_capacitacion_usd: float       # Formación del equipo
    costo_integracion_usd: float        # Desarrollo / integración
    costo_licencias_setup_usd: float    # Licencias iniciales, setup
    costo_hardware_usd: float           # GPU / servidores si aplica

    # ── Costos operativos mensuales ────────────────────────
    costo_api_mensual_usd: float        # Tokens consumidos
    costo_infra_mensual_usd: float      # Cómputo, red, almacenamiento
    costo_personal_mensual_usd: float   # Horas/mes dedicadas al sistema
    costo_mantenimiento_mensual_usd: float  # Actualizaciones, soporte

    # ── Beneficios estimados ───────────────────────────────
    ahorro_horas_hombre_mensual: float  # Horas ahorradas/mes (en USD)
    ingresos_adicionales_mensual: float # Nuevos ingresos atribuibles
    reduccion_errores_mensual: float    # Valor de errores evitados

    # ── Parámetros del análisis ────────────────────────────
    horizonte_meses: int = 24
    tasa_descuento_anual: float = 0.10   # 10% anual → 0.83%/mes
    crecimiento_uso_mensual: float = 0.02  # 2% más tokens/mes

    # ── Riesgo ────────────────────────────────────────────
    prob_fallo_adopcion: float = 0.15   # Probabilidad de fracaso
    impacto_fallo_usd: float = 0.0      # Si 0, se calcula auto


@dataclass
class ResultadoTCO:
    escenario: str
    costo_inicial_total: float
    costos_operativos_vp: float   # Valor presente
    beneficios_vp: float
    tco: float
    beneficio_neto: float
    roi_pct: float
    payback_meses: Optional[float]
    van: float                    # Valor Actual Neto
    roi_ajustado_riesgo: float
    tabla_mensual: list[dict]


# ─────────────────────────────────────────────────────────────
# 2. ENGINE DE CÁLCULO
# ─────────────────────────────────────────────────────────────

def calcular_tco(e: EscenarioDespliegue) -> ResultadoTCO:
    tasa_mensual = (1 + e.tasa_descuento_anual) ** (1 / 12) - 1

    costo_inicial = (
        e.costo_capacitacion_usd
        + e.costo_integracion_usd
        + e.costo_licencias_setup_usd
        + e.costo_hardware_usd
    )

    costos_vp = 0.0
    beneficios_vp = 0.0
    tabla = []
    flujo_acumulado = -costo_inicial
    payback_meses: Optional[float] = None
    flujo_acum_anterior = flujo_acumulado

    for mes in range(1, e.horizonte_meses + 1):
        # Costos crecen con el uso
        factor_uso = (1 + e.crecimiento_uso_mensual) ** (mes - 1)
        costo_op = (
            e.costo_api_mensual_usd * factor_uso
            + e.costo_infra_mensual_usd * factor_uso
            + e.costo_personal_mensual_usd
            + e.costo_mantenimiento_mensual_usd
        )
        beneficio_mes = (
            e.ahorro_horas_hombre_mensual
            + e.ingresos_adicionales_mensual * factor_uso
            + e.reduccion_errores_mensual
        )
        factor_desc = (1 + tasa_mensual) ** mes
        costos_vp  += costo_op / factor_desc
        beneficios_vp += beneficio_mes / factor_desc

        flujo_acum_anterior = flujo_acumulado
        flujo_acumulado += beneficio_mes - costo_op

        # Payback: interpolación lineal
        if payback_meses is None and flujo_acumulado >= 0 > flujo_acum_anterior:
            fraccion = -flujo_acum_anterior / (flujo_acumulado - flujo_acum_anterior)
            payback_meses = mes - 1 + fraccion

        tabla.append({
            "mes": mes,
            "costo_op": round(costo_op, 0),
            "beneficio": round(beneficio_mes, 0),
            "flujo_neto": round(beneficio_mes - costo_op, 0),
            "flujo_acum": round(flujo_acumulado, 0),
        })

    tco = costo_inicial + costos_vp
    beneficio_neto = beneficios_vp - tco
    roi = (beneficio_neto / tco * 100) if tco > 0 else 0
    van = beneficios_vp - costo_inicial - costos_vp

    # Riesgo: valor esperado ajustado
    impacto = e.impacto_fallo_usd if e.impacto_fallo_usd > 0 else costo_inicial * 0.6
    perdida_esperada = e.prob_fallo_adopcion * impacto
    roi_ajustado = roi * (1 - e.prob_fallo_adopcion) - (perdida_esperada / tco * 100)

    return ResultadoTCO(
        escenario=e.nombre,
        costo_inicial_total=round(costo_inicial, 0),
        costos_operativos_vp=round(costos_vp, 0),
        beneficios_vp=round(beneficios_vp, 0),
        tco=round(tco, 0),
        beneficio_neto=round(beneficio_neto, 0),
        roi_pct=round(roi, 1),
        payback_meses=round(payback_meses, 1) if payback_meses else None,
        van=round(van, 0),
        roi_ajustado_riesgo=round(roi_ajustado, 1),
        tabla_mensual=tabla,
    )


# ─────────────────────────────────────────────────────────────
# 3. ESCENARIOS REPRESENTATIVOS (empresa mediana LATAM)
# ─────────────────────────────────────────────────────────────

def escenarios_latam() -> list[EscenarioDespliegue]:
    """
    Empresa mediana: 200 empleados, procesa ~1M tokens/día.
    Dólares estadounidenses. Horizonte de análisis: 24 meses.
    """
    return [
        # ── ESCENARIO A: SaaS puro con GPT-4o-mini ────────
        EscenarioDespliegue(
            nombre="A – API Pública (GPT-4o-mini)",
            descripcion=(
                "Consumo directo vía API de OpenAI. Mínima inversión inicial, "
                "máxima flexibilidad. Sin control de datos. Costo variable."
            ),
            costo_capacitacion_usd=2_000,
            costo_integracion_usd=8_000,
            costo_licencias_setup_usd=0,
            costo_hardware_usd=0,
            # 1M tokens/día × 30 días × ($0.15 in + $0.60 out)/2 /1M ≈ $113/mes
            costo_api_mensual_usd=113,
            costo_infra_mensual_usd=150,   # Solo servidor de aplicación
            costo_personal_mensual_usd=500, # 0.25 FTE DevOps
            costo_mantenimiento_mensual_usd=100,
            ahorro_horas_hombre_mensual=4_500,  # 150 h × $30 analistas
            ingresos_adicionales_mensual=1_000,
            reduccion_errores_mensual=500,
            horizonte_meses=24,
            tasa_descuento_anual=0.10,
            crecimiento_uso_mensual=0.03,
            prob_fallo_adopcion=0.10,
        ),

        # ── ESCENARIO B: Plataforma Gestionada (Azure OpenAI) ──
        EscenarioDespliegue(
            nombre="B – Plataforma Gestionada (Azure OpenAI)",
            descripcion=(
                "Azure OpenAI con reserva de capacidad PTU (Provisioned Throughput Units). "
                "Mayor control, cumplimiento LGPD, latencia predecible. Costo mixto fijo+variable."
            ),
            costo_capacitacion_usd=5_000,
            costo_integracion_usd=20_000,
            costo_licencias_setup_usd=3_000,   # Setup Azure Landing Zone
            costo_hardware_usd=0,
            costo_api_mensual_usd=400,          # PTU + overage
            costo_infra_mensual_usd=600,        # VNet, Key Vault, Monitor
            costo_personal_mensual_usd=1_200,   # 0.5 FTE CloudOps
            costo_mantenimiento_mensual_usd=200,
            ahorro_horas_hombre_mensual=6_000,
            ingresos_adicionales_mensual=2_500,
            reduccion_errores_mensual=1_200,
            horizonte_meses=24,
            tasa_descuento_anual=0.10,
            crecimiento_uso_mensual=0.03,
            prob_fallo_adopcion=0.12,
        ),

        # ── ESCENARIO C: On-Premise con GPU ──────────────
        EscenarioDespliegue(
            nombre="C – On-Premise (GPU + Ollama/vLLM)",
            descripcion=(
                "Servidor GPU NVIDIA A100 (80 GB) en datacenter propio. "
                "Control total, cero costo por token, alta privacidad. CAPEX alto."
            ),
            costo_capacitacion_usd=12_000,
            costo_integracion_usd=15_000,
            costo_licencias_setup_usd=2_000,    # vLLM Enterprise opcional
            costo_hardware_usd=25_000,          # 1× A100 server (estimado)
            costo_api_mensual_usd=0,            # Sin costo por token
            costo_infra_mensual_usd=1_800,      # Electricidad, red, rack
            costo_personal_mensual_usd=3_500,   # 1.5 FTE MLOps
            costo_mantenimiento_mensual_usd=400,
            ahorro_horas_hombre_mensual=9_000,
            ingresos_adicionales_mensual=3_500,
            reduccion_errores_mensual=2_000,
            horizonte_meses=24,
            tasa_descuento_anual=0.10,
            crecimiento_uso_mensual=0.01,       # Limitado por hardware fijo
            prob_fallo_adopcion=0.20,           # Mayor complejidad operativa
            impacto_fallo_usd=30_000,           # Hardware no recuperable
        ),
    ]


# ─────────────────────────────────────────────────────────────
# 4. ANÁLISIS DE SENSIBILIDAD
# ─────────────────────────────────────────────────────────────

def analisis_sensibilidad(e: EscenarioDespliegue) -> None:
    """Muestra cómo cambia el ROI al variar el crecimiento de uso."""
    print(f"\n  Análisis de sensibilidad – {e.nombre}")
    print(f"  {'Crecimiento uso/mes':<25} {'ROI %':>8}  {'Payback (meses)':>16}")
    print("  " + "-" * 55)
    for tasa in [0.0, 0.01, 0.02, 0.03, 0.05, 0.08]:
        e2 = EscenarioDespliegue(**{**e.__dict__, "crecimiento_uso_mensual": tasa})
        r  = calcular_tco(e2)
        pb = f"{r.payback_meses:.1f}" if r.payback_meses else "N/A (>24m)"
        print(f"  {tasa:.0%} mensual             {r.roi_pct:>8.1f}%  {pb:>16}")


# ─────────────────────────────────────────────────────────────
# 5. VISUALIZACIÓN ASCII DE FLUJO ACUMULADO
# ─────────────────────────────────────────────────────────────

def grafico_flujo_ascii(resultado: ResultadoTCO, meses_mostrar: int = 24):
    tabla = resultado.tabla_mensual[:meses_mostrar]
    valores = [r["flujo_acum"] for r in tabla]
    min_v = min(valores)
    max_v = max(valores)
    rango = max_v - min_v or 1
    ancho = 40

    print(f"\n  Flujo acumulado neto – {resultado.escenario}")
    print(f"  ({'negativo':>20}  |  positivo)")
    print("  " + "-" * (ancho + 10))
    for r in tabla[::3]:   # cada 3 meses para no saturar
        v = r["flujo_acum"]
        norm = (v - min_v) / rango   # 0-1
        pos  = int(norm * ancho)
        cero = int((-min_v / rango) * ancho)
        linea = [" "] * (ancho + 1)
        linea[cero] = "|"
        if pos != cero:
            signo = "█" if v >= 0 else "▒"
            lo, hi = (min(pos, cero), max(pos, cero))
            for i in range(lo, hi + 1):
                if i != cero:
                    linea[i] = signo
        print(f"  m{r['mes']:>2} {''.join(linea)}  ${v:>9,.0f}")
    print("  " + "-" * (ancho + 10))
    if resultado.payback_meses:
        print(f"  ► Punto de equilibrio: mes {resultado.payback_meses:.1f}")


# ─────────────────────────────────────────────────────────────
# 6. RESUMEN EJECUTIVO
# ─────────────────────────────────────────────────────────────

def imprimir_resumen(resultados: list[ResultadoTCO]):
    print("\n")
    print("=" * 80)
    print("  RESUMEN EJECUTIVO – COMPARATIVA TCO/ROI (Horizonte 24 meses)")
    print("=" * 80)
    print(f"  {'Escenario':<40} {'TCO':>10} {'Beneficio N.':>14} {'ROI':>8}  {'Payback':>10}  {'VAN':>10}")
    print("  " + "-" * 98)
    for r in resultados:
        pb = f"{r.payback_meses:.1f}m" if r.payback_meses else ">24m"
        print(
            f"  {r.escenario:<40} "
            f"${r.tco:>9,.0f} "
            f"${r.beneficio_neto:>13,.0f} "
            f"{r.roi_pct:>7.1f}% "
            f"{pb:>10}  "
            f"${r.van:>9,.0f}"
        )
    print("  " + "-" * 98)

    # Ganador por dimensión
    mejor_roi = max(resultados, key=lambda r: r.roi_pct)
    menor_riesgo = max(resultados, key=lambda r: r.roi_ajustado_riesgo)
    paybacks = [r for r in resultados if r.payback_meses]
    mas_rapido = min(paybacks, key=lambda r: r.payback_meses) if paybacks else None

    print()
    print(f"  ★ Mejor ROI bruto:              {mejor_roi.escenario} ({mejor_roi.roi_pct:.1f}%)")
    print(f"  ★ Mejor ROI ajustado por riesgo: {menor_riesgo.escenario} ({menor_riesgo.roi_ajustado_riesgo:.1f}%)")
    if mas_rapido:
        print(f"  ★ Recuperación más rápida:      {mas_rapido.escenario} ({mas_rapido.payback_meses:.1f} meses)")


# ─────────────────────────────────────────────────────────────
# 7. MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  LAB 06 – TCO y ROI PARA IMPLEMENTACIONES LLM")
    print("  Curso: Fundamentos de Arquitectura LLM | Sesión 2 – Tema 3")
    print("=" * 80)

    print("""
  MARCO TEÓRICO
  ─────────────────────────────────────────────────────────────
  TCO (Total Cost of Ownership) = Costo Inicial + VP(Costos Operativos)
  ROI = (Beneficio Neto / TCO) × 100
  VAN = VP(Beneficios) − TCO
  Payback = Meses hasta que flujo acumulado ≥ 0

  Para LLMs, los costos se clasifican en:
    • CAPEX: hardware, licencias perpetuas, integraciones iniciales
    • OPEX:  API tokens, cómputo cloud, personal, mantenimiento

  En LATAM, la tasa de descuento sugerida oscila entre 10-15% anual
  debido a mayor incertidumbre macroeconómica y tasas de referencia locales.
    """)

    escenarios = escenarios_latam()
    resultados = [calcular_tco(e) for e in escenarios]

    imprimir_resumen(resultados)

    # Detalle de cada escenario
    for r, e in zip(resultados, escenarios):
        print(f"\n  {'─'*70}")
        print(f"  {r.escenario}")
        print(f"  {e.descripcion}")
        print(f"  {'─'*70}")
        print(f"  Costo inicial (CAPEX):      ${r.costo_inicial_total:>10,.0f}")
        print(f"  VP Costos operativos:        ${r.costos_operativos_vp:>10,.0f}")
        print(f"  TCO (24 meses):              ${r.tco:>10,.0f}")
        print(f"  VP Beneficios:               ${r.beneficios_vp:>10,.0f}")
        print(f"  Beneficio neto:              ${r.beneficio_neto:>10,.0f}")
        print(f"  ROI bruto:                   {r.roi_pct:>10.1f}%")
        print(f"  ROI ajustado por riesgo:     {r.roi_ajustado_riesgo:>10.1f}%")
        print(f"  VAN:                         ${r.van:>10,.0f}")
        pb_txt = f"{r.payback_meses:.1f} meses" if r.payback_meses else "> 24 meses"
        print(f"  Payback:                     {pb_txt:>10}")
        grafico_flujo_ascii(r)

    # Análisis de sensibilidad para el escenario A
    analisis_sensibilidad(escenarios[0])

    print("""
  ─────────────────────────────────────────────────────────────
  LECCIONES APRENDIDAS
  ─────────────────────────────────────────────────────────────
  1. El costo por token NO es el TCO. El personal es frecuentemente
     el mayor costo oculto en implementaciones LLM.

  2. On-Premise domina en ROI bruto SOLO cuando el volumen es alto
     (>10 M tokens/día). Por debajo de eso, la API es más económica.

  3. El riesgo de fallo de adopción (15-20%) reduce significativamente
     el ROI ajustado. Invierta en gestión del cambio.

  4. Payback <12 meses → proyecto viable. Entre 12-24 → requiere
     justificación estratégica adicional.

  5. VAN positivo en horizonte 24 m es condición mínima para aprobar
     el proyecto en comité de inversión.
  ─────────────────────────────────────────────────────────────
    """)


if __name__ == "__main__":
    main()
