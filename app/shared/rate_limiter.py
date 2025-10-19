import os
from typing import Set, Callable, Any

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from fastapi import FastAPI

    # Comma-separated list of IPs that should be exempt from rate limiting
    # Example: RATE_LIMIT_EXEMPT_IPS="127.0.0.1,192.168.1.10"
    _EXEMPT_IPS: Set[str] = {
        ip.strip() for ip in os.getenv("RATE_LIMIT_EXEMPT_IPS", "").split(",") if ip.strip()
    }

    # Global limiter instance for the application
    limiter = Limiter(key_func=get_remote_address)

    def _skip_if_exempt(request) -> bool:
        """
        Return True to skip rate limiting when the request comes from an exempt IP.
        """
        try:
            client_ip = request.client.host if getattr(request, "client", None) else None
        except Exception:
            client_ip = None
        return bool(client_ip and client_ip in _EXEMPT_IPS)

    # Register the request filter to bypass limits for exempt IPs
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
