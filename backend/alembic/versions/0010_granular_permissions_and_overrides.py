"""Add user_permission_overrides table and staff_booking_auto_confirm column

Revision ID: 0010
Revises: 0009
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
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


def _has_table(connection, schema: str, table: str) -> bool:
    row = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :tbl"
        ),
        {"schema": schema, "tbl": table},
    ).fetchone()
    return row is not None


def _has_column(connection, schema: str, table: str, column: str) -> bool:
    row = connection.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :tbl "
            "AND column_name = :col"
        ),
        {"schema": schema, "tbl": table, "col": column},
    ).fetchone()
    return row is not None


def upgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if not _has_table(connection, schema, "user_permission_overrides"):
            op.create_table(
                "user_permission_overrides",
                sa.Column("user_id", sa.Uuid(), sa.ForeignKey(f"{schema}.users.id"), primary_key=True),
                sa.Column("permission_id", sa.Uuid(), sa.ForeignKey(f"{schema}.permissions.id"), primary_key=True),
                sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("true")),
                sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
                schema=schema,
            )
        if not _has_column(connection, schema, "resource_types", "staff_booking_auto_confirm"):
            op.add_column(
                "resource_types",
                sa.Column("staff_booking_auto_confirm", sa.Boolean(), nullable=False, server_default=sa.text("true")),
                schema=schema,
            )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if _has_column(connection, schema, "resource_types", "staff_booking_auto_confirm"):
            op.drop_column("resource_types", "staff_booking_auto_confirm", schema=schema)
        if _has_table(connection, schema, "user_permission_overrides"):
            op.drop_table("user_permission_overrides", schema=schema)
