"""add_location_timestamp_field

Revision ID: 4b5bd9d23e74
Revises: 7b9aa0df48e9
Create Date: 2026-09-25 17:33:14.088416
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4b5bd9d23e74'
down_revision: Union[str, None] = '7b9aa0df48e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('location_timestamp', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'location_timestamp')
