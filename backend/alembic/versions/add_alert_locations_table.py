"""add_alert_locations_table

Revision ID: add_alert_locations_table
Revises: add_alert_location_fields
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_alert_locations_table'
down_revision: Union[str, None] = 'add_alert_location_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'alert_locations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alerts.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location_source', sa.String(length=30), nullable=False),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('resolved_order', sa.Integer(), nullable=True),
    )
    op.create_index('ix_alert_locations_alert_id', 'alert_locations', ['alert_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_alert_locations_alert_id', table_name='alert_locations')
    op.drop_table('alert_locations')