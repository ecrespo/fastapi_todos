"""
Create users table with user_role enum for PostgreSQL compatibility.

Revision ID: 20251021_000004
Revises: 20251021_000003
Create Date: 2025-10-21 18:12:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251021_000004"
down_revision = "20251021_000003"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(index_name: str, table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    # Create enum type for user roles (no-op on backends not supporting enums)
    user_role = sa.Enum("viewer", "editor", "admin", name="user_role")
    try:
        user_role.create(op.get_bind(), checkfirst=True)
    except Exception:
        # SQLite or already present
        pass

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("username", sa.String(), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("role", user_role, nullable=False),
            sa.Column("active", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        # Ensure unique index on username for backends that ignore "unique=True" during create if table pre-existed
        if not _has_index("ux_users_username", "users"):
            try:
                op.create_index("ux_users_username", "users", ["username"], unique=True)
            except Exception:
                pass


def downgrade() -> None:
    if _has_table("users"):
        # Drop index if exists
        try:
            op.drop_index("ux_users_username", table_name="users")
        except Exception:
            pass
        op.drop_table("users")

    # Drop enum type
    try:
        user_role = sa.Enum("viewer", "editor", "admin", name="user_role")
        user_role.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
