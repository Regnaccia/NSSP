"""categorie_articolo — sync da CATART1 EasyJob, assegnazione famiglia

Revision ID: 20260330_006
Revises: 20260330_005
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_006'
down_revision = '20260330_005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'categorie_articolo',
        sa.Column('codice',      sa.String(20),  nullable=False, primary_key=True),
        sa.Column('descrizione', sa.String(200), nullable=True),
        # famiglia: 'standard' | 'speciali' | 'barre' | NULL (= escludi da lanci)
        sa.Column('famiglia',    sa.String(20),  nullable=True),
        sa.Column('synced_at',   sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('categorie_articolo')
