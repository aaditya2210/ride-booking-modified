import time

from prometheus_client import Counter, Gauge, Histogram, make_asgi_app


HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests handled by a service.",
    ["service", "method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["service", "method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of in-flight HTTP requests.",
    ["service", "method"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state as a one-hot gauge.",
    ["service", "breaker", "state"],
)

CIRCUIT_BREAKER_CALLS_TOTAL = Counter(
    "circuit_breaker_calls_total",
    "Circuit breaker call outcomes.",
    ["service", "breaker", "outcome"],
)

CIRCUIT_BREAKER_TRANSITIONS_TOTAL = Counter(
    "circuit_breaker_state_transitions_total",
    "Circuit breaker state transitions.",
    ["service", "breaker", "state"],
)

NOTIFICATION_WEBSOCKET_CONNECTIONS = Gauge(
    "notification_websocket_connections",
    "Number of active notification websocket connections.",
    ["service"],
)


def _normalize_path(request) -> str:
    route = request.scope.get("route")
    if route and getattr(route, "path", None):
        return route.path
    return request.url.path


def configure_observability(app, service_name: str) -> None:
    if getattr(app.state, "observability_configured", False):
        return

    app.mount("/metrics", make_asgi_app())

    @app.middleware("http")
    async def prometheus_middleware(request, call_next):
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        HTTP_REQUESTS_IN_PROGRESS.labels(service=service_name, method=method).inc()
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.perf_counter() - started_at
            path = _normalize_path(request)
            HTTP_REQUESTS_TOTAL.labels(
                service=service_name,
                method=method,
                path=path,
                status=str(status_code),
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=service_name,
                method=method,
                path=path,
            ).observe(duration)
            HTTP_REQUESTS_IN_PROGRESS.labels(service=service_name, method=method).dec()

    app.state.observability_configured = True


def set_notification_websocket_connections(service_name: str, count: int) -> None:
    NOTIFICATION_WEBSOCKET_CONNECTIONS.labels(service=service_name).set(count)
