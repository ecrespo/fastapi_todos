from typing import List, Optional
from datetime import datetime

from sqlalchemy import text

from app.models.RequestsTodos import Todo  # type: ignore
from app.shared.db import get_async_session


class TodoRepository:
    """Repository layer for CRUD operations on todos using SQLAlchemy AsyncSession.

    Connections are managed centrally at app shutdown.
    """

    async def get_all(self) -> List[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(text("SELECT id, item, status, created_at FROM todos ORDER BY id ASC"))
            rows = res.fetchall()
            return [
                Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]))
                for row in rows
            ]

    async def get_paginated(self, offset: int, limit: int) -> tuple[List[Todo], int]:
        """Return a page slice and the total count."""
        async with await get_async_session() as session:
            # Total count first
            res_total = await session.execute(text("SELECT COUNT(*) FROM todos"))
            total = int(res_total.scalar() or 0)
            if total == 0:
                return [], 0
            # Page slice
            res = await session.execute(
                text("SELECT id, item, status, created_at FROM todos ORDER BY id ASC LIMIT :limit OFFSET :offset"),
                {"limit": limit, "offset": offset},
            )
            rows = res.fetchall()
            items = [
                Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]))
                for row in rows
            ]
            return items, total

    async def get_by_id(self, todo_id: int) -> Optional[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(
                text("SELECT id, item, status, created_at FROM todos WHERE id = :id"),
                {"id": todo_id},
            )
            row = res.first()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]))

    async def create(self, todo: Todo) -> None:
        async with await get_async_session() as session:
            # created_at is server default; status provided or default at DB level
            await session.execute(
                text("INSERT INTO todos (id, item, status, user_id) VALUES (:id, :item, :status, :user_id)"),
                {
                    "id": todo.id,
                    "item": todo.item,
                    "status": getattr(todo.status, 'value', todo.status),
                    "user_id": todo.user_id,
                },
            )
            await session.commit()

    async def update(self, todo_id: int, todo: Todo) -> Optional[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(
                text("UPDATE todos SET item = :item, status = :status WHERE id = :id"),
                {"item": todo.item, "status": getattr(todo.status, 'value', todo.status), "id": todo_id},
            )
            await session.commit()
            if (res.rowcount or 0) == 0:
                return None
            res2 = await session.execute(
                text("SELECT id, item, status, created_at FROM todos WHERE id = :id"),
                {"id": todo_id},
            )
            row = res2.first()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]))

    async def delete(self, todo_id: int) -> bool:
        async with await get_async_session() as session:
            res = await session.execute(text("DELETE FROM todos WHERE id = :id"), {"id": todo_id})
            await session.commit()
            return (res.rowcount or 0) > 0


def _parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # SQLite may return string timestamps via text() selection; attempt parse
    try:
        # Common SQLite CURRENT_TIMESTAMP format: YYYY-MM-DD HH:MM:SS
        return datetime.fromisoformat(str(value))
    except Exception:
        return None
