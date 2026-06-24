"""add operating_hours and buffer_minutes to resource_types

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
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


def _has_column(connection, schema: str, column: str) -> bool:
    row = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = 'resource_types' "
            "AND column_name = :col"
        ),
        {"schema": schema, "col": column},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if not _has_column(connection, schema, "operating_hours"):
            op.add_column(
                "resource_types",
                sa.Column("operating_hours", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
                schema=schema,
            )
        if not _has_column(connection, schema, "buffer_minutes"):
            op.add_column(
                "resource_types",
                sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
                schema=schema,
            )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        op.drop_column("resource_types", "buffer_minutes", schema=schema)
        op.drop_column("resource_types", "operating_hours", schema=schema)
