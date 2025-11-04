from __future__ import annotations

import re
from time import perf_counter
from typing import Callable, Awaitable

from starlette.types import ASGIApp, Receive, Scope, Send

from app.shared.metrics import http_requests_total, http_request_duration_seconds


class MetricsMiddleware:
    """
    Collects Prometheus HTTP metrics for requests hitting the todos endpoints.
    Labels: method, normalized path template, status code.
    """

    def __init__(self, app: ASGIApp, include_pattern: str = r"^/api/v1/todos") -> None:
        self.app = app
        self.include_re = re.compile(include_pattern)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("raw_path") or scope.get("path", "")  # type: ignore[assignment]
        method = scope.get("method", "").upper()  # type: ignore[assignment]

        # Only record for specified endpoints (todos)
        if not self.include_re.search(path.decode() if isinstance(path, (bytes, bytearray)) else path):
            await self.app(scope, receive, send)
            return

        start = perf_counter()
        status_code_holder: dict[str, int] = {"status": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_code_holder["status"] = int(message.get("status", 500))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = perf_counter() - start
            status = str(status_code_holder["status"])
            norm_path = self._normalize_path(path)
            http_requests_total.labels(method=method, path=norm_path, status=status).inc()
            http_request_duration_seconds.labels(method=method, path=norm_path, status=status).observe(duration)

    @staticmethod
    def _normalize_path(path: str | bytes) -> str:
        if isinstance(path, (bytes, bytearray)):
            path = path.decode()
        # Remove trailing slashes for cardinality control
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        # Replace numeric ids with :id
        path = re.sub(r"/\d+", "/:id", path)
        return path
