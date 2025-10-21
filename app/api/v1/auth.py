from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.shared.db import get_async_session, UserORM, AuthTokenORM, UserRole
from app.shared.security import verify_password, hash_password

router = APIRouter(prefix="/auth", tags=["auth"]) 


class LoginRequest(BaseModel):
    # Accept both 'user' and 'username' in payload; prefer 'username' internally
    model_config = ConfigDict(populate_by_name=True)
    username: str = Field(alias="user")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
async def register_user(payload: CreateUserRequest) -> CreatedUserResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")

    pwd_hash = hash_password(payload.password)
    async with (await get_async_session()) as session:
        user = UserORM(username=payload.username, password_hash=pwd_hash, role=UserRole.viewer, active=1)
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
async def login(payload: LoginRequest) -> TokenResponse:
    async with (await get_async_session()) as session:
        # Find active user by username
        res = await session.execute(
            select(UserORM.id, UserORM.password_hash, UserORM.active).where(UserORM.username == payload.username).limit(1)
        )
        row = res.first()
        if not row:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        user_id, password_hash, active = row
        if not active or not verify_password(payload.password, password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
        # Issue a token and persist it linked to the user
        token = uuid4().hex
        session.add(AuthTokenORM(token=token, name=f"user:{payload.username}", user_id=user_id, active=1))
        await session.commit()
        return TokenResponse(access_token=token)
