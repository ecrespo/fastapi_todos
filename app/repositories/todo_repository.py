from typing import List, Optional
import sqlite3
from app.models.RequestsTodos import Todo # type: ignore
from app.shared.db import get_connection


class TodoRepository:
    """Repository layer for CRUD operations on todos using SQLite3."""

    def get_all(self) -> List[Todo]:
        conn = get_connection()
        try:
            rows = conn.execute("SELECT id, item FROM todos ORDER BY id ASC").fetchall()
            return [Todo(id=row[0], item=row[1]) for row in rows]
        finally:
            conn.close()

    def get_by_id(self, todo_id: int) -> Optional[Todo]:
        conn = get_connection()
        try:
            row = conn.execute("SELECT id, item FROM todos WHERE id = ?", (todo_id,)).fetchone()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])
        finally:
            conn.close()

    def create(self, todo: Todo) -> None:
        conn = get_connection()
        try:
            conn.execute("INSERT INTO todos (id, item) VALUES (?, ?)", (todo.id, todo.item))
            conn.commit()
        finally:
            conn.close()

    def update(self, todo_id: int, item: str) -> Optional[Todo]:
        conn = get_connection()
        try:
            cur = conn.execute("UPDATE todos SET item = ? WHERE id = ?", (item, todo_id))
            conn.commit()
            if cur.rowcount == 0:
                return None
            row = conn.execute("SELECT id, item FROM todos WHERE id = ?", (todo_id,)).fetchone()
            if row is None:
                return None
            return Todo(id=row[0], item=row[1])
        finally:
            conn.close()

    def delete(self, todo_id: int) -> bool:
        conn = get_connection()
        try:
            cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
