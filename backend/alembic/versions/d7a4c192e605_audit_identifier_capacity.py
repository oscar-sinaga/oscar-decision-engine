"""Keep full valid feature/model/strategy identifiers in immutable audit records.

Revision ID: d7a4c192e605
Revises: c1e5f09a64d2
"""

import sqlalchemy as sa

from alembic import op

revision: str = "d7a4c192e605"
down_revision: str | None = "c1e5f09a64d2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.alter_column("audit_logs", "entity_id", type_=sa.String(256), existing_type=sa.String(150))
    op.alter_column(
        "audit_logs", "entity_version", type_=sa.String(256), existing_type=sa.String(50)
    )


def downgrade() -> None:
    # Never truncate immutable evidence in order to make a downgrade succeed.
    op.execute("LOCK TABLE audit_logs IN ACCESS EXCLUSIVE MODE")
    too_long = op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM audit_logs "
            "WHERE length(entity_id) > 150 OR length(entity_version) > 50)"
        )
    )
    if too_long:
        raise RuntimeError("Cannot narrow audit identifiers without losing existing evidence")
    op.alter_column(
        "audit_logs", "entity_version", type_=sa.String(50), existing_type=sa.String(256)
    )
    op.alter_column("audit_logs", "entity_id", type_=sa.String(150), existing_type=sa.String(256))
