from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def eager_env(monkeypatch):
    # Ensure Celery runs eagerly for integration test too (no RabbitMQ needed)
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    yield


def test_async_create_integration(client: TestClient, eager_env):  # type: ignore[override]
    # Use shared client fixture (with DB + auth)
    res = client.post("/api/v1/todos/async", json={"id": 42, "item": "demo-item-async"})
    assert res.status_code == 202
    data = res.json()
    assert data["message"].lower() in {"enqueued", "accepted", "queued"}
    assert "task_id" in data and isinstance(data["task_id"], str)

    # Since eager, the item should already be persisted
    res_get = client.get("/api/v1/todos/42")
    assert res_get.status_code == 200
    body = res_get.json()
    assert "todo" in body
    todo = body["todo"]
    assert todo["id"] == 42
    assert todo["item"] == "demo-item-async"
    # Verify additional model fields are present
    assert "status" in todo
    assert "created_at" in todo
