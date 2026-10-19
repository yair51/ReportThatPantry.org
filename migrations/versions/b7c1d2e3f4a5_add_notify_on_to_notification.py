"""add notify_on to notification table

Revision ID: b7c1d2e3f4a5
Revises: 8551925f3652
Create Date: 2026-10-18 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c1d2e3f4a5'
down_revision = '8551925f3652'
branch_labels = None
depends_on = None


def upgrade():
    # 'empty' = only reports at or below 33% full (the old behavior), 'all' = every report
    op.add_column('notification', sa.Column('notify_on', sa.String(length=10), nullable=False, server_default='empty'))


def downgrade():
    op.drop_column('notification', 'notify_on')
