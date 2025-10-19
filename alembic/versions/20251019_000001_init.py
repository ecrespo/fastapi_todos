"""
Initial schema with todos (datetime + status enum) and auth_tokens.

Revision ID: 20251019_000001
Revises: 
Create Date: 2025-10-19 12:47:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251019_000001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    todo_status = sa.Enum('start', 'in_process', 'pending', 'done', 'cancel', name='todo_status')
    todo_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'todos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('item', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('status', todo_status, server_default=sa.text("'pending'"), nullable=False),
    )

    op.create_table(
        'auth_tokens',
        sa.Column('token', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('active', sa.Integer(), server_default=sa.text('1'), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('todos')
    op.drop_table('auth_tokens')
    todo_status = sa.Enum('start', 'in_process', 'pending', 'done', 'cancel', name='todo_status')
    todo_status.drop(op.get_bind(), checkfirst=True)
