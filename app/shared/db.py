import sqlite3
from pathlib import Path
from app.shared.config import get_settings

# Resolve DB path using settings and .env
_settings = get_settings()
DB_PATH: Path = _settings.db_path

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
    """Create a new SQLite3 connection to the app database.

    Note: Caller is responsible for closing the connection.
    """
    # Support in-memory database via ":memory:"
    conn = sqlite3.connect(str(DB_PATH))
    # Return rows as tuples; repository will map them. Enable foreign keys if needed.
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Ensure database file and schema exist."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()


def ensure_auth_token(name: str, token: str | None = None) -> tuple[str, bool]:
    """Ensure there is an active token row for the given name.

    Returns a tuple (token_value, created_new) where created_new is True if we
    inserted a new token, False if one already existed.
    """
    import secrets

    conn = get_connection()
    try:
        # Try to find an existing active token for this name
        row = conn.execute(
            "SELECT token FROM auth_tokens WHERE name = ? AND active = 1 LIMIT 1",
            (name,),
        ).fetchone()
        if row is not None:
            return row[0], False
        # Create a new one
        token_value = token or secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)",
            (token_value, name),
        )
        conn.commit()
        return token_value, True
    finally:
        conn.close()
