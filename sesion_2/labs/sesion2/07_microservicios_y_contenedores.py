"""
Lab 07 – Patrones de Microservicios y Contenedores para LLM
============================================================
Tema #4: Patrones y escalabilidad
Objetivo: Demostrar los patrones arquitectónicos más usados en
         soluciones LLM a escala: API Gateway, Circuit Breaker,
         Sidecar, y análisis de configuraciones Docker.

NO requiere Docker instalado — simula los patrones con Python puro.

Ejecutar:
    cd labs/sesion2
    python 07_microservicios_y_contenedores.py
"""

from __future__ import annotations

import time
import random
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque
from typing import Callable, Optional, Any


# ─────────────────────────────────────────────────────────────
# 1. PATRÓN: API GATEWAY (fachada unificada)
# ─────────────────────────────────────────────────────────────

@dataclass
class ServicioLLM:
    """Simula un microservicio LLM independiente."""
    nombre: str
    latencia_ms: int        # latencia base
    tasa_error: float       # 0.0 – 1.0
    capacidad_rps: int      # requests/segundo máximos

    def llamar(self, prompt: str) -> dict:
        """Simula una llamada al servicio."""
        time.sleep(self.latencia_ms / 1_000)
        if random.random() < self.tasa_error:
            raise ConnectionError(f"[{self.nombre}] Error simulado")
        tokens = len(prompt.split()) * 4
        return {
            "servicio": self.nombre,
            "respuesta": f"Respuesta de {self.nombre}: procesado '{prompt[:30]}...'",
            "tokens": tokens,
            "latencia_ms": self.latencia_ms,
        }


class RoundRobinGateway:
    """
    Patrón API Gateway con balanceo Round-Robin.
    El Gateway es el punto de entrada único — los clientes
    nunca conocen qué servicio físico responde.
    """

    def __init__(self, servicios: list[ServicioLLM]):
        self.servicios = servicios
        self._idx = 0
        self._lock = threading.Lock()
        self.stats: dict[str, dict] = {s.nombre: {"ok": 0, "err": 0} for s in servicios}

    def _siguiente(self) -> ServicioLLM:
        with self._lock:
            s = self.servicios[self._idx % len(self.servicios)]
            self._idx += 1
        return s

    def request(self, prompt: str) -> Optional[dict]:
        svc = self._siguiente()
        try:
            resultado = svc.llamar(prompt)
            self.stats[svc.nombre]["ok"] += 1
            return resultado
        except ConnectionError as e:
            self.stats[svc.nombre]["err"] += 1
            print(f"    Gateway captó error: {e} → retrying con siguiente servicio")
            # Reintento simple con siguiente
            svc2 = self._siguiente()
            try:
                resultado = svc2.llamar(prompt)
                self.stats[svc2.nombre]["ok"] += 1
                return resultado
            except ConnectionError:
                self.stats[svc2.nombre]["err"] += 1
                return None

    def imprimir_stats(self):
        print("\n  ── Estadísticas Gateway ──────────────────")
        for nombre, s in self.stats.items():
            total = s["ok"] + s["err"]
            ok_pct = (s["ok"] / total * 100) if total else 0
            print(f"  {nombre:<20}  OK: {s['ok']:>3}  Err: {s['err']:>2}  ({ok_pct:.0f}% éxito)")


# ─────────────────────────────────────────────────────────────
# 2. PATRÓN: CIRCUIT BREAKER
# ─────────────────────────────────────────────────────────────

class EstadoCB(Enum):
    CERRADO  = auto()   # Normal — deja pasar requests
    ABIERTO  = auto()   # Falla detectada — bloquea requests
    SEMIABIERTO = auto() # Prueba si el servicio se recuperó


