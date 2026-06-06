"""add_schedules_to_booking

Revision ID: fafbaa33c76c
Revises: 0006
Create Date: 2026-06-06 14:09:06.629019
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'fafbaa33c76c'
down_revision: str | None = '0006'
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
            'bookings',
            sa.Column('schedules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=schema,
        )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        op.drop_column('bookings', 'schedules', schema=schema)
