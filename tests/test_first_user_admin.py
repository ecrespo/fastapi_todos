from fastapi.testclient import TestClient


def test_first_registered_user_is_admin_and_can_list_users(client: TestClient):
    # Register the first user
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "admin1", "password": "pw123", "confirm_password": "pw123"},
    )
    assert reg.status_code == 201, reg.text

    # Login with same credentials
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin1", "password": "pw123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    # The first user should have admin role; token should allow listing users
    resp = client.get("/api/v1/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "users" in data and isinstance(data["users"], list)
