from typing import List, Optional

from app.models.RequestsTodos import Todo  # type: ignore
from app.shared.db import get_async_connection


class TodoRepository:
    """Repository layer for CRUD operations on todos using aiosqlite."""

    async def get_all(self) -> List[Todo]:
        conn = await get_async_connection()
        try:
            async with conn.execute("SELECT id, item FROM todos ORDER BY id ASC") as cur:
                rows = await cur.fetchall()
                return [Todo(id=row[0], item=row[1]) for row in rows]
        finally:
            await conn.close()

    async def get_by_id(self, todo_id: int) -> Optional[Todo]:
        conn = await get_async_connection()
        try:
            async with conn.execute("SELECT id, item FROM todos WHERE id = ?", (todo_id,)) as cur:
                row = await cur.fetchone()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])
        finally:
            await conn.close()

    async def create(self, todo: Todo) -> None:
        conn = await get_async_connection()
        try:
            await conn.execute("INSERT INTO todos (id, item) VALUES (?, ?)", (todo.id, todo.item))
            await conn.commit()
        finally:
            await conn.close()

    async def update(self, todo_id: int, item: str) -> Optional[Todo]:
        conn = await get_async_connection()
        try:
            cur = await conn.execute("UPDATE todos SET item = ? WHERE id = ?", (item, todo_id))
            await conn.commit()
            if cur.rowcount == 0:
                return None
            async with conn.execute("SELECT id, item FROM todos WHERE id = ?", (todo_id,)) as cur2:
                row = await cur2.fetchone()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])
        finally:
            await conn.close()

    async def delete(self, todo_id: int) -> bool:
        conn = await get_async_connection()
        try:
            cur = await conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            await conn.commit()
            return cur.rowcount > 0
        finally:
            await conn.close()
