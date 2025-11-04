from fastapi.testclient import TestClient


def test_healthcheck(client: TestClient):
    # Prefer using the shared client fixture for DB setup, though DB not required here
    resp = client.get("/healthcheck")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
