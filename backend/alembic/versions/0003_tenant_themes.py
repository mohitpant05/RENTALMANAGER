"""add tenant_themes table

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_themes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("brand", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("colors", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("typography", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("components", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("features", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tenant_themes_tenant_id", "tenant_themes", ["tenant_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_tenant_themes_tenant_id")
    op.drop_table("tenant_themes")
