"""add_sos_location_fields_to_alerts

Revision ID: 4fe87994270f
Revises: 4b5bd9d23e74
Create Date: 2026-09-25 17:44:47.961609
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4fe87994270f'
down_revision: Union[str, None] = '4b5bd9d23e74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('alerts', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('alerts', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('alerts', sa.Column('accuracy', sa.Float(), nullable=True))
    op.add_column('alerts', sa.Column('timestamp', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('alerts', 'timestamp')
    op.drop_column('alerts', 'accuracy')
    op.drop_column('alerts', 'longitude')
    op.drop_column('alerts', 'latitude')
