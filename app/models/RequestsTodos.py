from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.shared.db import TodoStatus


def _normalize_status(value):
    if isinstance(value, str):
        # Accept both "pending" and "TodoStatus.pending" forms
        if value.startswith("TodoStatus."):
            value = value.split(".", 1)[1]
        try:
            return TodoStatus(value)
        except Exception:
            return value
    return value


class Todo(BaseModel):
    id: int
    item: str
    status: TodoStatus = TodoStatus.pending
    created_at: Optional[datetime] = None
    user_id: Optional[int] = None

    @field_validator("status", mode="before")
    @classmethod
    def coerce_status(cls, v):
        return _normalize_status(v)