import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


from app.api.v1.todos import router as todo_router
from app.shared.config import get_settings, Environment
from app.shared.db import init_db, ensure_auth_token
from app.shared.LoggerSingleton import logger
from app.middlewares import (
    ErrorHandlingMiddleware,
LoggingMiddleware,
ProcessTimeHeaderMiddleware
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup (uses settings internally)
    logger.info("Initializing database...")
    init_db()
    # Ensure a default auth token exists for CRUD of todos
    env_token = os.getenv("AUTH_DEFAULT_TOKEN")
    token_value, created = ensure_auth_token(name="auth_crud_todos", token=env_token)
    if created and env_token is None:
        # Log only if we generated it (not if provided via env)
        logger.info("Created default auth token for 'auth_crud_todos'. Token: %s", token_value)
    yield
    # Add any shutdown cleanup here if needed


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

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
app.add_middleware(LoggingMiddleware)
app.add_middleware(ProcessTimeHeaderMiddleware)

# Error handling (outermost)
app.add_middleware(ErrorHandlingMiddleware)



@app.get("/healthcheck")
async def health_check():
    """
    Handles the health check endpoint which verifies the application's
    basic status and readiness. This function provides a simple mechanism
    to ensure the application is operational.

    Returns:
        dict: A dictionary containing the current operational status.
    """
    return {"status": "ok"}

app.include_router(todo_router)
