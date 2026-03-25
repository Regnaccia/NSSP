from typing import Optional
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactOrder(Base, FactMetaMixin):
    """Ordine cliente canonico — derivato da sync_order_headers."""

    __tablename__ = "fact_orders"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    order_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    customer_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True, index=True)
    destination_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    customer_order_ref: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_method: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
