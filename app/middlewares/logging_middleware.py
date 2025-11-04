from __future__ import annotations

import time
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    import structlog


class LoggingMiddleware(BaseHTTPMiddleware):
    """Structured request/response logger with latency measurement using structlog."""

    def __init__(self, app, logger: structlog.stdlib.BoundLogger) -> None:
        super().__init__(app)
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response: Response | None = None

        # Extract request metadata
        request_id = request.headers.get("x-request-id", "")
        client_host = request.client.host if request.client else "unknown"

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000

            # Structured logging with context
            self._logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                client_host=client_host,
                request_id=request_id,
                query_params=str(request.query_params) if request.query_params else None,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000

            # Log error with structured context
            self._logger.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                client_host=client_host,
                request_id=request_id,
                error=str(exc),
                exc_info=True,
            )
            raise

        return response
