from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.shared.config import get_settings


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Dictionary containing the token payload (e.g., user_id, username)
        expires_delta: Optional custom expiration time; defaults to settings value

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "access"})

    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    return encoded_jwt


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    """Create a refresh token.

    Args:
        user_id: The user ID for which to create the refresh token

    Returns:
        Tuple of (token string, expiration datetime)
    """
    settings = get_settings()
    # Generate a random secure token
    token = secrets.token_urlsafe(32)

    # Calculate expiration
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    return token, expires_at


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify and decode a JWT token.

    Args:
        token: The JWT token string to verify

    Returns:
        Decoded token payload if valid, None otherwise
    """
    settings = get_settings()

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except InvalidTokenError:
        return None


def get_token_user_id(token: str) -> int | None:
    """Extract user_id from a JWT token.

    Args:
        token: The JWT token string

    Returns:
        User ID if present in token, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None
    return payload.get("user_id")


def get_token_username(token: str) -> str | None:
    """Extract username from a JWT token.

    Args:
        token: The JWT token string

    Returns:
        Username if present in token, None otherwise
    """
    payload = verify_token(token)
    if payload is None:
        return None
    return payload.get("sub")
