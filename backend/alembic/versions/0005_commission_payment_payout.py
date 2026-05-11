"""add commission, payment, payout tables and columns

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
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
    for schema in _get_tenant_schemas(connection):
        # --- resource_types: commission_config ---
        op.add_column(
            "resource_types",
            sa.Column("commission_config", sa.JSON, nullable=True),
            schema=schema,
        )

        # --- resources: commission_config + suspension_reason ---
        op.add_column(
            "resources",
            sa.Column("commission_config", sa.JSON, nullable=True),
            schema=schema,
        )
        op.add_column(
            "resources",
            sa.Column("suspension_reason", sa.String(50), nullable=True),
            schema=schema,
        )

        # --- bookings: commission financial fields ---
        op.add_column(
            "bookings",
            sa.Column("service_fee", sa.Float, nullable=False, server_default=sa.text("0.0")),
            schema=schema,
        )
        op.add_column(
            "bookings",
            sa.Column("platform_commission", sa.Float,
                      nullable=False,
                      server_default=sa.text("0.0")),
            schema=schema,
        )
        op.add_column(
            "bookings",
            sa.Column("owner_payout", sa.Float, nullable=False, server_default=sa.text("0.0")),
            schema=schema,
        )
        op.add_column(
            "bookings",
            sa.Column("customer_total", sa.Float, nullable=False, server_default=sa.text("0.0")),
            schema=schema,
        )

        # --- payments table ---
        op.create_table(
            "payments",
            sa.Column("id", sa.Uuid, nullable=False),
            sa.Column("booking_id", sa.Uuid, nullable=False, index=True),
            sa.Column("amount", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("currency", sa.String(10), nullable=False, server_default=sa.text("'USD'")),
            sa.Column("provider", sa.String(20),
                      nullable=False,
                      server_default=sa.text("'manual'")),
            sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("provider_ref", sa.String(255), nullable=True),
            sa.Column("provider_data", sa.JSON, nullable=True),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("refund_amount", sa.Float, nullable=True),
            sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            schema=schema,
        )

        # --- payouts table ---
        op.create_table(
            "payouts",
            sa.Column("id", sa.Uuid, nullable=False),
            sa.Column("owner_id", sa.Uuid, nullable=False, index=True),
            sa.Column("amount", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("currency", sa.String(10), nullable=False, server_default=sa.text("'USD'")),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
            sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
            sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("settled_by", sa.Uuid, nullable=True),
            sa.Column("provider_ref", sa.String(255), nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            schema=schema,
        )

        # --- payout_items table ---
        op.create_table(
            "payout_items",
            sa.Column("id", sa.Uuid, nullable=False),
            sa.Column("payout_id", sa.Uuid, nullable=False, index=True),
            sa.Column("booking_id", sa.Uuid, nullable=False, index=True),
            sa.Column("booking_total", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("commission", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.Column("owner_amount", sa.Float, nullable=False, server_default=sa.text("0.0")),
            sa.PrimaryKeyConstraint("id"),
            schema=schema,
        )


def downgrade() -> None:
    connection = op.get_bind()
    for schema in _get_tenant_schemas(connection):
        op.drop_table("payout_items", schema=schema)
        op.drop_table("payouts", schema=schema)
        op.drop_table("payments", schema=schema)
        op.drop_column("bookings", "customer_total", schema=schema)
        op.drop_column("bookings", "owner_payout", schema=schema)
        op.drop_column("bookings", "platform_commission", schema=schema)
        op.drop_column("bookings", "service_fee", schema=schema)
        op.drop_column("resources", "suspension_reason", schema=schema)
        op.drop_column("resources", "commission_config", schema=schema)
        op.drop_column("resource_types", "commission_config", schema=schema)
