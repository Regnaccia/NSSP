import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Commessa(Base):
    __tablename__ = "commesse"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    riga_ordine_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("righe_ordine.id"), nullable=True
    )  # NULL per commesse pure scorta
    articolo_id: Mapped[str] = mapped_column(String(36), ForeignKey("articoli.id"), nullable=False)
    macchina_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("macchine.id"), nullable=True
    )  # NULL finché non schedulata
    ldp_easyjob: Mapped[str | None] = mapped_column(String(50), nullable=True)

    qty_cliente: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_scorta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_prodotta_cliente: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_prodotta_scorta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    qty_ciclo_corrente: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stato: Mapped[str] = mapped_column(
        String(30), nullable=False, default="in_coda"
    )  # in_coda | in_produzione | sospesa | completata
    posizione_coda: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priorita_suggerita: Mapped[int | None] = mapped_column(Integer, nullable=True)

    sospesa_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sospesa_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    completata_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)

    riga_ordine = relationship("RigaOrdine", lazy="select")
    articolo = relationship("Articolo", lazy="select")
    macchina = relationship("Macchina", lazy="select")
