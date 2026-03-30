import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ConsegnaMagazzino(Base):
    __tablename__ = "consegne_magazzino"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    commessa_id: Mapped[str] = mapped_column(String(36), ForeignKey("commesse.id"), nullable=False)
    articolo_id: Mapped[str] = mapped_column(String(36), ForeignKey("articoli.id"), nullable=False)
    qty_consegnata: Mapped[int] = mapped_column(Integer, nullable=False)
    quota: Mapped[str] = mapped_column(String(10), nullable=False)  # cliente | scorta | mista
    qty_cliente: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_scorta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stato: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_attesa"
    )  # in_attesa | registrata_ej
    registrata_ej_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    commessa = relationship("Commessa", lazy="select")
    articolo = relationship("Articolo", lazy="select")
