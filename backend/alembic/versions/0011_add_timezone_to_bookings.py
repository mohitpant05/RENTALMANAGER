"""Add timezone column to bookings

Revision ID: 0011
Revises: 0010
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
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


def _has_column(connection, schema: str, table: str, column: str) -> bool:
    result = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :table AND column_name = :column"
        ),
        {"schema": schema, "table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if not _has_column(connection, schema, "bookings", "timezone"):
            op.add_column(
                "bookings",
                sa.Column("timezone", sa.String(50), server_default="UTC", nullable=False),
                schema=schema,
            )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if _has_column(connection, schema, "bookings", "timezone"):
            op.drop_column("bookings", "timezone", schema=schema)
