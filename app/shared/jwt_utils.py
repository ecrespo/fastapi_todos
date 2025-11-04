from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from jwt.exceptions import InvalidTokenError

from app.shared.config import get_settings


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token.

    Args:
        token: The JWT token string to verify

    Returns:
        Decoded token payload if valid, None otherwise
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except InvalidTokenError:
        return None


def get_token_user_id(token: str) -> Optional[int]:
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


def get_token_username(token: str) -> Optional[str]:
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
