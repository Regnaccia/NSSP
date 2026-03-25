from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, DateTime
from datetime import datetime
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncOrderHeader(Base, SyncMetaMixin):
    """Testate ordini clienti attivi — source: V_TORDCLI (deduplicata per ID_TESTATA)"""

    __tablename__ = "sync_order_headers"

    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    order_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    customer_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    destination_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    order_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    customer_order_ref: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    delivery_method: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
