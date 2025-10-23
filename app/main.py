import os
from contextlib import asynccontextmanager
from fastapi_mcp import FastApiMCP
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from secure import Secure


from app.shared.rate_limiter import setup_rate_limiter, limiter
from app.api.v1.todos import router as todo_router
from app.api.v1.auth import router as auth_router
from app.shared.config import get_settings, Environment
from app.shared.db import init_db_async, ensure_auth_token_async, close_async_connection
from app.shared.LoggerSingleton import logger
from app.middlewares import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    ProcessTimeHeaderMiddleware,
)
from redis import asyncio as aioredis
from app.shared.redis_settings import get_redis_client


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup (uses settings internally)
    logger.info("Initializing database...")
    await init_db_async()
    # Ensure a default auth token exists for CRUD of todos
    env_token = os.getenv("AUTH_DEFAULT_TOKEN")
    token_value, created = await ensure_auth_token_async(name="auth_crud_todos", token=env_token)
    if created and env_token is None:
        # Log only if we generated it (not if provided via env)
        logger.info("Created default auth token for 'auth_crud_todos'. Token: %s", token_value)
    yield
    # On shutdown, close the async DB singleton connection if open
    await close_async_connection()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
mcp = FastApiMCP(
    app,
    include_operations=["get_todos","create_todo","get_todo","update_todo"])
mcp.mount()

# Setup SlowAPI rate limiter and exception handler
setup_rate_limiter(app)

# Middlewares
# Trusted hosts: allow all by default; customize via settings if needed
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Redirect to HTTPS only in production to avoid affecting local/dev/tests
if settings.environment == Environment.prod:
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS settings: permissive defaults for tutorial/demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware)

# Custom middleware: logging and timing
app.add_middleware(LoggingMiddleware, logger=logger)
app.add_middleware(ProcessTimeHeaderMiddleware)

# Error handling (outermost)
app.add_middleware(ErrorHandlingMiddleware, logger=logger)

# Secure headers (outermost)
secure = Secure.with_default_headers()

@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    # Apply recommended security headers
    await secure.set_headers_async(response)
    # Relax Content-Security-Policy to allow FastAPI docs (Swagger UI and ReDoc) assets
    # These pages load scripts and styles from trusted CDNs and use small inline scripts.
    csp = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "img-src 'self' data: https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.redoc.ly; "
        "connect-src 'self'; "
        "frame-ancestors 'self'; "
        "form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


@app.get("/healthcheck")
@limiter.limit("5/minute")
async def health_check():
    """
    Handles the health check endpoint which verifies the application's
    basic status and readiness. This function provides a simple mechanism
    to ensure the application is operational.

    Returns:
        dict: A dictionary containing the current operational status.
    """
    return {"status": "ok"}



@app.get("/redis-check")
async def test_redis(redis_client: aioredis.Redis = Depends(get_redis_client)):
    # Set a value with a 60-second expiration
    await redis_client.set("my_key", "hello", ex=60)
    # Get the value back
    value = await redis_client.get("my_key")
    return {"my_key": value}

app.include_router(todo_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
