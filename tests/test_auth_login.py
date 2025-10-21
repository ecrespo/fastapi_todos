from fastapi.testclient import TestClient

from app.shared import db as dbmod
from app.shared.security import hash_password  # will be implemented


def test_login_success_and_token_works(client: TestClient):
    # Seed a user directly in the test DB
    conn = dbmod.get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, 1)",
            ("alice", hash_password("s3cret"), "editor"),
        )
        conn.commit()
    finally:
        conn.close()

    # Login with the seeded user
    resp = client.post("/api/v1/auth/login", json={"username": "alice", "password": "s3cret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data and isinstance(data["access_token"], str) and data["access_token"]
    assert data.get("token_type") == "bearer"

    # Use the received token to access a protected endpoint
    token = data["access_token"]
    resp2 = client.get("/api/v1/todos/", headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200


def test_login_invalid_credentials(client: TestClient):
    # No such user
    resp = client.post("/api/v1/auth/login", json={"username": "nobody", "password": "nope"})
    assert resp.status_code == 401
    assert resp.json().get("detail") in {"Invalid username or password", "Unauthorized"}
