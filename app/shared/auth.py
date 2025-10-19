from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, Header, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from sqlalchemy import select
from app.shared.db import get_async_session, AuthTokenORM

def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    """Extract token from Authorization header.

    Supports values like:
    - "Bearer <token>"
    - "<token>" (raw token, for convenience/tests)
    """
    if not authorization:
        return None
    auth = authorization.strip()
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # Allow raw token without scheme for simplicity in tests
    return auth


class APIVerifier:
    """
    APIVerifier class for verifying Bearer tokens via the Authorization header.

    Uses FastAPI Security with HTTPBearer to extract the token and validates it
    against the auth_tokens table. Returns the verified token if valid, raises
    401 otherwise.
    """

    def __init__(self) -> None:
        # Security scheme for Bearer tokens. auto_error=False so we can return 401 ourselves.
        self._http_bearer = HTTPBearer(auto_error=False)

    def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Security(lambda: None),  # placeholder, replaced below for mypy
    ) -> str: ...


# Workaround for proper FastAPI Security injection while keeping type hints clear
# We expose a single instance with Security bound to the scheme so FastAPI injects credentials.
_http_bearer_scheme = HTTPBearer(auto_error=False)

class _APIVerifier(APIVerifier):
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Security(_http_bearer_scheme)) -> str:  # type: ignore[override]
        if credentials is None or not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = credentials.credentials

        # Validate token against the configured database (SQLite, Postgres, etc.) using SQLAlchemy AsyncSession
        async with (await get_async_session()) as session:
            result = await session.execute(
                select(AuthTokenORM.token).where(
                    AuthTokenORM.token == token,
                    AuthTokenORM.active == 1,
                ).limit(1)
            )
            row = result.first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token


# Export a ready-to-use APIVerifier instance
api_verifier = _APIVerifier()


async def require_auth(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
) -> str:
    """FastAPI dependency that validates a bearer token against the DB (async).

    Extracts the token from the Authorization header and validates it against
    the auth_tokens table using SQLAlchemy AsyncSession. Returns the validated
    token string on success. Raises 401 otherwise.
    """
    token = _extract_bearer_token(authorization)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with (await get_async_session()) as session:
        result = await session.execute(
            select(AuthTokenORM.token).where(
                AuthTokenORM.token == token,
                AuthTokenORM.active == 1,
            ).limit(1)
        )
        row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
