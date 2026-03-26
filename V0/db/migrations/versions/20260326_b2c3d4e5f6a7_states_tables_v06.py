"""states_tables_v06

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'order_line_states',
        sa.Column('state_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_source_id', sa.BigInteger(), nullable=False),
        sa.Column('line_number', sa.BigInteger(), nullable=False),
        sa.Column('article_source_id', sa.String(length=25), nullable=True),
        sa.Column('state', sa.String(length=25), nullable=False),
        sa.Column('trace', sa.Text(), nullable=True),
        sa.Column('built_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('state_id'),
    )
    op.create_index('ix_order_line_states_order_source_id', 'order_line_states', ['order_source_id'])

    op.create_table(
        'order_states',
        sa.Column('state_id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('order_source_id', sa.BigInteger(), nullable=False),
        sa.Column('state', sa.String(length=25), nullable=False),
        sa.Column('total_lines', sa.Integer(), nullable=False),
        sa.Column('open_lines', sa.Integer(), nullable=False),
        sa.Column('coverable_lines', sa.Integer(), nullable=False),
        sa.Column('fulfilled_lines', sa.Integer(), nullable=False),
        sa.Column('trace', sa.Text(), nullable=True),
        sa.Column('built_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('state_id'),
    )
    op.create_index('ix_order_states_order_source_id', 'order_states', ['order_source_id'])


def downgrade() -> None:
    op.drop_index('ix_order_states_order_source_id', table_name='order_states')
    op.drop_table('order_states')
    op.drop_index('ix_order_line_states_order_source_id', table_name='order_line_states')
    op.drop_table('order_line_states')
