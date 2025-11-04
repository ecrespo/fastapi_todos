import inspect
from typing import Any

from app.models.RequestsTodos import Todo  # type: ignore
from app.repositories.todo_repository import TodoRepository


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


class TodoService:
    """
    Service layer for Todo-related business logic.

    Delegates to an async repository implemented with aiosqlite. It also
    tolerates a sync repository (used by some unit tests) by awaiting only
    when needed.
    """

    def __init__(self, repository: TodoRepository | None = None) -> None:
        self._repo = repository or TodoRepository()

    async def get_todos(self, page: int, size: int, user_id: int | None = None) -> tuple[list[Todo], int]:
        """
        Returns a slice of todos and the total count.
        If user_id is provided, restrict results to that user's todos.
        Falls back to the legacy get_all() repository method if a paginated
        method is not implemented by the repository (used by some unit tests).
        """
        offset = max(0, (page - 1) * size)
        # Prefer repo pagination if available
        get_paginated = getattr(self._repo, "get_paginated", None)
        if get_paginated is not None:
            return await _maybe_await(get_paginated(offset, size, user_id))
        # Fallback: load all then slice (and filter if needed)
        all_items: list[Todo] = await _maybe_await(self._repo.get_all())
        if user_id is not None:
            all_items = [t for t in all_items if getattr(t, "user_id", None) == user_id]
        total = len(all_items)
        return all_items[offset : offset + size], total

    async def get_todo(self, todo_id: int) -> Todo | None:
        return await _maybe_await(self._repo.get_by_id(todo_id))

    async def create_todo(self, todo: Todo) -> None:
        # Place for validations/business rules before persisting
        await _maybe_await(self._repo.create(todo))

    async def update_todo(self, todo_id: int, todo_obj: Todo) -> Todo | None:
        # Example: could validate item content, enforce constraints, etc.
        return await _maybe_await(self._repo.update(todo_id, todo_obj))

    async def delete_todo(self, todo_id: int) -> bool:
        return await _maybe_await(self._repo.delete(todo_id))
