from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import (
    Enum as SAEnum,
    String,
    Integer,
    DateTime,
    Text,
    text,
)
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.shared.config import get_settings

# Resolve DB path using settings and .env
_settings = get_settings()
DB_PATH: Path | str = _settings.db_path


def _build_database_url(db_path: Path | str) -> str:
    # Support ':memory:' and file paths
    if isinstance(db_path, Path):
        return f"sqlite+aiosqlite:///{db_path}"
    if str(db_path) == ":memory:":
        return "sqlite+aiosqlite://"
    # Any other string assume file path
    return f"sqlite+aiosqlite:///{db_path}"

DATABASE_URL: str = _build_database_url(DB_PATH)


class Base(DeclarativeBase):
    pass


class TodoStatus(str, Enum):
    start = "start"
    in_process = "in_process"
    pending = "pending"
    done = "done"
    cancel = "cancel"


class TodoORM(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[str]] = mapped_column(
        DateTime,
        server_default=text("'2025-10-19 00:00:00'"),
        nullable=False,
    )
    status: Mapped[TodoStatus] = mapped_column(SAEnum(TodoStatus, name="todo_status"), nullable=False, server_default=text("'pending'"))


class AuthTokenORM(Base):
    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[Optional[str]] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    active: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


# Async SQLAlchemy engine/session
_engine: Optional[AsyncEngine] = None
_SessionFactory: Optional[sessionmaker] = None


def _ensure_engine() -> tuple[AsyncEngine, sessionmaker]:
    global _engine, _SessionFactory
    if _engine is None:
        # Build URL from the current DB_PATH instead of the module-time constant to honor test overrides
        db_url = _build_database_url(DB_PATH)
        _engine = create_async_engine(db_url, future=True)
        _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)
    assert _SessionFactory is not None
    return _engine, _SessionFactory


async def get_async_session() -> AsyncSession:
    _, factory = _ensure_engine()
    return factory()


def get_connection() -> sqlite3.Connection:
    """Backward-compatible sync sqlite3 connection for tests/auth seeding."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Create tables if they do not exist using SQLAlchemy metadata (sync entrypoint).

    Note: SQLAlchemy async engine is used under the hood via run_sync.
    Also resets the async engine to honor any runtime changes to DB_PATH (used in tests).
    """
    import asyncio
    global _engine, _SessionFactory
    # Reset engine/session so that re-pointing DB_PATH takes effect
    _engine = None
    _SessionFactory = None

    async def _create_all() -> None:
        engine, _ = _ensure_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_all())


async def init_db_async() -> None:
    engine, _ = _ensure_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_async_connection() -> None:
    """Dispose the async engine if created."""
    global _engine
    if _engine is not None:
        try:
            await _engine.dispose()
        finally:
            _engine = None


def ensure_auth_token(name: str, token: str | None = None) -> tuple[str, bool]:
    """Ensure there is an active token row for the given name (sync).

    Uses sqlite3 for compatibility with existing tests which seed/read tokens synchronously.
    Returns (token_value, created_new).
    """
    import secrets

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT token FROM auth_tokens WHERE name = ? AND active = 1 LIMIT 1",
            (name,),
        ).fetchone()
        if row is not None:
            return row[0], False
        token_value = token or secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)",
            (token_value, name),
        )
        conn.commit()
        return token_value, True
    finally:
        conn.close()


async def ensure_auth_token_async(name: str, token: str | None = None) -> Tuple[str, bool]:
    """Async variant implemented with AsyncSession/SQLAlchemy."""
    import secrets

    _, factory = _ensure_engine()
    async with factory() as session:
        # Check existing
        res = await session.execute(text("SELECT token FROM auth_tokens WHERE name = :name AND active = 1 LIMIT 1"), {"name": name})
        row = res.first()
        if row is not None:
            return row[0], False
        token_value = token or secrets.token_urlsafe(32)
        await session.execute(
            text("INSERT INTO auth_tokens (token, name, active) VALUES (:token, :name, 1)"),
            {"token": token_value, "name": name},
        )
        await session.commit()
        return token_value, True
