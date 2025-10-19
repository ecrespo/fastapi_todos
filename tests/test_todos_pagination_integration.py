from __future__ import annotations

from fastapi.testclient import TestClient
import pytest


def _create_many(client: TestClient, n: int, start: int = 1) -> None:
    for i in range(start, start + n):
        resp = client.post("/api/v1/todos/", json={"id": i, "item": f"task-{i}"})
        assert resp.status_code == 200


@pytest.mark.usefixtures("client")
def test_integration_pagination_happy(client: TestClient):
    _create_many(client, 23)

    # Page 1 size 10
    r1 = client.get("/api/v1/todos/?page=1&size=10")
    assert r1.status_code == 200
    d1 = r1.json()
    assert len(d1["todos"]) == 10
    assert [t["id"] for t in d1["todos"]] == list(range(1, 11))
    assert d1["pagination"]["total"] == 23
    assert d1["pagination"]["pages"] == 3

    # Page 2 size 10
    r2 = client.get("/api/v1/todos/?page=2&size=10")
    assert r2.status_code == 200
    d2 = r2.json()
    assert len(d2["todos"]) == 10
    assert [t["id"] for t in d2["todos"]] == list(range(11, 21))

    # Page 3 size 10 -> last 3
    r3 = client.get("/api/v1/todos/?page=3&size=10")
    assert r3.status_code == 200
    d3 = r3.json()
    assert len(d3["todos"]) == 3
    assert [t["id"] for t in d3["todos"]] == [21, 22, 23]


@pytest.mark.usefixtures("client")
def test_integration_pagination_validation(client: TestClient):
    _create_many(client, 2, start=1001)
    # page and size bounds
    assert client.get("/api/v1/todos/?page=0&size=10").status_code == 422
    assert client.get("/api/v1/todos/?page=1&size=0").status_code == 422
    assert client.get("/api/v1/todos/?page=1&size=1000").status_code == 422
