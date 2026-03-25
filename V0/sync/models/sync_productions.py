from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Numeric, DateTime, Boolean
from decimal import Decimal
from datetime import datetime
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncProduction(Base, SyncMetaMixin):
    """Produzioni attive — source: DPRE_PROD"""

    __tablename__ = "sync_productions"

    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    customer_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    production_order: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    qty_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_to_produce: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_produced: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    qty_in_progress: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    is_closed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    order_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    order_line: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    planned_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
