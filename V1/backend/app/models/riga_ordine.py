import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RigaOrdine(Base):
    __tablename__ = "righe_ordine"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ordine_id: Mapped[str] = mapped_column(String(36), ForeignKey("ordini.id"), nullable=False)
    articolo_id: Mapped[str] = mapped_column(String(36), ForeignKey("articoli.id"), nullable=False)
    riga_ej_id: Mapped[str] = mapped_column(String(50), nullable=False)
    qty_ordinata: Mapped[int] = mapped_column(Integer, nullable=False)
    qty_disponibile: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_in_produzione: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_consegnata: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # qty_da_produrre NON è una colonna — calcolata live:
    # max(0, qty_ordinata - qty_disponibile - qty_in_produzione)
    stato: Mapped[str] = mapped_column(
        String(30), nullable=False, default="aperto"
    )  # aperto | in_produzione | pronto | spedito | chiuso
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    ordine = relationship("Ordine", back_populates="righe")
    articolo = relationship("Articolo", lazy="select")
