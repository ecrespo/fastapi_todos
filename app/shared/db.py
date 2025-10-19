import sqlite3
from pathlib import Path
from typing import Tuple

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

def get_connection() -> sqlite3.Connection:
    """Create a new synchronous SQLite3 connection to the app database.

    Note: This is kept for backward compatibility (auth/tests). Prefer
    the async helpers for new code paths.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


async def get_async_connection() -> aiosqlite.Connection:
    """Create a new aiosqlite connection to the app database.

    Caller should not reuse across threads. Foreign keys are enabled.
    """
    conn = await aiosqlite.connect(str(DB_PATH))
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn


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
    try:
        await conn.executescript(SCHEMA_SQL)
        await conn.commit()
    finally:
        await conn.close()


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
    """Async variant of ensure_auth_token."""
    import secrets

    conn = await get_async_connection()
    try:
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
    finally:
        await conn.close()
