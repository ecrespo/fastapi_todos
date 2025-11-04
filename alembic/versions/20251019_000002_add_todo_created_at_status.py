"""
Add created_at and status columns to todos if missing.

Revision ID: 20251019_000002
Revises: 20251019_000001
Create Date: 2025-10-19 13:15:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251019_000002"
down_revision = "20251019_000001"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c["name"] for c in inspector.get_columns(table_name)]
    return column_name in cols


def upgrade() -> None:
    # Ensure enum exists on backends that support it (no-op on SQLite)
    todo_status = sa.Enum("start", "in_process", "pending", "done", "cancel", name="todo_status")
    try:
        todo_status.create(op.get_bind(), checkfirst=True)
    except Exception:
        # Safe-guard for SQLite and idempotency
        pass

    if not _has_column("todos", "created_at"):
        op.add_column(
            "todos",
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
    if not _has_column("todos", "status"):
        op.add_column(
            "todos",
            sa.Column("status", todo_status, server_default=sa.text("'pending'"), nullable=False),
        )


def downgrade() -> None:
    # Drop columns if they exist; ignore errors if not present
    if _has_column("todos", "status"):
        op.drop_column("todos", "status")
    if _has_column("todos", "created_at"):
        op.drop_column("todos", "created_at")

    # Drop enum type on backends that created it
    try:
        todo_status = sa.Enum("start", "in_process", "pending", "done", "cancel", name="todo_status")
        todo_status.drop(op.get_bind(), checkfirst=True)
    except Exception:
        pass
