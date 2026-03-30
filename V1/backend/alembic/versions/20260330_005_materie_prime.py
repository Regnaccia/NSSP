"""Aggiunge tabella materie_prime e FK articoli.materia_prima_id.

Revision ID: 20260330_005
Revises: 20260330_004
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_005'
down_revision = '20260330_004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'materie_prime',
        sa.Column('id',          sa.String(36),  nullable=False, primary_key=True),
        sa.Column('codice',      sa.String(50),  nullable=False, unique=True),
        sa.Column('codice_upper',sa.String(50),  nullable=False, unique=True),
        sa.Column('descrizione', sa.Text(),       nullable=True),
        sa.Column('lunghezza_mm',sa.Integer(),    nullable=True),   # MRS-owned, configurabile
        sa.Column('synced_at',   sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column(
        'articoli',
        sa.Column(
            'materia_prima_id',
            sa.String(36),
            sa.ForeignKey('materie_prime.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column('articoli', 'materia_prima_id')
    op.drop_table('materie_prime')
