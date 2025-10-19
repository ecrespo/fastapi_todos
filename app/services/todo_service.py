from typing import List, Optional, Any
import inspect

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

    def __init__(self, repository: Optional[TodoRepository] = None) -> None:
        self._repo = repository or TodoRepository()

    async def get_todos(self) -> List[Todo]:
        return await _maybe_await(self._repo.get_all())

    async def get_todo(self, todo_id: int) -> Optional[Todo]:
        return await _maybe_await(self._repo.get_by_id(todo_id))

    async def create_todo(self, todo: Todo) -> None:
        # Place for validations/business rules before persisting
        await _maybe_await(self._repo.create(todo))

    async def update_todo(self, todo_id: int, todo_obj: Todo) -> Optional[Todo]:
        # Example: could validate item content, enforce constraints, etc.
        return await _maybe_await(self._repo.update(todo_id, todo_obj))

    async def delete_todo(self, todo_id: int) -> bool:
        return await _maybe_await(self._repo.delete(todo_id))
