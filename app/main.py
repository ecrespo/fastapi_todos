from fastapi import FastAPI

from app.api.v1.todos import router as todo_router


app = FastAPI(title="FastAPI Todos")

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
