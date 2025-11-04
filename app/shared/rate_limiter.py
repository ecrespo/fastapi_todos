import os
from collections.abc import Callable
from typing import Any

try:
    from fastapi import FastAPI
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    from app.shared.config import get_settings

    settings = get_settings()

    # Parse exempt IPs and paths from settings/env
    _EXEMPT_IPS: set[str] = {ip.strip() for ip in settings.rate_limit_exempt_ips.split(",") if ip.strip()}
    _EXEMPT_PATHS: set[str] = {p.strip() for p in settings.rate_limit_exempt_paths.split(",") if p.strip()}

    # Try to configure Redis as storage backend, fallback to memory
    storage_uri = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}" if settings else None

    # Global limiter instance for the application
    limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)

    def _skip_if_exempt(request) -> bool:
        """
        Return True to skip rate limiting when the request comes from an exempt IP or for exempt paths.
        """
        try:
            client_ip = request.client.host if getattr(request, "client", None) else None
            path = request.url.path if getattr(request, "url", None) else None
        except Exception:
            client_ip = None
            path = None
        if client_ip and client_ip in _EXEMPT_IPS:
            return True
        if path and path in _EXEMPT_PATHS:
            return True
        return False

    # Register the request filter to bypass limits for exempt IPs and paths
    limiter.request_filter(_skip_if_exempt)

    def setup_rate_limiter(app: FastAPI) -> None:
        """Wire slowapi into FastAPI app: state and exception handler."""
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

except Exception:
    # Fallback when slowapi is not available (e.g., during tests without dependency)
    class _DummyLimiter:
        def limit(self, _spec: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                return func

            return decorator

        def request_filter(self, _func: Callable[..., Any]) -> Callable[..., Any]:
            return _func

    limiter = _DummyLimiter()  # type: ignore

    def setup_rate_limiter(_app: Any) -> None:  # no-op for tests
        return
