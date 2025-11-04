from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Security, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.shared.auth import admin_required, api_verifier
from app.shared.db import AuthTokenORM, RefreshTokenORM, UserORM, UserRole, get_async_session
from app.shared.jwt_utils import create_access_token, create_refresh_token
from app.shared.security import hash_password, verify_password
from app.shared.rate_limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    # Accept both 'user' and 'username' in payload; prefer 'username' internally
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(alias="user")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class CreateUserRequest(BaseModel):
    # Accept both 'user' and 'username' in payload; prefer 'username' internally
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(alias="user")
    password: str
    confirm_password: str


class CreatedUserResponse(BaseModel):
    id: int
    username: str
    role: str
    message: str = "user created"


@router.post("/register", response_model=CreatedUserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_user(payload: CreateUserRequest) -> CreatedUserResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    pwd_hash = hash_password(payload.password)
    async with await get_async_session() as session:
        # Determine role: first user becomes admin, others are viewers
        cnt_res = await session.execute(select(func.count()).select_from(UserORM))
        total_users = int(cnt_res.scalar_one() or 0)
        role = UserRole.admin if total_users == 0 else UserRole.viewer
        user = UserORM(username=payload.username, password_hash=pwd_hash, role=role, active=1)
        session.add(user)
        try:
            await session.commit()
            await session.refresh(user)
        except IntegrityError:
            # Likely unique constraint on username
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    return CreatedUserResponse(id=user.id, username=user.username, role=getattr(user.role, "value", str(user.role)))


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def login(payload: LoginRequest) -> TokenResponse:
    from app.shared.config import get_settings

    settings = get_settings()

    async with await get_async_session() as session:
        # Find active user by username
        res = await session.execute(
            select(UserORM.id, UserORM.username, UserORM.password_hash, UserORM.active, UserORM.role)
            .where(UserORM.username == payload.username)
            .limit(1)
        )
        row = res.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        user_id, username, password_hash, active, role = row
        if not active or not verify_password(payload.password, password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

        # Create JWT access token with user information
        role_str = getattr(role, "value", str(role))
        access_token = create_access_token(data={"sub": username, "user_id": user_id, "role": role_str})

        # Create refresh token
        refresh_token, expires_at = create_refresh_token(user_id)

        # Store only refresh token in database (JWT access tokens are self-contained)
        session.add(RefreshTokenORM(token=refresh_token, user_id=user_id, expires_at=expires_at, revoked=0))
        await session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,  # convert to seconds
        )


# ===== Users management endpoints =====
class UserSummary(BaseModel):
    id_user: int
    user: str
    role: str


class UsersListResponse(BaseModel):
    users: list[UserSummary]


class UpdateRoleRequest(BaseModel):
    role: UserRole


class MessageResponse(BaseModel):
    message: str


@router.get("/users", response_model=UsersListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def list_users(_: None = Depends(admin_required)) -> UsersListResponse:
    async with await get_async_session() as session:
        res = await session.execute(select(UserORM.id, UserORM.username, UserORM.role, UserORM.active))
        rows = res.all()
    items: list[UserSummary] = []
    for uid, username, role, active in rows:
        if not active:
            continue
        role_str = getattr(role, "value", str(role))
        items.append(UserSummary(id_user=uid, user=username, role=role_str))
    return UsersListResponse(users=items)


@router.get("/users/{user_id}", response_model=UserSummary, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute")
async def get_user(user_id: int, _: None = Depends(admin_required)) -> UserSummary:
    async with await get_async_session() as session:
        res = await session.execute(
            select(UserORM.id, UserORM.username, UserORM.role, UserORM.active).where(UserORM.id == user_id).limit(1)
        )
        row = res.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    uid, username, role, active = row
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    role_str = getattr(role, "value", str(role))
    return UserSummary(id_user=uid, user=username, role=role_str)


@router.patch("/users/{user_id}/role", response_model=UserSummary, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def update_user_role(user_id: int, payload: UpdateRoleRequest, _: None = Depends(admin_required)) -> UserSummary:
    async with await get_async_session() as session:
        res = await session.execute(select(UserORM).where(UserORM.id == user_id).limit(1))
        user = res.scalar_one_or_none()
        if not user or not user.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        user.role = payload.role
        await session.commit()
        await session.refresh(user)
        return UserSummary(id_user=user.id, user=user.username, role=getattr(user.role, "value", str(user.role)))


class UpdatePasswordRequest(BaseModel):
    password: str
    confirm_password: str


@router.patch("/users/{user_id}/password", response_model=MessageResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def update_user_password(
    user_id: int,
    payload: UpdatePasswordRequest,
    token: str = Security(api_verifier),
) -> MessageResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="passwords do not match")
    # Determine if caller is admin or is the same user
    async with await get_async_session() as session:
        # Find caller's user_id and role if any
        tok_res = await session.execute(
            select(AuthTokenORM.user_id).where(AuthTokenORM.token == token, AuthTokenORM.active == 1).limit(1)
        )
        tok_row = tok_res.first()
        caller_user_id = tok_row[0] if tok_row else None
        is_admin = False
        if caller_user_id is not None:
            ures = await session.execute(select(UserORM.role).where(UserORM.id == caller_user_id).limit(1))
            urow = ures.first()
            if urow:
                role = urow[0]
                role_str = getattr(role, "value", str(role)).lower()
                is_admin = role_str == "admin"
        else:
            # Legacy tokens without user are treated as admin-equivalent in this codebase
            is_admin = True

        if not is_admin and caller_user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")

        # Update target user's password
        res = await session.execute(select(UserORM).where(UserORM.id == user_id).limit(1))
        user = res.scalar_one_or_none()
        if not user or not user.active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
        user.password_hash = hash_password(payload.password)
        await session.commit()

    return MessageResponse(message="password updated")


# ===== Refresh token endpoint =====
class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def refresh_token_endpoint(payload: RefreshTokenRequest) -> TokenResponse:
    """Refresh an access token using a valid refresh token."""
    from app.shared.config import get_settings

    settings = get_settings()

    async with await get_async_session() as session:
        # Validate refresh token
        res = await session.execute(
            select(RefreshTokenORM.user_id, RefreshTokenORM.expires_at, RefreshTokenORM.revoked)
            .where(RefreshTokenORM.token == payload.refresh_token)
            .limit(1)
        )
        row = res.first()

        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user_id, expires_at_str, revoked = row

        # Check if token is revoked
        if revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has been revoked")

        # Check if token is expired
        expires_at = datetime.fromisoformat(expires_at_str) if isinstance(expires_at_str, str) else expires_at_str
        if datetime.now(UTC) > expires_at.replace(tzinfo=UTC):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token has expired")

        # Get user information
        user_res = await session.execute(
            select(UserORM.username, UserORM.role, UserORM.active).where(UserORM.id == user_id).limit(1)
        )
        user_row = user_res.first()

        if not user_row or not user_row[2]:  # Check active status
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        username, role, active = user_row
        role_str = getattr(role, "value", str(role))

        # Generate new access token
        access_token = create_access_token(data={"sub": username, "user_id": user_id, "role": role_str})

        # Generate new refresh token (rotate refresh tokens for security)
        new_refresh_token, new_expires_at = create_refresh_token(user_id)

        # Revoke old refresh token
        old_token_obj = await session.execute(
            select(RefreshTokenORM).where(RefreshTokenORM.token == payload.refresh_token)
        )
        old_token = old_token_obj.scalar_one_or_none()
        if old_token:
            old_token.revoked = 1

        # Store new refresh token (JWT access tokens are self-contained, no need to store)
        session.add(RefreshTokenORM(token=new_refresh_token, user_id=user_id, expires_at=new_expires_at, revoked=0))
        await session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
