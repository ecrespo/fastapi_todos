from __future__ import annotations

import asyncio
from typing import Dict, Any

from app.shared.celery_app import celery_app


@celery_app.task(name="todos.create_todo")
def create_todo_task(todo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task to create a Todo item using the same service logic as the API.
    Runs the async create flow in a fresh event loop. Returns a minimal payload.
    """
    # Import inside the task to avoid circular imports at module import time
    from app.api.v1 import todos as todos_module

    async def _run():
        # Reuse the API's internal function to ensure cache invalidation parity
        await todos_module._create_todo_internal(todo_data)

    asyncio.run(_run())
    return {"status": "ok", "id": todo_data.get("id")}
