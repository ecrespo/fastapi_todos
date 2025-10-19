import sqlite3
from pathlib import Path
from typing import Tuple, Optional

import aiosqlite

from app.shared.config import get_settings

# Resolve DB path using settings and .env
_settings = get_settings()
DB_PATH: Path | str = _settings.db_path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS todos (
    id INTEGER PRIMARY KEY,
    item TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_tokens (
    token TEXT PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active INTEGER NOT NULL DEFAULT 1
);
"""

# Async connection singleton holder
_ASYNC_CONN: Optional[aiosqlite.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Create a new synchronous SQLite3 connection to the app database.

    Note: This is kept for backward compatibility (auth/tests). Prefer
    the async helpers for new code paths.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


async def get_async_connection() -> aiosqlite.Connection:
    """Return a singleton aiosqlite connection to the app database.

    The same connection instance is reused across calls within the process.
    Foreign keys are enabled on first initialization.
    """
    global _ASYNC_CONN
    if _ASYNC_CONN is None:
        _ASYNC_CONN = await aiosqlite.connect(str(DB_PATH))
        await _ASYNC_CONN.execute("PRAGMA foreign_keys = ON;")
    return _ASYNC_CONN


def init_db() -> None:
    """Ensure database file and schema exist (sync)."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


async def init_db_async() -> None:
    """Ensure database file and schema exist (async)."""
    conn = await get_async_connection()
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()


async def close_async_connection() -> None:
    """Close the singleton async connection if it exists."""
    global _ASYNC_CONN
    if _ASYNC_CONN is not None:
        try:
            await _ASYNC_CONN.close()
        finally:
            _ASYNC_CONN = None


def ensure_auth_token(name: str, token: str | None = None) -> tuple[str, bool]:
    """Ensure there is an active token row for the given name (sync).

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
    """Async variant of ensure_auth_token using the singleton connection."""
    import secrets

    conn = await get_async_connection()
    async with conn.execute(
        "SELECT token FROM auth_tokens WHERE name = ? AND active = 1 LIMIT 1",
        (name,),
    ) as cur:
        row = await cur.fetchone()
    if row is not None:
        return row[0], False
    token_value = token or secrets.token_urlsafe(32)
    await conn.execute(
        "INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)",
        (token_value, name),
    )
    await conn.commit()
    return token_value, True
