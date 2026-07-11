"""p3 rule model v2

Revision ID: 8f3c2a1b7d04
Revises: 1864d7efc83f
Create Date: 2026-07-11
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "8f3c2a1b7d04"
down_revision: str | None = "1864d7efc83f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CATEGORIES = (
    "VALIDATION",
    "ELIGIBILITY",
    "AFFORDABILITY",
    "BUREAU",
    "FRAUD",
    "COLLATERAL",
    "LIMIT",
    "TENOR",
    "PRICING",
    "ROUTING",
    "FINAL_DECISION",
)


def _category_id(index: int) -> UUID:
    return UUID(f"30000000-0000-0000-0000-{index:012d}")


def upgrade() -> None:
    op.add_column(
        "rule_versions",
        sa.Column(
            "rule_kind",
            sa.String(length=20),
            server_default="POLICY_OUTCOME",
            nullable=False,
        ),
    )
    op.add_column("rule_versions", sa.Column("expression_text", sa.Text(), nullable=True))
    op.alter_column("rule_versions", "action_json", existing_type=sa.JSON(), nullable=True)
    op.add_column(
        "features",
        sa.Column("writable", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_table(
        "rule_categories",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rule_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_rule_categories_code")),
    )
    categories = sa.table(
        "rule_categories",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
    )
    op.bulk_insert(
        categories,
        [
            {"id": _category_id(index), "code": code, "label": code.replace("_", " ").title()}
            for index, code in enumerate(_CATEGORIES, start=1)
        ],
    )


def downgrade() -> None:
    op.drop_table("rule_categories")
    op.drop_column("features", "writable")
    op.execute("UPDATE rule_versions SET action_json = '{}'::jsonb WHERE action_json IS NULL")
    op.alter_column("rule_versions", "action_json", existing_type=sa.JSON(), nullable=False)
    op.drop_column("rule_versions", "expression_text")
    op.drop_column("rule_versions", "rule_kind")
