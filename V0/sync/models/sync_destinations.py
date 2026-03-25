from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncDestination(Base, SyncMetaMixin):
    """Destinazioni clienti — source: POT_DESTDIV"""

    __tablename__ = "sync_destinations"

    source_id: Mapped[str] = mapped_column(String(6), primary_key=True)
    customer_source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    is_default: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
