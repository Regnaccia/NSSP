from typing import Optional
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactStockMovement(Base, FactMetaMixin):
    """
    Movimento di magazzino canonico — derivato da sync_stock_movements.

    Strategia builder: APPEND_ONLY (MAG_REALE è append-only per design).
    """

    __tablename__ = "fact_stock_movements"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True, index=True)
    depot_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    qty_in: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    qty_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    movement_type: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
