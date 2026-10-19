"""add time_zone to location table

Revision ID: c4d5e6f7a8b9
Revises: b7c1d2e3f4a5
Create Date: 2026-10-18 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b7c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
    # IANA time zone name per pantry; report times themselves stay in UTC
    op.add_column('location', sa.Column('time_zone', sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column('location', 'time_zone')
