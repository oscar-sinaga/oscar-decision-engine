"""Add request fingerprints and database-enforced append-only evidence.

Revision ID: c1e5f09a64d2
Revises: f4b7c9d2e601
"""

import sqlalchemy as sa
from alembic import op

revision: str = "c1e5f09a64d2"
down_revision: str | None = "f4b7c9d2e601"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("request_fingerprint", sa.String(64), nullable=True))
    # Historical idempotency keys are intentionally NOT backfilled from masked snapshots:
    # original request bytes and caller scope are unavailable, so replay must return 409.
    op.execute("""
        CREATE FUNCTION oscar_reject_evidence_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'OSCAR evidence records are append-only'
              USING ERRCODE = '42501';
        END;
        $$;
    """)
    for table in ("decision_traces", "audit_logs"):
        op.execute(f"""
            CREATE TRIGGER oscar_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION oscar_reject_evidence_change();
        """)
        op.execute(f"""
            CREATE TRIGGER oscar_{table}_no_truncate
            BEFORE TRUNCATE ON {table}
            FOR EACH STATEMENT EXECUTE FUNCTION oscar_reject_evidence_change();
        """)


def downgrade() -> None:
    for table in ("audit_logs", "decision_traces"):
        op.execute(f"DROP TRIGGER IF EXISTS oscar_{table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS oscar_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS oscar_reject_evidence_change()")
    op.drop_column("decisions", "request_fingerprint")
