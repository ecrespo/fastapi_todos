from fastapi.testclient import TestClient


def test_register_then_login(client: TestClient):
    # Register a new user
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "juan", "password": "pw123", "confirm_password": "pw123"},
    )
    assert reg.status_code == 201, reg.text
    data = reg.json()
    assert data["username"] == "juan"

    # Login with same credentials
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "juan", "password": "pw123"},
    )
    assert login.status_code == 200, login.text
    tok = login.json()["access_token"]
    assert tok
