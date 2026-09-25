"""add_alert_location_fields_and_locations_table

Revision ID: add_alert_location_fields
Revises: 2bfd451b4aed
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_alert_location_fields'
down_revision: Union[str, None] = '2bfd451b4aed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add location fields to alerts table
    op.add_column('alerts', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('alerts', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('alerts', sa.Column('location_source', sa.String(length=30), nullable=True))

    # Create locations table for geographic gazetteer
    op.create_table(
        'locations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False, index=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True, default='India'),
        sa.Column('aliases', sa.Text(), nullable=True),
    )
    op.create_index('ix_locations_normalized_name', 'locations', ['normalized_name'], unique=False)
    op.create_index('ix_locations_state_district', 'locations', ['state', 'district'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_locations_state_district', table_name='locations')
    op.drop_index('ix_locations_normalized_name', table_name='locations')
    op.drop_table('locations')
    op.drop_column('alerts', 'location_source')
    op.drop_column('alerts', 'longitude')
    op.drop_column('alerts', 'latitude')