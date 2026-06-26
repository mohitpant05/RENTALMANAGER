"""Add demo_slot_blocks table

Revision ID: 0015
Revises: 0014
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_slot_blocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slot_time", sa.Time(), nullable=False),
        sa.Column("specific_date", sa.Date(), nullable=True),
        sa.Column(
            "action",
            sa.Enum("block", "unblock", name="demoslotblockactionenum"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slot_time", "specific_date", name="uq_slot_block_time_date"),
    )


def downgrade() -> None:
    op.drop_table("demo_slot_blocks")
    op.execute("DROP TYPE IF EXISTS demoslotblockactionenum")
