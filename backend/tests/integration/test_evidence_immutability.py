"""Database-level append-only evidence guard regression tests."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditLog
from app.modules.decisions.models import DecisionTrace
from app.shared.database.session import get_sessionmaker
from tests.integration.test_decision_runtime import lease_back_motor_payload, submit


@pytest.mark.parametrize("operation", ("UPDATE", "DELETE", "TRUNCATE"))
@pytest.mark.parametrize("table", ("audit_logs", "decision_traces"))
async def test_evidence_tables_reject_mutations(
    db_client: AsyncClient, operation: str, table: str
) -> None:
    created = await submit(db_client, lease_back_motor_payload())
    assert created.status_code == 201
    async with get_sessionmaker()() as session:
        if table == "audit_logs":
            row = await session.scalar(select(AuditLog).order_by(AuditLog.created_at.desc()))
        else:
            row = await session.scalar(
                select(DecisionTrace).order_by(DecisionTrace.created_at.desc())
            )
        assert row is not None
        if operation == "UPDATE":
            stmt = text(f"UPDATE {table} SET created_at = created_at WHERE id = :id")
        elif operation == "DELETE":
            stmt = text(f"DELETE FROM {table} WHERE id = :id")
        else:
            stmt = text(f"TRUNCATE TABLE {table}")
        with pytest.raises(DBAPIError):
            await session.execute(stmt, {"id": row.id})
        await session.rollback()
