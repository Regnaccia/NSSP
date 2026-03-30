"""Cambia default mesi_scorta da 3 a 2 e aggiorna articoli esistenti.

Revision ID: 20260330_003
Revises: 20260330_002
Create Date: 2026-03-30
"""
from alembic import op

revision = '20260330_003'
down_revision = '20260330_002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE articoli ALTER COLUMN mesi_scorta SET DEFAULT 2")
    op.execute("UPDATE articoli SET mesi_scorta = 2 WHERE mesi_scorta = 3")


def downgrade() -> None:
    op.execute("ALTER TABLE articoli ALTER COLUMN mesi_scorta SET DEFAULT 3")
    op.execute("UPDATE articoli SET mesi_scorta = 3 WHERE mesi_scorta = 2")
