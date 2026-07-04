"""Authentication/authorization FastAPI dependencies.

Authorization is enforced server-side on every protected route via
``require_permission``; frontend visibility is never a security boundary.
"""

import uuid
from typing import Annotated, Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.auth.security import decode_access_token
from app.shared.database import get_session
from app.shared.domain.errors import AuthenticationError, AuthorizationError
from app.shared.logging import get_logger

logger = get_logger("oscar.auth")

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except ValueError as exc:
        raise AuthenticationError("Invalid token subject") from exc
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise AuthenticationError("Unknown or inactive principal")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(permission_code: str) -> Any:
    """Route dependency: authenticated principal holding ``permission_code``.

    Returns ``Any`` so routes can declare ``user: User = require_permission(...)``.
    """

    async def _checker(user: CurrentUser) -> User:
        if permission_code not in user.permission_codes:
            logger.info(
                "auth.permission_denied",
                extra={"username": user.username, "permission": permission_code},
            )
            raise AuthorizationError(f"Missing permission: {permission_code}")
        return user

    return Depends(_checker)
