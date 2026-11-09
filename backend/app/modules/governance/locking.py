"""Transaction-scoped policy locks; runtime readers can proceed concurrently.

One namespace-wide writer lock is deliberately conservative for an internal
workbench. It prevents stale ORM state from defeating lifecycle checks and
prevents mixed configuration snapshots while runtime plans are built.
"""

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


async def lock_policy(session: AsyncSession, *entities: Any, shared: bool = False) -> None:
    statement = (
        "SELECT pg_advisory_xact_lock_shared(734927160208)"
        if shared
        else "SELECT pg_advisory_xact_lock(734927160208)"
    )
    await session.execute(text(statement))
    # Route handlers may have loaded these objects before waiting for the lock.
    for entity in entities:
        state = inspect(entity)
        names = [column.key for column in state.mapper.column_attrs]
        names.extend(rel.key for rel in state.mapper.relationships if rel.key not in state.unloaded)
        await session.refresh(entity, attribute_names=names)
