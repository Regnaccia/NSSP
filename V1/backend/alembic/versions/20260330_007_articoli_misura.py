"""articoli: aggiunge colonna misura (da ANAART)

Revision ID: 20260330_007
Revises: 20260330_006
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '20260330_007'
down_revision = '20260330_006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('articoli', sa.Column('misura', sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column('articoli', 'misura')
