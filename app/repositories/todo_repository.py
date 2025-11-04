from datetime import datetime
from time import perf_counter

from sqlalchemy import text

from app.models.RequestsTodos import Todo  # type: ignore
from app.shared.db import get_async_session
from app.shared.metrics import (
    db_connection_attempts_total,
    db_sessions_in_use,
    db_queries_total,
    db_query_duration_seconds,
)


class TodoRepository:
    """Repository layer for CRUD operations on todos using SQLAlchemy AsyncSession.

    Connections are managed centrally at app shutdown.
    """

    async def get_all(self) -> list[Todo]:
        db_connection_attempts_total.labels(result="success").inc()
        async with await get_async_session() as session:
            db_sessions_in_use.inc()
            try:
                stmt = "SELECT id, item, status, created_at, user_id FROM todos ORDER BY id ASC"
                start = perf_counter()
                res = await session.execute(text(stmt))
                duration = perf_counter() - start
                db_queries_total.labels(statement="SELECT", result="success").inc()
                db_query_duration_seconds.labels(statement="SELECT", result="success").observe(duration)
                rows = res.fetchall()
                return [
                    Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]), user_id=row[4])
                    for row in rows
                ]
            except Exception:
                db_queries_total.labels(statement="SELECT", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()

    async def get_paginated(self, offset: int, limit: int, user_id: int | None = None) -> tuple[list[Todo], int]:
        """Return a page slice and the total count.
        If user_id is provided, restrict results to that user's todos.
        """
        try:
            session_cm = await get_async_session()
            db_connection_attempts_total.labels(result="success").inc()
        except Exception:
            db_connection_attempts_total.labels(result="failure").inc()
            raise
        async with session_cm as session:
            db_sessions_in_use.inc()
            try:
                # Total count first (filtered if user_id provided)
                if user_id is not None:
                    start = perf_counter()
                    res_total = await session.execute(
                        text("SELECT COUNT(*) FROM todos WHERE user_id = :user_id"),
                        {"user_id": user_id},
                    )
                    db_queries_total.labels(statement="SELECT", result="success").inc()
                    db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                else:
                    start = perf_counter()
                    res_total = await session.execute(text("SELECT COUNT(*) FROM todos"))
                    db_queries_total.labels(statement="SELECT", result="success").inc()
                    db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                total = int(res_total.scalar() or 0)
                if total == 0:
                    return [], 0
                # Page slice
                if user_id is not None:
                    stmt = (
                        "SELECT id, item, status, created_at, user_id FROM todos WHERE user_id = :user_id ORDER BY id ASC LIMIT :limit OFFSET :offset"
                    )
                    start = perf_counter()
                    res = await session.execute(
                        text(stmt),
                        {"limit": limit, "offset": offset, "user_id": user_id},
                    )
                    db_queries_total.labels(statement="SELECT", result="success").inc()
                    db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                else:
                    stmt = (
                        "SELECT id, item, status, created_at, user_id FROM todos ORDER BY id ASC LIMIT :limit OFFSET :offset"
                    )
                    start = perf_counter()
                    res = await session.execute(
                        text(stmt),
                        {"limit": limit, "offset": offset},
                    )
                    db_queries_total.labels(statement="SELECT", result="success").inc()
                    db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                rows = res.fetchall()
                items = [
                    Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]), user_id=row[4])
                    for row in rows
                ]
                return items, total
            except Exception:
                db_queries_total.labels(statement="SELECT", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()

    async def get_by_id(self, todo_id: int) -> Todo | None:
        db_connection_attempts_total.labels(result="success").inc()
        async with await get_async_session() as session:
            db_sessions_in_use.inc()
            try:
                stmt = "SELECT id, item, status, created_at, user_id FROM todos WHERE id = :id"
                start = perf_counter()
                res = await session.execute(
                    text(stmt),
                    {"id": todo_id},
                )
                db_queries_total.labels(statement="SELECT", result="success").inc()
                db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                row = res.first()
                if row is None:
                    return None
                return Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]), user_id=row[4])
            except Exception:
                db_queries_total.labels(statement="SELECT", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()

    async def create(self, todo: Todo) -> None:
        db_connection_attempts_total.labels(result="success").inc()
        async with await get_async_session() as session:
            db_sessions_in_use.inc()
            try:
                stmt = "INSERT INTO todos (id, item, status, user_id) VALUES (:id, :item, :status, :user_id)"
                start = perf_counter()
                await session.execute(
                    text(stmt),
                    {
                        "id": todo.id,
                        "item": todo.item,
                        "status": getattr(todo.status, "value", todo.status),
                        "user_id": todo.user_id,
                    },
                )
                db_queries_total.labels(statement="INSERT", result="success").inc()
                db_query_duration_seconds.labels(statement="INSERT", result="success").observe(perf_counter() - start)
                await session.commit()
            except Exception:
                db_queries_total.labels(statement="INSERT", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()

    async def update(self, todo_id: int, todo: Todo) -> Todo | None:
        db_connection_attempts_total.labels(result="success").inc()
        async with await get_async_session() as session:
            db_sessions_in_use.inc()
            try:
                upd_stmt = "UPDATE todos SET item = :item, status = :status WHERE id = :id"
                start = perf_counter()
                res = await session.execute(
                    text(upd_stmt),
                    {"item": todo.item, "status": getattr(todo.status, "value", todo.status), "id": todo_id},
                )
                db_queries_total.labels(statement="UPDATE", result="success").inc()
                db_query_duration_seconds.labels(statement="UPDATE", result="success").observe(perf_counter() - start)
                await session.commit()
                if (res.rowcount or 0) == 0:
                    return None
                sel_stmt = "SELECT id, item, status, created_at, user_id FROM todos WHERE id = :id"
                start = perf_counter()
                res2 = await session.execute(
                    text(sel_stmt),
                    {"id": todo_id},
                )
                db_queries_total.labels(statement="SELECT", result="success").inc()
                db_query_duration_seconds.labels(statement="SELECT", result="success").observe(perf_counter() - start)
                row = res2.first()
                if row is None:
                    return None
                return Todo(id=row[0], item=row[1], status=row[2], created_at=_parse_dt(row[3]), user_id=row[4])
            except Exception:
                # On any exception, increment generic failure counter
                db_queries_total.labels(statement="UPDATE", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()

    async def delete(self, todo_id: int) -> bool:
        db_connection_attempts_total.labels(result="success").inc()
        async with await get_async_session() as session:
            db_sessions_in_use.inc()
            try:
                stmt = "DELETE FROM todos WHERE id = :id"
                start = perf_counter()
                res = await session.execute(text(stmt), {"id": todo_id})
                db_queries_total.labels(statement="DELETE", result="success").inc()
                db_query_duration_seconds.labels(statement="DELETE", result="success").observe(perf_counter() - start)
                await session.commit()
                return (res.rowcount or 0) > 0
            except Exception:
                db_queries_total.labels(statement="DELETE", result="failure").inc()
                raise
            finally:
                db_sessions_in_use.dec()


def _parse_dt(value) -> datetime | None:
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
