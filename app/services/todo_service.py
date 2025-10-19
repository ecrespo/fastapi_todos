from typing import Any, Dict, List, Optional

from app.models.RequestsTodos import Todo # type: ignore
from app.repositories.todo_repository import TodoRepository

class TodoService:
    """
    Service layer for Todo-related business logic.

    This layer orchestrates access to the repository and is intended to host
    domain rules, validations, aggregations, and cross-cutting concerns.
    For now, it delegates directly to the repository to keep behavior
    unchanged while establishing a clean separation from the routing layer.
    """

    def __init__(self, repository: Optional[TodoRepository] = None) -> None:
        self._repo = repository or TodoRepository()

    def get_todos(self) -> List[Todo]:
        return self._repo.get_all()

    def get_todo(self, todo_id: int) -> Optional[Todo]:
        return self._repo.get_by_id(todo_id)

    def create_todo(self, todo: Todo) -> None:
        # Place for validations/business rules before persisting
        self._repo.create(todo)

    def update_todo(self, todo_id: int, todo_obj: Todo) -> Optional[Todo]:
        # Example: could validate item content, enforce constraints, etc.
        return self._repo.update(todo_id, todo_obj.item)

    def delete_todo(self, todo_id: int) -> bool:
        return self._repo.delete(todo_id)
