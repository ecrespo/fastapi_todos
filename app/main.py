from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.todos import router as todo_router
from app.shared.config import get_settings
from app.shared.db import init_db
from app.shared.LoggerSingleton import logger
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB on startup (uses settings internally)
    logger.info("Initializing database...")
    init_db()

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
