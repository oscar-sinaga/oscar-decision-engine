"""Translate concurrent catalog duplicate inserts without hiding unrelated DB failures."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.domain.errors import ConflictError


async def flush_unique(session: AsyncSession, message: str) -> None:
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        if getattr(exc.orig, "sqlstate", None) == "23505":
            raise ConflictError(message) from exc
        raise
