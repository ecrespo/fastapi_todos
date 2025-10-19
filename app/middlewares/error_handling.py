from __future__ import annotations

import logging
import traceback
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.shared.config import get_settings
from app.shared.LoggerSingleton import logger

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Catches unhandled exceptions, logs them, and returns a JSON 500 response.

    If debug mode is enabled in settings, include a short error summary to help troubleshooting.
    """

    def __init__(self, app, logger) -> None:
        super().__init__(app)
        self._logger = logger
        self._settings = get_settings()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001
            # Log full traceback for diagnostics
            # tb = traceback.format_exc()
            self._logger.exception(
                "Unhandled exception during request processing",
                extra={
                    "method": request.method,
                    "url": str(request.url),
                    "client": request.client.host if request.client else None,
                },
            )
            detail: str | dict[str, str]
            if self._settings.debug:
                detail = {
                    "error": str(exc),
                    "type": exc.__class__.__name__,
                }
            else:
                detail = "Internal Server Error"
            return JSONResponse(status_code=500, content={"detail": detail})