@dataclass
class CircuitBreaker:
    """
    Circuit Breaker para llamadas a LLMs.
    Evita que una cascada de errores derribe todo el sistema.

    Analogía: un disyuntor eléctrico que se abre al detectar
    sobrecarga, evitando que el cortocircuito queme el circuito completo.
    """
    nombre: str
    umbral_errores: int = 3         # Errores consecutivos para abrir
    timeout_abierto_s: float = 2.0  # Tiempo antes de intentar semi-abrir
    funcion: Optional[Callable] = None

    estado: EstadoCB = field(default=EstadoCB.CERRADO, init=False)
    _errores_consec: int = field(default=0, init=False)
    _abierto_desde: float = field(default=0.0, init=False)

    def llamar(self, *args, **kwargs) -> Any:
        if self.estado == EstadoCB.ABIERTO:
            if time.time() - self._abierto_desde > self.timeout_abierto_s:
                self.estado = EstadoCB.SEMIABIERTO
                print(f"    CB [{self.nombre}]: SEMI-ABIERTO → probando recuperación")
            else:
                raise RuntimeError(f"Circuit Breaker [{self.nombre}] ABIERTO — solicitud rechazada")

        try:
            resultado = self.funcion(*args, **kwargs)
            if self.estado == EstadoCB.SEMIABIERTO:
                self.estado = EstadoCB.CERRADO
                self._errores_consec = 0
                print(f"    CB [{self.nombre}]: CERRADO ← servicio recuperado")
            return resultado
        except Exception as exc:
            self._errores_consec += 1
            if self._errores_consec >= self.umbral_errores:
                self.estado = EstadoCB.ABIERTO
                self._abierto_desde = time.time()
                print(f"    CB [{self.nombre}]: ABIERTO ✗ ({self._errores_consec} errores)")
            raise


# ─────────────────────────────────────────────────────────────
# 3. ANÁLISIS DE DOCKERFILE MULTI-STAGE
# ─────────────────────────────────────────────────────────────

DOCKERFILE_MONOLITICO = """\
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
# Incluye código fuente, archivos de test, .git, caché de pip
CMD ["uvicorn", "app.main:app"]
"""

