from __future__ import annotations

from typing import Dict, List, Optional
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.RequestsTodos import Todo
from app.services.todo_service import TodoService
import app.api.v1.todos as todos_module
from app.shared import db as dbmod
from app.shared.db import init_db


class MockRepository:
    def __init__(self) -> None:
        self._store: Dict[int, str] = {}

    # Repository interface
    def get_all(self) -> List[Todo]:
        return [Todo(id=k, item=v) for k, v in sorted(self._store.items())]

    def get_by_id(self, todo_id: int) -> Optional[Todo]:
        if todo_id in self._store:
            return Todo(id=todo_id, item=self._store[todo_id])
        return None

    def create(self, todo: Todo) -> None:
        self._store[todo.id] = todo.item

    def update(self, todo_id: int, item: str) -> Optional[Todo]:
        if todo_id not in self._store:
            return None
        self._store[todo_id] = item
        return Todo(id=todo_id, item=item)

    def delete(self, todo_id: int) -> bool:
        return self._store.pop(todo_id, None) is not None


@pytest.fixture()
def mocked_service(monkeypatch):
    repo = MockRepository()
    # Seed some data
    repo.create(Todo(id=1, item="alpha"))
    repo.create(Todo(id=2, item="beta"))

    service = TodoService(repository=repo)
    # Replace module-level service used by the router
    monkeypatch.setattr(todos_module, "service", service, raising=True)
    return service


@pytest.fixture()
def unit_client(mocked_service) -> TestClient:  # type: ignore[override]
    # Use a temp DB and seed an auth token; keep router's service monkeypatched
    fd, path = tempfile.mkstemp(prefix="unit_test_todos_", suffix=".db")
    os.close(fd)
    try:
        dbmod.DB_PATH = path
        init_db()
        conn = dbmod.get_connection()
        try:
            conn.execute("INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)", ("test-token", "pytest-unit"))
            conn.commit()
        finally:
            conn.close()
        client = TestClient(app, headers={"Authorization": "Bearer test-token"})
        yield client
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def test_get_all_todos(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/")
    assert res.status_code == 200
    data = res.json()
    assert "todos" in data
    assert data["todos"] == [
        {"id": 1, "item": "alpha"},
        {"id": 2, "item": "beta"},
    ]


def test_get_single_todo_found(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/1")
    assert res.status_code == 200
    assert res.json() == {"todo": {"id": 1, "item": "alpha"}}


def test_get_single_todo_not_found(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/999")
    assert res.status_code == 200
    assert res.json() == {"message": "Not todo found!"}


def test_create_todo(unit_client: TestClient):
    res = unit_client.post("/api/v1/todos/", json={"id": 3, "item": "gamma"})
    assert res.status_code == 200
    assert res.json() == {"message": "Todo has been created successfully!"}
    # Verify it appears in list
    res2 = unit_client.get("/api/v1/todos/3")
    assert res2.json() == {"todo": {"id": 3, "item": "gamma"}}


def test_update_todo_found(unit_client: TestClient):
    res = unit_client.put("/api/v1/todos/2", json={"id": 2, "item": "beta-upd"})
    assert res.status_code == 200
    assert res.json() == {"todo": {"id": 2, "item": "beta-upd"}}


def test_update_todo_not_found(unit_client: TestClient):
    res = unit_client.put("/api/v1/todos/999", json={"id": 999, "item": "nope"})
    assert res.status_code == 200
    assert res.json() == {"message": "Not todo found!"}


def test_delete_todo_found(unit_client: TestClient):
    res = unit_client.delete("/api/v1/todos/1")
    assert res.status_code == 200
    assert res.json() == {"message": "Todo has been deleted successfully!"}


def test_delete_todo_not_found(unit_client: TestClient):
    res = unit_client.delete("/api/v1/todos/999")
    assert res.status_code == 200
    assert res.json() == {"message": "Not todo found!"}
