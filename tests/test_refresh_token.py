"""Test refresh token functionality."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.shared.db import init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize test database before each test."""
    import app.shared.db as db_module

    # Save original DB_PATH if it exists
    original_db_path = getattr(db_module, "DB_PATH", None)

    db_module.DB_PATH = ":memory:"
    init_db()
    yield
    # Cleanup after test
    if original_db_path is not None:
        db_module.DB_PATH = original_db_path


@pytest.mark.anyio
async def test_refresh_token_flow():
    """Test complete refresh token flow: register, login, refresh."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Register a user
        register_response = await client.post(
            "/api/v1/auth/register",
            json={"user": "testuser", "password": "testpass123", "confirm_password": "testpass123"},
        )
        assert register_response.status_code == 201
        assert register_response.json()["username"] == "testuser"

        # 2. Login to get tokens
        login_response = await client.post("/api/v1/auth/login", json={"user": "testuser", "password": "testpass123"})
        assert login_response.status_code == 200
        login_data = login_response.json()

        # Verify response structure
        assert "access_token" in login_data
        assert "refresh_token" in login_data
        assert "token_type" in login_data
        assert "expires_in" in login_data
        assert login_data["token_type"] == "bearer"
        assert login_data["expires_in"] > 0

        access_token = login_data["access_token"]
        refresh_token = login_data["refresh_token"]

        # 3. Verify access token works
        todos_response = await client.get("/api/v1/todos/", headers={"Authorization": f"Bearer {access_token}"})
        assert todos_response.status_code == 200

        # 4. Use refresh token to get new access token
        refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()

        # Verify new tokens received
        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        new_access_token = refresh_data["access_token"]
        new_refresh_token = refresh_data["refresh_token"]

        # New refresh token should be different (access token might be same if created in same second)
        assert new_refresh_token != refresh_token

        # 5. Verify new access token works
        todos_response2 = await client.get("/api/v1/todos/", headers={"Authorization": f"Bearer {new_access_token}"})
        assert todos_response2.status_code == 200

        # 6. Verify old refresh token is revoked (should fail)
        old_refresh_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert old_refresh_response.status_code == 401
        assert "revoked" in old_refresh_response.json()["detail"].lower()


@pytest.mark.anyio
async def test_refresh_token_invalid():
    """Test refresh with invalid token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid_token"})
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
