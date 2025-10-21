"""
Add user_id to auth_tokens (nullable) to link tokens to users.

Revision ID: 20251021_000003
Revises: 20251019_000002
Create Date: 2025-10-21 18:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251021_000003'
down_revision = '20251019_000002'
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in cols


def upgrade() -> None:
    if not _has_column('auth_tokens', 'user_id'):
        op.add_column('auth_tokens', sa.Column('user_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    if _has_column('auth_tokens', 'user_id'):
        op.drop_column('auth_tokens', 'user_id')
