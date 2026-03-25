from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Numeric, DateTime
from decimal import Decimal
from datetime import datetime
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncStockMovement(Base, SyncMetaMixin):
    """
    Movimenti di magazzino — source: MAG_REALE.
    Ogni riga è un movimento (carico o scarico).
    FLG_CARSCA: C = carico, S = scarico.
    Il saldo per articolo si calcola nel core (computed fact).
    """

    __tablename__ = "sync_stock_movements"

    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    depot_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    qty_in: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    qty_out: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    movement_type: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    document_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    document_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    registered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
