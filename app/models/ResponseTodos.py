from pydantic import BaseModel

from app.models.RequestsTodos import Todo


class Pagination(BaseModel):
    total: int
    page: int
    size: int
    pages: int


class TodosBase(BaseModel):
    todos: list[Todo]


class PaginatedTodos(BaseModel):
    todos: list[Todo]
    pagination: Pagination


class TodoResponse(BaseModel):
    todo: Todo


class MessageResponse(BaseModel):
    message: str


class TaskEnqueuedResponse(BaseModel):
    message: str
    task_id: str
