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


from typing import Sequence
from fastapi import Depends
from sqlalchemy import select
from app.shared.db import UserORM


def role_required(allowed_roles: Sequence[str]):
    """Return a FastAPI dependency that ensures the caller has one of the allowed roles.

    Backward compatibility: tokens without an associated user_id are treated as admin-equivalent.
    """
    allowed = set(r.lower() for r in allowed_roles)

    async def _checker(token: str = Security(api_verifier)) -> None:  # type: ignore[override]
        # Look up token -> user_id, then fetch user's role
        async with (await get_async_session()) as session:
            tok = await session.execute(
                select(AuthTokenORM.user_id).where(
                    AuthTokenORM.token == token,
                    AuthTokenORM.active == 1,
                ).limit(1)
            )
            row = tok.first()
            user_id = row[0] if row else None
            # Legacy tokens (no user) are allowed (treated as admin) to not break existing flows/tests
            if user_id is None:
                return
            ures = await session.execute(
                select(UserORM.role, UserORM.active).where(UserORM.id == user_id).limit(1)
            )
            urow = ures.first()
        if not urow:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        role, active = urow
        # Extract comparable string from enum or plain string
        role_str = getattr(role, "value", str(role)).lower()
        if not active or role_str not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return None

    return _checker


# Common role dependencies
editor_required = role_required(["editor", "admin"])
admin_required = role_required(["admin"]) 


async def is_admin_token(token: str) -> bool:
    """Return True if the token belongs to an active admin user.
    Legacy tokens without user binding are treated as admin for backward compatibility.
    """
    async with (await get_async_session()) as session:
        tok = await session.execute(
            select(AuthTokenORM.user_id).where(
                AuthTokenORM.token == token,
                AuthTokenORM.active == 1,
            ).limit(1)
        )
        row = tok.first()
        user_id = row[0] if row else None
        if user_id is None:
            return True
        ures = await session.execute(
            select(UserORM.role, UserORM.active).where(UserORM.id == user_id).limit(1)
        )
        urow = ures.first()
    if not urow:
        return False
    role, active = urow
    role_str = getattr(role, "value", str(role)).lower()
    return bool(active) and role_str == "admin"


async def get_user_id_for_token(token: str) -> Optional[int]:
    """Return the user_id associated to a token if present and active; otherwise None.

    Legacy tokens without user binding will return None.
    """
    async with (await get_async_session()) as session:
        result = await session.execute(
            select(AuthTokenORM.user_id).where(
                AuthTokenORM.token == token,
                AuthTokenORM.active == 1,
            ).limit(1)
        )
        row = result.first()
    return row[0] if row else None
