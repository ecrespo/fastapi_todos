from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Simple request/response logger with latency measurement."""

    def __init__(self, app, logger) -> None:
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response: Response
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            # Use extra fields to keep message simple and structure in extras
            self._logger.info(
                "%s %s -> %s (%.2f ms)",
                request.method,
                request.url.path,
                "<pending>",
                duration_ms,
            )
        # Adjust log to include final status code (log again with code, keeping above to ensure logging even on early errors)
        # Overwrite with a clearer event
        self._logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