DOCKERFILE_MULTISTAGE = """\
# ── Etapa 1: builder ────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt

# ── Etapa 2: runtime (imagen final) ─────────────────────────
FROM python:3.12-slim AS runtime
# Usuario sin privilegios (principio de mínimo privilegio)
RUN useradd -m -u 1000 appuser
WORKDIR /app
# Solo las dependencias compiladas, sin pip ni caché
COPY --from=builder /install /usr/local
# Solo el código de producción
COPY --chown=appuser:appuser ./backend/app ./app
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

DOCKER_COMPOSE_LLM = """\
version: "3.9"
services:

  # ── Servicio LLM local ─────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama_models:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # ── Backend FastAPI ────────────────────────────────────
  backend:
    build:
      context: .
      target: runtime      # usa solo la etapa de producción
    ports: ["8000:8000"]
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - LOG_LEVEL=info
    depends_on: [ollama]
    deploy:
      replicas: 2          # 2 réplicas para HA básica
      restart_policy:
        condition: on-failure
        max_attempts: 3

  # ── Frontend React/Nginx ───────────────────────────────
  frontend:
    build: ./frontend
    ports: ["80:80"]
    depends_on: [backend]

  # ── Proxy inverso / API Gateway ───────────────────────
  nginx:
    image: nginx:alpine
    ports: ["443:443"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on: [backend, frontend]

volumes:
  ollama_models:
"""

HEALTHCHECK_PATTERN = """\
# Patrón Health Check para contenedores LLM
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:8000/health || exit 1

# En FastAPI:
@app.get("/health")
async def health():
    checks = {
        "api": "ok",
        "ollama": await ping_ollama(),    # Verifica servicio LLM
        "memoria_libre_gb": psutil.virtual_memory().available / 1e9,
    }
    status = "ok" if all(v == "ok" or isinstance(v, float) for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
"""


def analizar_dockerfiles():
    print("\n  ── ANÁLISIS: Dockerfile Monolítico vs Multi-Stage ──────")
    print("\n  [MONOLÍTICO] Estimación de tamaño:")
    print("   python:3.12 base:          ~1.0 GB")
    print("   + dependencias pip:        ~300 MB")
    print("   + código fuente + tests:   ~50  MB")
    print("   + caché pip:               ~150 MB")
    print("   TOTAL estimado:           ~1.5 GB")

    print("\n  [MULTI-STAGE] Estimación de tamaño:")
    print("   python:3.12-slim base:     ~130 MB")
    print("   + dependencias (solo lib): ~200 MB")
    print("   + código producción:       ~5   MB")
    print("   + sin pip, sin caché:      +0   MB")
    print("   TOTAL estimado:           ~335 MB")
    print("   REDUCCIÓN:                ~78%")

    print("\n  Beneficios del multi-stage para LLM:")
    print("  • Menor superficie de ataque (sin compiladores en prod)")
    print("  • Builds reproducibles: el builder nunca contamina runtime")
    print("  • Usuario sin privilegios: si el contenedor es comprometido,")
    print("    el atacante no tiene permisos root")
    print("  • --no-cache-dir: la imagen nunca tiene caché de pip descargable")


# ─────────────────────────────────────────────────────────────
# 4. PATRÓN SIDECAR (Log Aggregation)
# ─────────────────────────────────────────────────────────────

class SidecarLogger:
    """
    Simula el patrón Sidecar para agregación de logs.
    El sidecar corre en el mismo pod (Kubernetes) o stack (Docker)
    pero en un contenedor separado, sin modificar el servicio principal.
    """

    def __init__(self, destino: str = "stdout"):
        self._buffer: deque = deque(maxlen=100)
        self.destino = destino

    def registrar(self, nivel: str, mensaje: str, metadata: dict | None = None):
        entrada = {
            "timestamp": time.time(),
            "nivel": nivel,
            "mensaje": mensaje,
            "metadata": metadata or {},
        }
        self._buffer.append(entrada)
        # En producción, enviaría a Fluentd, Datadog, CloudWatch, etc.
        return entrada

    def flush(self):
        """Simula el envío periódico del sidecar."""
        entradas = list(self._buffer)
        self._buffer.clear()
        return entradas


# ─────────────────────────────────────────────────────────────
# 5. DEMO INTEGRADA
# ─────────────────────────────────────────────────────────────

def demo_api_gateway():
    print("\n  ── DEMO 1: API Gateway con Round-Robin ──────────────────")
    servicios = [
        ServicioLLM("llm-replica-1", latencia_ms=50, tasa_error=0.05, capacidad_rps=10),
        ServicioLLM("llm-replica-2", latencia_ms=55, tasa_error=0.05, capacidad_rps=10),
        ServicioLLM("llm-replica-3", latencia_ms=60, tasa_error=0.30, capacidad_rps=10),  # instancia degradada
    ]
    gateway = RoundRobinGateway(servicios)

    prompts = [
        "¿Cuáles son los modelos LLM más usados en LATAM?",
        "Explica el patrón Circuit Breaker",
        "¿Qué es Docker multi-stage build?",
        "Resume el concepto de microservicios",
        "¿Cuándo usar Kubernetes vs Docker Swarm?",
        "Define escalabilidad horizontal",
    ]

    print(f"  Enviando {len(prompts)} requests a través del Gateway...")
    for prompt in prompts:
        resultado = gateway.request(prompt)
        if resultado:
            print(f"  ✓ {resultado['servicio']:<20} {resultado['latencia_ms']:>4}ms  '{prompt[:35]}...'")
        else:
            print(f"  ✗ Todos los reintentos fallaron: '{prompt[:35]}...'")

    gateway.imprimir_stats()


def demo_circuit_breaker():
    print("\n\n  ── DEMO 2: Circuit Breaker ───────────────────────────────")

    # Servicio que falla inicialmente y luego se recupera
    llamadas = [0]
    def servicio_inestable(prompt: str) -> str:
        llamadas[0] += 1
        # Falla en llamadas 1, 2, 3 — se "recupera" después
        if llamadas[0] <= 3:
            raise ConnectionError(f"Timeout en llamada {llamadas[0]}")
        return f"Respuesta OK (llamada {llamadas[0]})"

    cb = CircuitBreaker(
        nombre="llm-servicio",
        umbral_errores=3,
        timeout_abierto_s=0.5,
        funcion=servicio_inestable,
    )

    print(f"  Estado inicial: {cb.estado.name}")
    for intento in range(8):
        time.sleep(0.1)
        try:
            resultado = cb.llamar("test")
            print(f"  Intento {intento+1}: ✓ {resultado}  Estado: {cb.estado.name}")
        except RuntimeError as e:
            print(f"  Intento {intento+1}: ✗ {e}")
        except ConnectionError as e:
            print(f"  Intento {intento+1}: ✗ ConnectionError: {e}  Estado: {cb.estado.name}")


def demo_sidecar():
    print("\n\n  ── DEMO 3: Patrón Sidecar (Log Aggregation) ─────────────")
    sidecar = SidecarLogger()
    sidecar.registrar("INFO",  "Request recibido", {"tokens": 512, "modelo": "gemini-2.5-flash"})
    sidecar.registrar("INFO",  "Cache HIT",        {"clave": "hash:abc123"})
    sidecar.registrar("WARN",  "Latencia alta",    {"p99_ms": 4200, "umbral_ms": 3000})
    sidecar.registrar("ERROR", "Token limit exceeded", {"max": 8192, "solicitado": 9000})

    entradas = sidecar.flush()
    print(f"  Sidecar agregó {len(entradas)} entradas de log:")
    for e in entradas:
        print(f"  [{e['nivel']:<5}] {e['mensaje']:<30}  {e['metadata']}")
    print("\n  (En producción: enviadas a Fluentd → Elasticsearch/CloudWatch)")


def mostrar_dockerfiles():
    print("\n\n  ── REFERENCIA: Dockerfile Multi-Stage ───────────────────")
    analizar_dockerfiles()

    print("\n\n  ── REFERENCIA: Docker Compose para stack LLM ────────────")
    print("  (Extracto ilustrativo — ver docker-compose.yml en el repo)")
    for linea in DOCKER_COMPOSE_LLM.splitlines()[:20]:
        print(f"  {linea}")
    print("  ...")

    print("\n\n  ── REFERENCIA: Patrón Health Check ──────────────────────")
    for linea in HEALTHCHECK_PATTERN.splitlines():
        print(f"  {linea}")


# ─────────────────────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 80)
    print("  LAB 07 – PATRONES DE MICROSERVICIOS Y CONTENEDORES PARA LLM")
    print("  Curso: Fundamentos de Arquitectura LLM | Sesión 2 – Tema 4")
    print("=" * 80)

    print("""
  MARCO CONCEPTUAL
  ─────────────────────────────────────────────────────────────
  Los sistemas LLM en producción NO son aplicaciones monolíticas.
  Se componen de múltiples servicios especializados:

    ┌──────────┐    ┌───────────────┐    ┌──────────────┐
    │  Cliente │───▶│  API Gateway  │───▶│ Servicio LLM │×N
    └──────────┘    │  (Rate limit) │    │ (contenedor) │
                    │  (Auth/JWT)   │    └──────────────┘
                    │  (Logging)    │           │
                    └───────────────┘    ┌──────▼──────┐
                                         │ Circuit     │
                                         │ Breaker     │
                                         └─────────────┘

  Patrones clave para LLM:
  1. API Gateway:       Punto único de entrada, abstrae complejidad
  2. Circuit Breaker:   Tolerancia a fallos, evita cascadas de error
  3. Sidecar:          Logging/monitoring sin modificar el servicio
  4. Multi-stage build: Imágenes mínimas y seguras
    """)

    demo_api_gateway()
    demo_circuit_breaker()
    demo_sidecar()
    mostrar_dockerfiles()

    print("""
  ─────────────────────────────────────────────────────────────
  RESUMEN DE PATRONES
  ─────────────────────────────────────────────────────────────
  PATRÓN          PROBLEMA QUE RESUELVE
  ─────────────────────────────────────
  API Gateway     Clientes no deben conocer la topología interna.
                  Centraliza: auth, rate-limit, logging, routing.

  Circuit Breaker Un LLM lento o caído no debe derribar todo el sistema.
                  Se "abre" al detectar N errores consecutivos,
                  rechazando requests rápido hasta que el servicio sane.

  Sidecar         Añadir logging, métricas o mTLS SIN modificar el
                  contenedor principal. Misma red y volúmenes, desacoplado.

  Multi-stage     Imagen de desarrollo ≠ imagen de producción.
                  El compilador, pip cache y archivos de test no deben
                  llegar al ambiente productivo.
  ─────────────────────────────────────────────────────────────
    """)


if __name__ == "__main__":
    main()
