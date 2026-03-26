from typing import Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.computed_facts.models.mixins import ComputedMetaMixin


class ComputedOrderLine(Base, ComputedMetaMixin):
    """
    Riga ordine con quantità residua calcolata.

    Derivata da fact_order_lines.
    qty_remaining = qty_ordered - qty_shipped
    """

    __tablename__ = "computed_order_lines"
    __table_args__ = (
        UniqueConstraint("order_source_id", "line_number", name="uq_computed_order_lines_key"),
    )

    computed_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    qty_ordered: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_shipped: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_remaining: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    is_fully_shipped: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_open_line: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 4), nullable=True)
    value_remaining: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4), nullable=True)
    qty_coverable_now: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    coverable_now: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
