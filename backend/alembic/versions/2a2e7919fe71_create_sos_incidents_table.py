"""create_sos_incidents_table

Revision ID: 2a2e7919fe71
Revises: 4fe87994270f
Create Date: 2026-09-25 18:51:43.851357
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2a2e7919fe71'
down_revision: Union[str, None] = '4fe87994270f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sos_incidents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporting_user_id', sa.Integer(), nullable=False),
        sa.Column('assigned_responder_id', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('location_accuracy', sa.Float(), nullable=True),
        sa.Column('location_timestamp', sa.BigInteger(), nullable=True),
        sa.Column('emergency_type', sa.String(100), nullable=True),
        sa.Column('emergency_details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('responder_type', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_responder_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reporting_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sos_incidents_id'), 'sos_incidents', ['id'], unique=False)
    op.create_index(op.f('ix_sos_incidents_reporting_user_id'), 'sos_incidents', ['reporting_user_id'], unique=False)
    op.create_index(op.f('ix_sos_incidents_assigned_responder_id'), 'sos_incidents', ['assigned_responder_id'], unique=False)
    op.create_index(op.f('ix_sos_incidents_status'), 'sos_incidents', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sos_incidents_status'), table_name='sos_incidents')
    op.drop_index(op.f('ix_sos_incidents_assigned_responder_id'), table_name='sos_incidents')
    op.drop_index(op.f('ix_sos_incidents_reporting_user_id'), table_name='sos_incidents')
    op.drop_index(op.f('ix_sos_incidents_id'), table_name='sos_incidents')
    op.drop_table('sos_incidents')
