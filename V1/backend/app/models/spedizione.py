import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Spedizione(Base):
    __tablename__ = "spedizioni"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ordine_id: Mapped[str] = mapped_column(String(36), ForeignKey("ordini.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # totale | parziale | urgenza
    stato: Mapped[str] = mapped_column(
        String(30), nullable=False, default="in_preparazione"
    )  # in_preparazione | pronta | in_spedizione | spedita | annullata
    corriere: Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_pianificata: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_spedizione: Mapped[date | None] = mapped_column(Date, nullable=True)
    colli: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peso_kg = mapped_column(Numeric(8, 2), nullable=True)
    evento_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("eventi.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    ordine = relationship("Ordine", lazy="select")
    evento = relationship("Evento", lazy="select")
