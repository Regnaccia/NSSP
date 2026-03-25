from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactProduction(Base, FactMetaMixin):
    """Ordine di produzione canonico — derivato da sync_productions."""

    __tablename__ = "fact_productions"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    production_order: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    customer_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True, index=True)
    qty_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_to_produce: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_produced: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_in_progress: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    is_closed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    order_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    order_line: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    planned_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
