import uuid
from datetime import datetime, date, timezone
from sqlalchemy import String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Evento(Base):
    __tablename__ = "eventi"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tipo: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # urgenza_formale | priorita_interna | ordine_pronto | feedback_urgenza | suggerimento_scheduler
    mittente: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # produzione | magazzino | logistica | sistema
    destinatario: Mapped[str] = mapped_column(String(30), nullable=False)

    ref_ordine_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ordini.id"), nullable=True)
    ref_commessa_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("commesse.id"), nullable=True)
    ref_articolo_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("articoli.id"), nullable=True)

    stato: Mapped[str] = mapped_column(
        String(20), nullable=False, default="aperto"
    )  # aperto | in_lavorazione | risolto | rifiutato
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Feedback urgenza
    feedback_stato: Mapped[str | None] = mapped_column(String(30), nullable=True)  # accettata | non_fattibile
    feedback_data_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)
    feedback_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    corriere_override: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ref_ordine = relationship("Ordine", lazy="select")
    ref_commessa = relationship("Commessa", lazy="select")
    ref_articolo = relationship("Articolo", lazy="select")
