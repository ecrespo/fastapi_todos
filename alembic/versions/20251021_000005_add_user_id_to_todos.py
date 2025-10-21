"""
Add user_id column to todos table.

Revision ID: 20251021_000005
Revises: 20251021_000004
Create Date: 2025-10-21 18:55:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251021_000005'
down_revision = '20251021_000004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column to todos (nullable integer)
    op.add_column('todos', sa.Column('user_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Drop user_id column from todos
    op.drop_column('todos', 'user_id')
