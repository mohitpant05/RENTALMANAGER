"""Add demo_requests table

Revision ID: 0014
Revises: 0013
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "demo_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("message", sa.String(length=2000), nullable=True),
        sa.Column("slot_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "completed", "cancelled", name="demorequeststatusenum"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", "slot_start", name="uq_demo_email_slot"),
    )
    op.create_index("ix_demo_requests_email", "demo_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_demo_requests_email", table_name="demo_requests")
    op.drop_table("demo_requests")
    op.execute("DROP TYPE IF EXISTS demorequeststatusenum")
