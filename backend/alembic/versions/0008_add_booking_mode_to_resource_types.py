"""add booking_mode to resource_types

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-21
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
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
        has_col = connection.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = :schema AND table_name = 'resource_types' "
                "AND column_name = 'booking_mode'"
            ),
            {"schema": schema},
        ).fetchone()
        if not has_col:
            op.add_column(
                "resource_types",
                sa.Column("booking_mode", sa.String(20), nullable=False, server_default="both"),
                schema=schema,
            )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        op.drop_column("resource_types", "booking_mode", schema=schema)
