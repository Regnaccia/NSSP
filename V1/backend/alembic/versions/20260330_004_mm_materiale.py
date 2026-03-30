"""Aggiunge mm_materiale ad articoli (REGN_QT_OCCORR + REGN_QT_SCARTO da ANAART).

Revision ID: 20260330_004
Revises: 20260330_003
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_004'
down_revision = '20260330_003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'articoli',
        sa.Column('mm_materiale', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('articoli', 'mm_materiale')
