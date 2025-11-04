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
    repo.create(Todo(id=10, item="seed"))

    service = TodoService(repository=repo)
    # Replace module-level service used by the router
    monkeypatch.setattr(todos_module, "service", service, raising=True)
    return service


@pytest.fixture()
def unit_client(mocked_service, monkeypatch) -> TestClient:  # type: ignore[override]
    # Force Celery to run tasks eagerly for unit tests
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")

    # Use a temp DB and seed an auth token; keep router's service monkeypatched
    fd, path = tempfile.mkstemp(prefix="unit_test_todos_celery_", suffix=".db")
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


def test_async_create_enqueues_and_creates(unit_client: TestClient):
    # Post to async endpoint
    res = unit_client.post("/api/v1/todos/async", json={"id": 11, "item": "async-item"})
    assert res.status_code == 202
    body = res.json()
    assert body["message"].lower() in {"enqueued", "accepted", "queued"}
    assert "task_id" in body and isinstance(body["task_id"], str) and len(body["task_id"]) > 0

    # Because Celery is eager in tests, the item should already exist
    res_get = unit_client.get("/api/v1/todos/11")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "todo" in data
    todo = data["todo"]
    assert todo["id"] == 11
    assert todo["item"] == "async-item"
    assert "status" in todo
    assert "created_at" in todo
