"""
Lab 08 – Escalabilidad y Orquestación de LLMs
===============================================
Tema #4: Patrones y escalabilidad
Objetivo: Comparar escalabilidad horizontal vs vertical,
         simular auto-scaling basado en métricas, y analizar
         manifiestos de Kubernetes (HPA) y Docker Swarm.

NO requiere Kubernetes instalado — simulación pura en Python.

Ejecutar:
    cd labs/sesion2
    python 08_escalabilidad_y_orquestacion.py
"""

from __future__ import annotations

import time
import math
import random
import threading
from dataclasses import dataclass, field
from collections import deque
from typing import Optional

# ─────────────────────────────────────────────────────────────
# 1. MODELOS DE RECURSOS
# ─────────────────────────────────────────────────────────────

@dataclass
class InstanciaLLM:
    """Una instancia de servidor LLM (pod, contenedor o VM)."""
    id: int
    vcpus: int
    ram_gb: float
    gpu_vram_gb: float
    tokens_por_segundo: int     # Throughput de la instancia

    @property
    def costo_hora_usd(self) -> float:
        """Estimado de costo basado en specs (cloud, zona US-East)."""
        return round(self.vcpus * 0.048 + self.gpu_vram_gb * 0.12, 3)

    @property
    def etiqueta(self) -> str:
        return f"inst-{self.id:02d} ({self.vcpus}vCPU/{self.ram_gb}GB/{self.gpu_vram_gb}GB VRAM)"


@dataclass
class Cluster:
    """Pool de instancias LLM."""
    instancias: list[InstanciaLLM] = field(default_factory=list)

    @property
    def throughput_total(self) -> int:
        return sum(i.tokens_por_segundo for i in self.instancias)

    @property
    def costo_hora(self) -> float:
        return sum(i.costo_hora_usd for i in self.instancias)

    @property
    def resumen(self) -> dict:
        return {
            "instancias": len(self.instancias),
            "throughput_total_tps": self.throughput_total,
            "costo_hora_usd": round(self.costo_hora, 3),
        }


# ─────────────────────────────────────────────────────────────
# 2. ESCALABILIDAD HORIZONTAL vs VERTICAL
# ─────────────────────────────────────────────────────────────

class EstrategiaEscalado:
    """Simula el escalado horizontal (más instancias) y vertical (mayor instancia)."""

    INSTANCIA_PEQUEÑA  = lambda: InstanciaLLM(0,  4,  8,  0,    2_000)   # CPU only
    INSTANCIA_MEDIANA  = lambda: InstanciaLLM(0,  8, 16, 16,   12_000)   # GPU T4
    INSTANCIA_GRANDE   = lambda: InstanciaLLM(0, 16, 32, 40,   35_000)   # GPU A100
    INSTANCIA_XLARGE   = lambda: InstanciaLLM(0, 64, 128, 80,  80_000)   # A100 SXM

    @staticmethod
    def escalar_horizontalmente(demanda_tps: int) -> Cluster:
        """
        Escala HORIZONTAL: N instancias medianas.
        Principio: si necesitas más capacidad, añade más unidades iguales.
        """
        instancia_tipo = EstrategiaEscalado.INSTANCIA_MEDIANA()
        n = math.ceil(demanda_tps / instancia_tipo.tokens_por_segundo)
        n = max(1, n)
        cluster = Cluster()
        for i in range(n):
            inst = EstrategiaEscalado.INSTANCIA_MEDIANA()
            inst.id = i
            cluster.instancias.append(inst)
        return cluster

    @staticmethod
    def escalar_verticalmente(demanda_tps: int) -> Cluster:
        """
        Escala VERTICAL: una instancia más grande.
        Limitado por el hardware disponible.
        """
        tipo_seleccionado = EstrategiaEscalado.INSTANCIA_XLARGE()
        # Si la XLARGE no alcanza, igual usamos solo una (límite físico)
        tipo_seleccionado.id = 0
        cluster = Cluster(instancias=[tipo_seleccionado])
        return cluster


