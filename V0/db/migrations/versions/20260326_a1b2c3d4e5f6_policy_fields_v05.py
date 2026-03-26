"""policy_fields_v05

Revision ID: a1b2c3d4e5f6
Revises: cc3d86f0809b
Create Date: 2026-03-26 09:00:00.000000

Aggiunge campi policy-driven a computed_order_lines:
  - qty_coverable_now: quanta domanda è coperta dallo stock attuale (FIFO)
  - coverable_now:     True se l'intera qty_remaining è coperta
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'cc3d86f0809b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('computed_order_lines',
        sa.Column('qty_coverable_now', sa.Numeric(13, 5), nullable=True))
    op.add_column('computed_order_lines',
        sa.Column('coverable_now', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('computed_order_lines', 'coverable_now')
    op.drop_column('computed_order_lines', 'qty_coverable_now')
