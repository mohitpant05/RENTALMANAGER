# backend/alembic/versions/0013_add_manager_id_and_lister_permissions.py
"""Add manager_id to users and new permission domains

Revision ID: 0013
Revises: 0012
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSIONS = [
    ("customers:*:read", "Read customer list"),
    ("customers:*:create", "Create customers"),
    ("customers:*:manage", "Manage customers"),
    ("customers:*:deactivate", "Deactivate customers"),
    ("listers:*:invite", "Invite listers"),
    ("listers:*:read", "Read listers"),
    ("listers:*:manage", "Manage listers"),
]


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
        # Add manager_id column
        if not _has_column(connection, schema, "users", "manager_id"):
            op.add_column(
                "users",
                sa.Column("manager_id", sa.dialects.postgresql.UUID(), nullable=True),
                schema=schema,
            )
            op.create_foreign_key(
                f"fk_{schema}_users_manager_id",
                "users", "users",
                ["manager_id"], ["id"],
                source_schema=schema, referent_schema=schema,
                ondelete="SET NULL",
            )
            op.create_index(
                f"ix_{schema}_users_manager_id",
                "users", ["manager_id"],
                schema=schema,
            )

        # Seed new permissions
        for codename, description in NEW_PERMISSIONS:
            existing = connection.execute(
                sa.text(
                    f'SELECT id FROM "{schema}".permissions WHERE codename = :codename'
                ),
                {"codename": codename},
            ).first()
            if not existing:
                connection.execute(
                    sa.text(
                        f'INSERT INTO "{schema}".permissions (id, codename, description) '
                        f"VALUES (gen_random_uuid(), :codename, :description)"
                    ),
                    {"codename": codename, "description": description},
                )

        # Add new permissions to the 'staff' role
        staff_role = connection.execute(
            sa.text(f'SELECT id FROM "{schema}".roles WHERE slug = :slug'),
            {"slug": "staff"},
        ).first()
        if staff_role:
            staff_perms_to_add = [
                "customers:*:read", "customers:*:manage",
                "listers:*:invite", "listers:*:read", "listers:*:manage",
            ]
            for codename in staff_perms_to_add:
                perm = connection.execute(
                    sa.text(f'SELECT id FROM "{schema}".permissions WHERE codename = :codename'),
                    {"codename": codename},
                ).first()
                if perm:
                    exists = connection.execute(
                        sa.text(
                            f'SELECT 1 FROM "{schema}".role_permissions '
                            f"WHERE role_id = :rid AND permission_id = :pid"
                        ),
                        {"rid": staff_role[0], "pid": perm[0]},
                    ).first()
                    if not exists:
                        connection.execute(
                            sa.text(
                                f'INSERT INTO "{schema}".role_permissions (role_id, permission_id) '
                                f"VALUES (:rid, :pid)"
                            ),
                            {"rid": staff_role[0], "pid": perm[0]},
                        )


def downgrade() -> None:
    connection = op.get_bind()
    schemas = _get_tenant_schemas(connection)
    for schema in schemas:
        if _has_column(connection, schema, "users", "manager_id"):
            op.drop_index(f"ix_{schema}_users_manager_id", table_name="users", schema=schema)
            op.drop_constraint(f"fk_{schema}_users_manager_id", "users", schema=schema)
            op.drop_column("users", "manager_id", schema=schema)
        for codename, _ in NEW_PERMISSIONS:
            connection.execute(
                sa.text(f'DELETE FROM "{schema}".permissions WHERE codename = :codename'),
                {"codename": codename},
            )
