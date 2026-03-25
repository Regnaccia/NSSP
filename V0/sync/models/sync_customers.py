from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncCustomer(Base, SyncMetaMixin):
    """Anagrafica clienti — source: ANACLI"""

    __tablename__ = "sync_customers"

    source_id: Mapped[str] = mapped_column(String(6), primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(110), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(70), nullable=True)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
