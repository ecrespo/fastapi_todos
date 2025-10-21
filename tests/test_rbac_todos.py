from fastapi.testclient import TestClient

from app.shared import db as dbmod
from app.shared.security import hash_password


def seed_user(username: str, password: str, role: str) -> None:
    conn = dbmod.get_connection()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, 1)",
            (username, hash_password(password), role),
        )
        conn.commit()
    finally:
        conn.close()


def login(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def test_rbac_enforcement_on_todos(client: TestClient):
    # Seed three users with different roles
    seed_user("viewy", "pw", "viewer")
    seed_user("ed", "pw", "editor")
    seed_user("root", "pw", "admin")

    token_view = login(client, "viewy", "pw")
    token_edit = login(client, "ed", "pw")
    token_admin = login(client, "root", "pw")

    # Viewer should not create
    resp = client.post(
        "/api/v1/todos/",
        json={"id": 9001, "item": "nope"},
        headers={"Authorization": f"Bearer {token_view}"},
    )
    assert resp.status_code in (401, 403)

    # Editor can create
    resp2 = client.post(
        "/api/v1/todos/",
        json={"id": 9002, "item": "ok"},
        headers={"Authorization": f"Bearer {token_edit}"},
    )
    assert resp2.status_code == 200

    # Editor can update but not delete
    resp3 = client.put(
        "/api/v1/todos/9002",
        json={"id": 9002, "item": "updated"},
        headers={"Authorization": f"Bearer {token_edit}"},
    )
    assert resp3.status_code == 200

    resp4 = client.delete(
        "/api/v1/todos/9002",
        headers={"Authorization": f"Bearer {token_edit}"},
    )
    assert resp4.status_code in (401, 403)

    # Admin can delete
    resp5 = client.delete(
        "/api/v1/todos/9002",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert resp5.status_code == 200

    # Legacy default token from fixture should still be allowed to create
    resp6 = client.post(
        "/api/v1/todos/",
        json={"id": 9003, "item": "legacy"},
        # fixture provides Authorization header with test-token by default
    )
    assert resp6.status_code == 200
