"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.models import User
from app.modules.auth.security import create_access_token, verify_password
from app.shared.database import get_session
from app.shared.domain.errors import AuthenticationError
from app.shared.logging import get_logger

logger = get_logger("oscar.auth")

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    username: str
    full_name: str
    roles: list[str]
    permissions: list[str]


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoginResponse:
    user = await session.scalar(select(User).where(User.username == body.username))
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.hashed_password)
    ):
        logger.info("auth.login_failed", extra={"username": body.username})
        raise AuthenticationError("Invalid credentials")
    logger.info("auth.login_succeeded", extra={"username": user.username})
    return LoginResponse(access_token=create_access_token(str(user.id), actor_type=user.actor_type))


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(
        username=user.username,
        full_name=user.full_name,
        roles=sorted(user.role_codes),
        permissions=sorted(user.permission_codes),
    )
