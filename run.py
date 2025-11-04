import os

import uvicorn


def main() -> None:
    """
    Start the FastAPI app using uvicorn, pointing to fastapi_project.main:app.

    Environment variables (optional):
      - HOST: bind address (default: 0.0.0.0)
      - PORT: port number (default: 8000)
      - WORKERS: number of worker processes (default: 1)
      - RELOAD: enable auto-reload on file changes (default: true)

    Note: Uvicorn does not support reload with workers > 1. If RELOAD is true,
    workers will be forced to 1.
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    workers = int(os.getenv("WORKERS", "1"))
    reload_flag = os.getenv("RELOAD", "true").strip().lower() in {"1", "true", "yes", "on"}

    # Ensure compatibility: reload requires a single worker
    if reload_flag and workers != 1:
        workers = 1

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload_flag,
        workers=workers,
        factory=False,
    )


if __name__ == "__main__":
    main()
