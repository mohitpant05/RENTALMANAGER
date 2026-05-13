"""add preferred_currency to users

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
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
    # public.users
    op.add_column(
        "users",
        sa.Column(
            "preferred_currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        schema="public",
    )

    # tenant schemas
    connection = op.get_bind()
    for schema in _get_tenant_schemas(connection):
        op.add_column(
            "users",
            sa.Column(
                "preferred_currency",
                sa.String(3),
                nullable=False,
                server_default=sa.text("'USD'"),
            ),
            schema=schema,
        )


def downgrade() -> None:
    op.drop_column("users", "preferred_currency", schema="public")

    connection = op.get_bind()
    for schema in _get_tenant_schemas(connection):
        op.drop_column("users", "preferred_currency", schema=schema)
