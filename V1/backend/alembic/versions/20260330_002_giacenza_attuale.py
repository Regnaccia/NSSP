"""Aggiunge giacenza_attuale ad articoli per sync MAG_REALE.

Revision ID: 20260330_002
Revises: 20260327_001
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'articoli',
        sa.Column('giacenza_attuale', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('articoli', 'giacenza_attuale')
