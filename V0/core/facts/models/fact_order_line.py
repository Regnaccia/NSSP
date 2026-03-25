from typing import Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactOrderLine(Base, FactMetaMixin):
    """Riga ordine canonica — derivata da sync_order_lines."""

    __tablename__ = "fact_order_lines"
    __table_args__ = (
        UniqueConstraint("order_source_id", "line_number", name="uq_fact_order_lines_key"),
    )

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    article_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qty_ordered: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_shipped: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_packed: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    customer_line_ref: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 4), nullable=True)
