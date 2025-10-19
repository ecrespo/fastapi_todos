from typing import List, Optional

from sqlalchemy import text

from app.models.RequestsTodos import Todo  # type: ignore
from app.shared.db import get_async_session


class TodoRepository:
    """Repository layer for CRUD operations on todos using SQLAlchemy AsyncSession.

    Connections are managed centrally at app shutdown.
    """

    async def get_all(self) -> List[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(text("SELECT id, item FROM todos ORDER BY id ASC"))
            rows = res.fetchall()
            return [Todo(id=row[0], item=row[1]) for row in rows]

    async def get_by_id(self, todo_id: int) -> Optional[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(text("SELECT id, item FROM todos WHERE id = :id"), {"id": todo_id})
            row = res.first()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])

    async def create(self, todo: Todo) -> None:
        async with await get_async_session() as session:
            await session.execute(
                text("INSERT INTO todos (id, item) VALUES (:id, :item)"),
                {"id": todo.id, "item": todo.item},
            )
            await session.commit()

    async def update(self, todo_id: int, item: str) -> Optional[Todo]:
        async with await get_async_session() as session:
            res = await session.execute(
                text("UPDATE todos SET item = :item WHERE id = :id"),
                {"item": item, "id": todo_id},
            )
            await session.commit()
            if res.rowcount == 0:
                return None
            res2 = await session.execute(text("SELECT id, item FROM todos WHERE id = :id"), {"id": todo_id})
            row = res2.first()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])

    async def delete(self, todo_id: int) -> bool:
        async with await get_async_session() as session:
            res = await session.execute(text("DELETE FROM todos WHERE id = :id"), {"id": todo_id})
            await session.commit()
            return (res.rowcount or 0) > 0
