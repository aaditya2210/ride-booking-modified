import threading
import time

from shared.observability import (
    CIRCUIT_BREAKER_CALLS_TOTAL,
    CIRCUIT_BREAKER_STATE,
    CIRCUIT_BREAKER_TRANSITIONS_TOTAL,
)


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a circuit breaker short-circuits a call."""


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    STATES = (CLOSED, OPEN, HALF_OPEN)

    def __init__(
        self,
        name: str,
        service_name: str,
        failure_threshold: int = 3,
        recovery_timeout: int = 30,
        half_open_success_threshold: int = 1,
    ) -> None:
        self.name = name
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold
        self._lock = threading.Lock()
        self._state = self.CLOSED
        self._failure_count = 0
        self._half_open_successes = 0
        self._opened_at = 0.0
        self._sync_state_metrics_locked()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "service": self.service_name,
                "state": self._state,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "half_open_success_threshold": self.half_open_success_threshold,
                "failure_count": self._failure_count,
                "half_open_successes": self._half_open_successes,
            }

    def call(self, func, *args, **kwargs):
        self._before_call()
        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            CIRCUIT_BREAKER_CALLS_TOTAL.labels(
                service=self.service_name,
                breaker=self.name,
                outcome="failure",
            ).inc()
            raise

        self._record_success()
        CIRCUIT_BREAKER_CALLS_TOTAL.labels(
            service=self.service_name,
            breaker=self.name,
            outcome="success",
        ).inc()
        return result

    def _before_call(self) -> None:
        with self._lock:
            if self._state != self.OPEN:
                return

            now = time.monotonic()
            if now - self._opened_at >= self.recovery_timeout:
                self._transition_to_locked(self.HALF_OPEN)
                return

        CIRCUIT_BREAKER_CALLS_TOTAL.labels(
            service=self.service_name,
            breaker=self.name,
            outcome="short_circuit",
        ).inc()
        raise CircuitBreakerOpenError(
            f"Circuit breaker '{self.name}' is open for service '{self.service_name}'"
        )

    def _record_success(self) -> None:
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_success_threshold:
                    self._transition_to_locked(self.CLOSED)
                return

            self._failure_count = 0

    def _record_failure(self) -> None:
        with self._lock:
            if self._state == self.HALF_OPEN:
                self._transition_to_locked(self.OPEN)
                return

            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._transition_to_locked(self.OPEN)

    def _transition_to_locked(self, new_state: str) -> None:
        if new_state == self._state:
            self._sync_state_metrics_locked()
            return

        self._state = new_state
        if new_state == self.OPEN:
            self._opened_at = time.monotonic()
            self._failure_count = 0
            self._half_open_successes = 0
        elif new_state == self.HALF_OPEN:
            self._half_open_successes = 0
        else:
            self._failure_count = 0
            self._half_open_successes = 0
            self._opened_at = 0.0

        CIRCUIT_BREAKER_TRANSITIONS_TOTAL.labels(
            service=self.service_name,
            breaker=self.name,
            state=new_state,
        ).inc()
        self._sync_state_metrics_locked()

    def _sync_state_metrics_locked(self) -> None:
        for state in self.STATES:
            CIRCUIT_BREAKER_STATE.labels(
                service=self.service_name,
                breaker=self.name,
                state=state,
            ).set(1 if self._state == state else 0)
