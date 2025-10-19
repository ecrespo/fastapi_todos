from pydantic import BaseModel
from app.models.RequestsTodos import Todo


class TodosBase(BaseModel):
    todos: list[Todo]
