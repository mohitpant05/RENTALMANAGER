"""add hold_config to resource_types

Revision ID: 0007
Revises: fafbaa33c76c
Create Date: 2026-06-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007"
down_revision: str | None = "fafbaa33c76c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _get_tenant_schemas(connection) -> list[str]:
    result = connection.execute(
        sa.text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name LIKE 'tenant_%'"
        )
    )
    return [row[0] for row in result]


def upgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        op.add_column(
            "resource_types",
            sa.Column("hold_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=schema,
        )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        op.drop_column("resource_types", "hold_config", schema=schema)
