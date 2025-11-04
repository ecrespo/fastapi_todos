from __future__ import annotations

from celery import Celery

from app.shared.config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    app = Celery(
        "fastapi_todos",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "app.tasks.todo_tasks",
        ],
    )
    # Configure eager mode for tests if requested via env/settings
    app.conf.task_always_eager = bool(settings.celery_task_always_eager)
    app.conf.task_eager_propagates = True
    # JSON serialization for safety
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    # Ensure the worker retries connecting to the broker on startup to avoid race with RabbitMQ readiness
    app.conf.broker_connection_retry_on_startup = True
    return app


# Singleton celery app
celery_app: Celery = create_celery_app()
