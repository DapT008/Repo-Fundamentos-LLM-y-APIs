"""
Circuit Breaker — Tema 5: Alta Disponibilidad

Patrón de resiliencia que protege el sistema cuando un servicio externo
(Ollama, proveedor LLM en la nube) empieza a fallar.

Estados:
  CERRADO  → peticiones pasan normalmente; se cuentan los fallos
  ABIERTO  → peticiones rechazadas inmediatamente (fail-fast)
  SEMIABIERTO → se permite una petición de prueba

                 N fallos
  CERRADO ────────────────→ ABIERTO
     ↑                          │
     │ prueba exitosa            │ timeout
     └──── SEMIABIERTO ←────────┘
"""

import asyncio
import time
from enum import Enum
from typing import Callable, Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CERRADO"
    OPEN = "ABIERTO"
    HALF_OPEN = "SEMIABIERTO"


class CircuitBreakerOpenError(Exception):
    """Se lanza cuando el circuito está ABIERTO (fail-fast)."""
    pass


class CircuitBreaker:
    """
    Circuit breaker genérico, seguro para asyncio.

    Uso básico
    ----------
    cb = CircuitBreaker(name="ollama")

    result = await cb.call(my_async_func, arg1, arg2)

    Parámetros
    ----------
    name : str
        Nombre descriptivo para los logs.
    failure_threshold : int
        Número de fallos consecutivos para abrir el circuito.
    recovery_timeout : int
        Segundos que el circuito permanece ABIERTO antes de pasar a SEMIABIERTO.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int | None = None,
        recovery_timeout: int | None = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold or settings.CB_FAILURE_THRESHOLD
        self.recovery_timeout = recovery_timeout or settings.CB_RECOVERY_TIMEOUT

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    # ── Propiedad de estado ──────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def get_status(self) -> dict:
        """Alias de status_dict() para compatibilidad."""
        return self.status_dict()

    def status_dict(self) -> dict:
        """Retorna el estado actual para exponer en /health."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "threshold": self.failure_threshold,
            "seconds_until_retry": max(
                0,
                self.recovery_timeout - (time.time() - self._last_failure_time)
            ) if self._state == CircuitState.OPEN else 0,
        }

    # ── Lógica principal ─────────────────────────────────────────────────────

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Llama a `func` con protección del circuit breaker.

        Lanza
        -----
        CircuitBreakerOpenError : si el circuito está ABIERTO.
        Exception               : la excepción original si la llamada falla.
        """
        async with self._lock:
            await self._maybe_transition_to_half_open()

            if self._state == CircuitState.OPEN:
                logger.warning(
                    "Circuit breaker ABIERTO — petición rechazada",
                    circuit=self.name,
                )
                raise CircuitBreakerOpenError(
                    f"Servicio '{self.name}' no disponible. "
                    f"Reintentando en {self.recovery_timeout}s."
                )

        # Ejecutar la función FUERA del lock para no bloquear
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except CircuitBreakerOpenError:
            raise
        except Exception as exc:
            await self._on_failure(exc)
            raise

    # ── API síncrona para testing ────────────────────────────────────────────

    def record_failure(self) -> None:
        """Registra un fallo de forma síncrona (útil en tests)."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if (
            self._state == CircuitState.HALF_OPEN
            or self._failure_count >= self.failure_threshold
        ):
            self._state = CircuitState.OPEN

    def record_success(self) -> None:
        """Registra un éxito de forma síncrona (útil en tests)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0

    def can_pass_request(self) -> bool:
        """
        Verifica si una petición puede pasar.
        Si el circuito está OPEN y ha pasado el timeout, lo pasa a HALF_OPEN.
        """
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.HALF_OPEN:
            return True
        if (
            self._state == CircuitState.OPEN
            and time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            return True
        return False

    # ── Transiciones de estado ───────────────────────────────────────────────

    async def _maybe_transition_to_half_open(self) -> None:
        if (
            self._state == CircuitState.OPEN
            and time.time() - self._last_failure_time >= self.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            logger.info(
                "Circuit breaker → SEMIABIERTO (probando recuperación)",
                circuit=self.name,
            )

    async def _on_success(self) -> None:
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "Circuit breaker → CERRADO (servicio recuperado)",
                    circuit=self.name,
                )
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _on_failure(self, exc: Exception) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if (
                self._state == CircuitState.HALF_OPEN
                or self._failure_count >= self.failure_threshold
            ):
                self._state = CircuitState.OPEN
                logger.error(
                    "Circuit breaker → ABIERTO",
                    circuit=self.name,
                    failure_count=self._failure_count,
                    error=str(exc),
                )
            else:
                logger.warning(
                    "Fallo registrado en circuit breaker",
                    circuit=self.name,
                    failure_count=self._failure_count,
                    threshold=self.failure_threshold,
                    error=str(exc),
                )


# ── Instancias globales (una por servicio externo) ────────────────────────────

ollama_cb = CircuitBreaker(name="ollama")
