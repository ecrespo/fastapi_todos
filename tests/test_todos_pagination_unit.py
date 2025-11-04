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

    # Old interface still supported
    def get_all(self) -> list[Todo]:
        todos: list[Todo] = []
        for k in sorted(self._store.keys()):
            item, status, created_at = self._store[k]
            todos.append(Todo(id=k, item=item, status=status, created_at=created_at))
        return todos

    # New optional interface (not implemented here to test service fallback path)
    # def get_paginated(self, offset: int, limit: int) -> tuple[List[Todo], int]:
    #     ...

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
    # Seed 25 items to exercise pagination logic via service fallback
    for i in range(1, 26):
        repo.create(Todo(id=i, item=f"item-{i}"))

    service = TodoService(repository=repo)
    # Replace module-level service used by the router
    monkeypatch.setattr(todos_module, "service", service, raising=True)
    return service


@pytest.fixture()
def unit_client(mocked_service) -> TestClient:  # type: ignore[override]
    # Use a temp DB and seed an auth token; keep router's service monkeypatched
    fd, path = tempfile.mkstemp(prefix="unit_test_todos_pagination_", suffix=".db")
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


def test_pagination_happy_path(unit_client: TestClient):
    # Request page 2 of size 10 -> items 11..20
    res = unit_client.get("/api/v1/todos/?page=2&size=10")
    assert res.status_code == 200
    data = res.json()
    assert "todos" in data
    assert "pagination" in data

    todos = data["todos"]
    meta = data["pagination"]

    assert len(todos) == 10
    assert [t["id"] for t in todos] == list(range(11, 21))

    assert meta["total"] == 25
    assert meta["page"] == 2
    assert meta["size"] == 10
    assert meta["pages"] == 3


def test_pagination_last_page_partial(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/?page=3&size=10")
    assert res.status_code == 200
    data = res.json()
    todos = data["todos"]
    meta = data["pagination"]
    assert len(todos) == 5
    assert [t["id"] for t in todos] == list(range(21, 26))
    assert meta["total"] == 25
    assert meta["pages"] == 3


def test_pagination_out_of_range(unit_client: TestClient):
    res = unit_client.get("/api/v1/todos/?page=99&size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["todos"] == []
    meta = data["pagination"]
    assert meta["total"] == 25
    assert meta["page"] == 99
    assert meta["size"] == 10
    assert meta["pages"] == 3


def test_pagination_validation(unit_client: TestClient):
    # Invalid page should 422
    res1 = unit_client.get("/api/v1/todos/?page=0&size=10")
    assert res1.status_code == 422
    # Invalid size should 422
    res2 = unit_client.get("/api/v1/todos/?page=1&size=0")
    assert res2.status_code == 422
    # Too large size should 422
    res3 = unit_client.get("/api/v1/todos/?page=1&size=1000")
    assert res3.status_code == 422
