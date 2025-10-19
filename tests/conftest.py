import os
import sys
import tempfile
import contextlib
from pathlib import Path
from typing import Generator


import pytest
from fastapi.testclient import TestClient


# Ensure project root is on sys.path for package imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.main import app
from app.shared import db as dbmod
from app.shared.db import init_db


@contextlib.contextmanager
def temp_db_path() -> Generator[str, None, None]:
    # Create a temp file path but let sqlite create it
    fd, path = tempfile.mkstemp(prefix="test_todos_", suffix=".db")
    os.close(fd)
    try:
        yield path
    finally:
        # Cleanup after tests
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    # Route the app to use a temp DB per test module (non-function scope to satisfy Hypothesis health check)
    with temp_db_path() as db_path:
        # Point the DB module to the temporary database file
        dbmod.DB_PATH = db_path
        # Initialize schema on the temp database
        init_db()
        # Seed a test token and return client with Authorization header
        conn = dbmod.get_connection()
        try:
            conn.execute("INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)", ("test-token", "pytest"))
            conn.commit()
        finally:
            conn.close()
        with TestClient(app, headers={"Authorization": "Bearer test-token"}) as c:
            yield c