def comparar_estrategias():
    print("\n  ── COMPARATIVA: Escalabilidad Horizontal vs Vertical ────")
    print()
    print(f"  {'Demanda TPS':>12}  {'Instancias H':>13}  {'Costo/h H':>10}  {'Costo/h V':>10}  {'Ventaja':>10}")
    print("  " + "-" * 65)

    for demanda_tps in [1_000, 5_000, 20_000, 60_000, 100_000]:
        ch = EstrategiaEscalado.escalar_horizontalmente(demanda_tps)
        cv = EstrategiaEscalado.escalar_verticalmente(demanda_tps)
        cubre_v = "✓" if cv.throughput_total >= demanda_tps else "✗ NO ALCANZA"
        ventaja = "Horizontal" if ch.costo_hora < cv.costo_hora else "Vertical"
        if cv.throughput_total < demanda_tps:
            ventaja = "Horizontal (V no alcanza)"
        print(
            f"  {demanda_tps:>12,}  "
            f"{len(ch.instancias):>10} instancias  "
            f"${ch.costo_hora:>8.2f}/h  "
            f"${cv.costo_hora:>8.2f}/h  "
            f"{ventaja}"
        )

    print("""
  CONCLUSIONES:
  • Horizontal: mejor para cargas masivas, alta disponibilidad, sin límite práctico.
    Desventaja: un modelo LLM grande (70B params) NO cabe en 1 GPU pequeña.
  • Vertical: mejor para modelos que no se particionan fácilmente.
    Desventaja: hay un máximo físico (GPU más grande disponible).
  • En la práctica: Tensor Parallelism (horizontal en GPUs) + Scale-out de réplicas.
    """)


# ─────────────────────────────────────────────────────────────
# 3. AUTO-SCALING SIMULADO (HPA-style)
# ─────────────────────────────────────────────────────────────

@dataclass
class MetricaAutoscaler:
    instancias_actuales: int
    min_instancias: int
    max_instancias: int
    umbral_scale_up: float    # Si CPU/GPU utilización > X%, escalar
    umbral_scale_down: float  # Si CPU/GPU utilización < X%, desescalar
    cooldown_s: float         # Tiempo mínimo entre decisiones
    _ultimo_escalado: float = field(default=0.0, init=False)

    def decidir(self, utilizacion: float) -> tuple[int, str]:
        """Retorna (nuevas_instancias, motivo)."""
        ahora = time.time()
        if ahora - self._ultimo_escalado < self.cooldown_s:
            return self.instancias_actuales, "cooldown activo"

        if utilizacion > self.umbral_scale_up:
            nuevas = min(self.max_instancias, self.instancias_actuales + 1)
            if nuevas != self.instancias_actuales:
                self._ultimo_escalado = ahora
                self.instancias_actuales = nuevas
            return nuevas, f"scale-up (util={utilizacion:.0%})"
        elif utilizacion < self.umbral_scale_down:
            nuevas = max(self.min_instancias, self.instancias_actuales - 1)
            if nuevas != self.instancias_actuales:
                self._ultimo_escalado = ahora
                self.instancias_actuales = nuevas
            return nuevas, f"scale-down (util={utilizacion:.0%})"

        return self.instancias_actuales, f"estable (util={utilizacion:.0%})"


def simular_autoscaling():
    """Simula un día de tráfico con patrón de carga real."""
    print("\n  ── SIMULACIÓN: Auto-Scaling (tipo HPA de Kubernetes) ────")
    print("""
  Escenario: e-commerce LATAM
  Horas pico: 12:00-14:00 y 19:00-22:00
  Instancias configuradas: min=1, max=8
    """)

    autoscaler = MetricaAutoscaler(
        instancias_actuales=2,
        min_instancias=1,
        max_instancias=8,
        umbral_scale_up=0.70,
        umbral_scale_down=0.30,
        cooldown_s=0.0,   # Simulación rápida sin cooldown real
    )

    # Patrón de tráfico simulado (0-23 horas)
    def trafico_hora(hora: int) -> float:
        """Utilización simulada según hora del día."""
        if 0 <= hora < 7:   return random.uniform(0.05, 0.15)   # Madrugada baja
        if 7 <= hora < 10:  return random.uniform(0.25, 0.45)   # Mañana
        if 10 <= hora < 12: return random.uniform(0.50, 0.65)   # Prealmuerzo
        if 12 <= hora < 14: return random.uniform(0.80, 0.95)   # Almuerzo (pico)
        if 14 <= hora < 18: return random.uniform(0.40, 0.60)   # Tarde
        if 18 <= hora < 22: return random.uniform(0.75, 0.90)   # Noche (pico 2)
        return random.uniform(0.10, 0.25)                         # Noche tardía

    print(f"  {'Hora':>5}  {'Utilización':>12}  {'Instancias':>11}  {'Decisión'}")
    print("  " + "-" * 65)
    instancias_max_alcanzado = 0
    for hora in range(24):
        util = trafico_hora(hora)
        instancias, motivo = autoscaler.decidir(util)
        instancias_max_alcanzado = max(instancias_max_alcanzado, instancias)
        barra_util = "█" * int(util * 20)
        barra_inst = "▪" * instancias
        print(f"  {hora:>02d}:00  {util:>6.0%}  {barra_util:<20}  {instancias:>3}×  {barra_inst:<8}  {motivo}")

    print(f"\n  Máximo de instancias alcanzado: {instancias_max_alcanzado}")
    print("""
  EQUIVALENTE EN KUBERNETES (HPA manifest):
  ──────────────────────────────────────────
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: llm-backend-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: llm-backend
    minReplicas: 1
    maxReplicas: 8
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # scale-up si CPU > 70%
    - type: External
      external:
        metric:
          name: llm_queue_depth    # KEDA: largo de cola de tokens
        target:
          type: AverageValue
          averageValue: "500"      # si cola > 500 tokens pendientes
    """)


