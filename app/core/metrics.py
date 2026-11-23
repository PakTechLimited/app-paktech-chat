"""Prometheus metrics.

gunicorn runs several worker processes, so metrics are kept in multiprocess
mode (PROMETHEUS_MULTIPROC_DIR) and summed when /metrics is read. Labels are
kept low-cardinality on purpose: the route template, never the raw URL.
"""

import os
import time

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from starlette.responses import Response

HTTP_REQUESTS = Counter(
    "http_requests", "HTTP requests handled", ["method", "route", "status"]
)
HTTP_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
WS_CONNECTIONS = Gauge(
    "ws_connections_active",
    "Open WebSocket connections",
    multiprocess_mode="livesum",
)
WS_MESSAGES = Counter("ws_messages", "Chat messages sent over WebSocket")
WS_ATTEMPTS = Counter(
    "ws_connection_attempts", "WebSocket connection attempts by outcome", ["result"]
)


def _route_label(path: str, scope) -> str:
    """Full route template, e.g. /api/v1/rooms/{room_id}; unmatched for anything else.

    scope["route"].path is relative to the router prefix in this FastAPI version,
    so the template is rebuilt from the original path by turning each matched
    path-parameter value back into its {name}.
    """
    if scope.get("route") is None:
        return "unmatched"
    params = {str(v): k for k, v in scope.get("path_params", {}).items()}
    segments = [f"{{{params[s]}}}" if s in params else s for s in path.split("/")]
    return "/".join(segments) or "/"


class MetricsMiddleware:
    """Pure ASGI middleware: records every HTTP request except /metrics itself."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] == "/metrics":
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500
        path = scope["path"]  # full path, before routers rewrite the scope

        async def send_wrapper(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            route = _route_label(path, scope)
            method = scope["method"]
            HTTP_REQUESTS.labels(method, route, str(status)).inc()
            HTTP_LATENCY.labels(method, route).observe(time.perf_counter() - start)


def metrics_response() -> Response:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        data = generate_latest(registry)
    else:
        data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
