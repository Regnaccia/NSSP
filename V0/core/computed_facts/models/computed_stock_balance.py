from typing import Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.computed_facts.models.mixins import ComputedMetaMixin


class ComputedStockBalance(Base, ComputedMetaMixin):
    """
    Saldo di magazzino per articolo e deposito.

    Derivato da fact_stock_movements via SQL aggregation (GROUP BY).
    stock_balance = SUM(qty_in) - SUM(qty_out)
    """

    __tablename__ = "computed_stock_balances"
    __table_args__ = (
        UniqueConstraint("article_source_id", "depot_code", name="uq_computed_stock_balances_key"),
    )

    computed_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    depot_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True, index=True)
    qty_in_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    qty_out_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    stock_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    movement_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
