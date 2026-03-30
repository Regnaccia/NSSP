import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Ordine(Base):
    __tablename__ = "ordini"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    numero_ordine: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    cliente_id: Mapped[str] = mapped_column(String(36), ForeignKey("clienti.id"), nullable=False)
    data_ordine: Mapped[date] = mapped_column(Date, nullable=False)
    data_consegna: Mapped[date | None] = mapped_column(Date, nullable=True)
    stato: Mapped[str] = mapped_column(
        String(30), nullable=False, default="aperto"
    )  # aperto | parzialmente_spedito | spedito | chiuso
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    cliente = relationship("Cliente", lazy="select")
    righe = relationship("RigaOrdine", back_populates="ordine", lazy="select")
