"""make password_hash nullable on tenant users table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    for schema in _get_tenant_schemas(connection):
        op.alter_column(
            "users",
            "password_hash",
            existing_type=sa.String(255),
            nullable=True,
            schema=schema,
        )


def downgrade() -> None:
    connection = op.get_bind()
    for schema in _get_tenant_schemas(connection):
        op.alter_column(
            "users",
            "password_hash",
            existing_type=sa.String(255),
            nullable=False,
            schema=schema,
        )
