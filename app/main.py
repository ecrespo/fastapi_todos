import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.todos import router as todo_router
from app.shared.config import get_settings, Environment
from app.shared.db import init_db, ensure_auth_token
from app.shared.LoggerSingleton import logger
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