# ─────────────────────────────────────────────────────────────
# 4. KUBERNETES vs DOCKER SWARM
# ─────────────────────────────────────────────────────────────

COMPARATIVA_ORQUESTADORES = {
    "Criterio": [
        "Curva de aprendizaje",
        "Instalación/setup",
        "Auto-scaling",
        "Service discovery",
        "Rolling updates",
        "Health checks",
        "Ecosistema (Helm, etc.)",
        "GPU scheduling",
        "Multicluster",
        "Ideal para LLM si…",
    ],
    "Kubernetes (K8s)": [
        "Alta (meses)",
        "Compleja (kubeadm, K3s, managed)",
        "HPA + KEDA + VPA + KHPA",
        "CoreDNS + Ingress + Service mesh",
        "Estrategias: RollingUpdate, Blue-Green",
        "Liveness + Readiness + Startup probes",
        "Helm, Kustomize, ArgoCD, Flux",
        "Device Plugin + NVIDIA operator",
        "Federation, Fleet, Submariner",
        "Equipo DevOps dedicado, >10 servicios",
    ],
    "Docker Swarm": [
        "Baja (días)",
        "Simple (docker swarm init)",
        "Básico (replica count manual)",
        "DNS interno automático",
        "update-config rolling básico",
        "healthcheck en Dockerfile",
        "Stack files (.yml) simples",
        "Limitado (--generic-resource)",
        "No nativo",
        "Equipo pequeño, <5 servicios, PoC/MVP",
    ],
}


def imprimir_comparativa():
    print("\n  ── COMPARATIVA: Kubernetes vs Docker Swarm ──────────────")
    print()
    cols = list(COMPARATIVA_ORQUESTADORES.keys())
    datos = list(COMPARATIVA_ORQUESTADORES.values())
    ancho = [28, 40, 35]

    header = "  " + "  ".join(f"{c:<{ancho[i]}}" for i, c in enumerate(cols))
    print(header)
    print("  " + "-" * 105)
    for idx in range(len(datos[0])):
        fila = "  " + "  ".join(f"{datos[j][idx]:<{ancho[j]}}" for j in range(len(cols)))
        print(fila[:108])


# ─────────────────────────────────────────────────────────────
# 5. BUSES DE MENSAJERÍA (Message Buses)
# ─────────────────────────────────────────────────────────────

class ColaMensajes:
    """Simulación simple de un bus de mensajería (tipo Kafka/RabbitMQ)."""

    def __init__(self, nombre: str, max_size: int = 100):
        self.nombre = nombre
        self._cola: deque = deque(maxlen=max_size)
        self._consumidos = 0

    def publicar(self, mensaje: dict) -> bool:
        if len(self._cola) >= self._cola.maxlen:
            return False   # Back-pressure
        self._cola.append({"id": len(self._cola) + self._consumidos, **mensaje})
        return True

    def consumir(self) -> Optional[dict]:
        if self._cola:
            self._consumidos += 1
            return self._cola.popleft()
        return None

    @property
    def pendientes(self) -> int:
        return len(self._cola)


