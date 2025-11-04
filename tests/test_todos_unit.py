from __future__ import annotations

import os
import tempfile
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import app.api.v1.todos as todos_module
from app.main import app
from app.models.RequestsTodos import Todo
from app.services.todo_service import TodoService
from app.shared import db as dbmod
from app.shared.db import init_db


class MockRepository:
    def __init__(self) -> None:
        # store maps id to a tuple (item, status, created_at)
        self._store: dict[int, tuple[str, str, datetime]] = {}

    # Repository interface
    def get_all(self) -> list[Todo]:
        todos: list[Todo] = []
        for k in sorted(self._store.keys()):
            item, status, created_at = self._store[k]
            todos.append(Todo(id=k, item=item, status=status, created_at=created_at))
        return todos

    def get_by_id(self, todo_id: int) -> Todo | None:
        if todo_id in self._store:
            item, status, created_at = self._store[todo_id]
            return Todo(id=todo_id, item=item, status=status, created_at=created_at)
        return None

    def create(self, todo: Todo) -> None:
        self._store[todo.id] = (todo.item, str(todo.status), todo.created_at or datetime.now())

    def update(self, todo_id: int, todo: Todo) -> Todo | None:
        if todo_id not in self._store:
            return None
        _, _, created_at = self._store[todo_id]
        self._store[todo_id] = (todo.item, str(todo.status), created_at)
        return Todo(id=todo_id, item=todo.item, status=todo.status, created_at=created_at)

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
            conn.execute(
                "INSERT INTO auth_tokens (token, name, active) VALUES (?, ?, 1)", ("test-token", "pytest-unit")
            )
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
    todos = data["todos"]
    assert isinstance(todos, list)
    assert len(todos) == 2
    assert todos[0]["id"] == 1
    assert todos[0]["item"] == "alpha"
    assert "status" in todos[0]
    assert "created_at" in todos[0]
    assert todos[1]["id"] == 2
    assert todos[1]["item"] == "beta"
    assert "status" in todos[1]
    assert "created_at" in todos[1]


def test_get_single_todo_found(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/1")
    assert res.status_code == 200
    data = res.json()
    assert "todo" in data
    todo = data["todo"]
    assert todo["id"] == 1
    assert todo["item"] == "alpha"
    assert "status" in todo
    assert "created_at" in todo


def test_get_single_todo_not_found(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/999")
    assert res.status_code == 200
    assert res.json() == {"message": "Not todo found!"}


def test_create_todo(unit_client: TestClient):
    res = unit_client.post("/api/v1/todos/", json={"id": 3, "item": "gamma"})
    assert res.status_code == 200
    assert res.json() == {"message": "Todo has been created successfully!"}
    # Verify it appears in list with new fields present
    res2 = unit_client.get("/api/v1/todos/3")
    data = res2.json()
    assert "todo" in data
    todo = data["todo"]
    assert todo["id"] == 3
    assert todo["item"] == "gamma"
    assert "status" in todo
    assert "created_at" in todo


def test_update_todo_found(unit_client: TestClient):
    res = unit_client.put("/api/v1/todos/2", json={"id": 2, "item": "beta-upd"})
    assert res.status_code == 200
    data = res.json()
    assert "todo" in data
    todo = data["todo"]
    assert todo["id"] == 2
    assert todo["item"] == "beta-upd"
    assert "status" in todo
    assert "created_at" in todo


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
