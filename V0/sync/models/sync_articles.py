from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, DateTime
from datetime import datetime
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncArticle(Base, SyncMetaMixin):
    """Anagrafica articoli — source: ANAART"""

    __tablename__ = "sync_articles"

    source_id: Mapped[str] = mapped_column(String(25), primary_key=True)
    description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description_2: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    is_blocked: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    material_code: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