def demo_mensaje_asincrono():
    print("\n  ── DEMO: Procesamiento Asíncrono con Cola de Mensajes ────")
    print("""
  PATRÓN: Producer → Queue → Consumer (Workers LLM)

  Ventajas para LLM:
  • Desacopla el front-end (respuesta HTTP inmediata al usuario)
    del procesamiento LLM (puede tardar segundos)
  • Permite absorber picos: la cola actúa como buffer
  • Facilita reintentos: si un worker falla, el mensaje vuelve a la cola
  • Permite prioridades: requests premium antes que batch jobs
    """)

    cola = ColaMensajes("llm-requests", max_size=10)

    # Publicar requests
    requests_entrantes = [
        {"tipo": "chat",    "usuario": "u001", "tokens_est": 512,  "prioridad": "normal"},
        {"tipo": "summary", "usuario": "u002", "tokens_est": 8000, "prioridad": "batch"},
        {"tipo": "chat",    "usuario": "u003", "tokens_est": 256,  "prioridad": "premium"},
        {"tipo": "embed",   "usuario": "u004", "tokens_est": 100,  "prioridad": "normal"},
        {"tipo": "chat",    "usuario": "u005", "tokens_est": 1024, "prioridad": "normal"},
    ]

    print("  Publicando en cola:")
    for req in requests_entrantes:
        ok = cola.publicar(req)
        icono = "✓" if ok else "✗ COLA LLENA"
        print(f"  {icono}  {req['tipo']:<10}  usuario={req['usuario']}  "
              f"tokens≈{req['tokens_est']:>5}  [{req['prioridad']}]")

    print(f"\n  Mensajes en cola: {cola.pendientes}")
    print("\n  Workers consumiendo:")
    worker_id = 1
    while (msg := cola.consumir()) is not None:
        latencia_sim = msg["tokens_est"] // 500 + 1   # Simula tiempo de proceso
        print(f"  Worker-{worker_id % 2 + 1}  procesó msg-{msg['id']}  "
              f"{msg['tipo']:<10}  ~{latencia_sim}s")
        worker_id += 1

    print(f"\n  Cola vacía. {cola._consumidos} mensajes procesados.")
    print("""
  EQUIVALENTE EN PRODUCCIÓN:
  ──────────────────────────
  • Apache Kafka:    Alta durabilidad, particiones, millones de msgs/s
  • RabbitMQ:        Routing flexible, ACK, dead-letter queue
  • AWS SQS + SNS:   Serverless, cero ops, integración AWS nativa
  • Google Pub/Sub:  Serverless, entrega garantizada, global
  • Redis Streams:   Ligero, latencia ultra-baja, ideal para PoC

  Para LLM específicamente:
  • La cola absorbe el "burstiness" de requests (ej: cuando todos piden
    a la vez al terminar una reunión o publicar un artículo viral).
  • KEDA (Kubernetes Event Driven Autoscaler) escala pods de workers
    basándose en la profundidad de la cola de Kafka/SQS.
    """)


# ─────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  LAB 08 – ESCALABILIDAD Y ORQUESTACIÓN DE LLMs")
    print("  Curso: Fundamentos de Arquitectura LLM | Sesión 2 – Tema 4")
    print("=" * 80)

    print("""
  PRINCIPIO FUNDAMENTAL
  ─────────────────────────────────────────────────────────────
  Un sistema escalable puede manejar un AUMENTO de carga
  añadiendo recursos de forma PROPORCIONAL al incremento,
  sin rediseñar la arquitectura.

  Dos dimensiones de escalabilidad:

    VERTICAL (Scale-Up):   Reemplaza por instancia más grande
    ─────────────────────  A100 → H100, 8 vCPU → 64 vCPU
    Límite: hardware más grande disponible.
    Sin HA nativa (SPOF).

    HORIZONTAL (Scale-Out): Añade más instancias iguales
    ──────────────────────  1 réplica → 8 réplicas
    Límite: coordinación (consistency, sesiones compartidas).
    Alta disponibilidad inherente.
    """)

    comparar_estrategias()
    simular_autoscaling()
    imprimir_comparativa()
    demo_mensaje_asincrono()

    print("""
  ─────────────────────────────────────────────────────────────
  GUÍA DE DECISIÓN: ¿Kubernetes o Docker Swarm?
  ─────────────────────────────────────────────────────────────

  USA DOCKER SWARM cuando:
  ✓ El equipo tiene < 5 personas de infraestructura
  ✓ Es un MVP o PoC con plazo < 3 meses
  ✓ Tienes < 10 servicios / contenedores
  ✓ No necesitas GPU scheduling avanzado
  ✓ Ya usas Docker Compose y quieres mínimo cambio

  USA KUBERNETES cuando:
  ✓ Necesitas auto-scaling basado en métricas de LLM (KEDA)
  ✓ Tienes GPUs heterogéneas que requieren scheduling
  ✓ Necesitas multi-región o multi-cluster
  ✓ El equipo ya tiene experiencia K8s o planea invertir en ella
  ✓ Tienes requisitos de compliance (pod security, network policies)

  RECOMENDACIÓN LATAM:
  Para el 80% de las empresas medianas de la región:
  Empieza con Docker Swarm → migra a K8s cuando superes
  10 servicios o necesites KEDA para cola de tokens LLM.
  ─────────────────────────────────────────────────────────────
    """)


if __name__ == "__main__":
    main()
