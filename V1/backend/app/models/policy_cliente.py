import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class PolicyCliente(Base):
    __tablename__ = "policy_clienti"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cliente_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clienti.id"), nullable=False, unique=True
    )  # una policy per cliente
    tipo_policy: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # GIORNO_FISSO | DATA_TASSATIVA | SOGLIA_VALORE | DEFAULT | SPECIFICO
    giorno_fisso: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1=Lun … 7=Dom
    soglia_valore = mapped_column(Numeric(10, 2), nullable=True)
    corriere_preferito: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note_spedizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_json = mapped_column(JSONB, nullable=True)
    configurata_da: Mapped[str | None] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    cliente = relationship("Cliente", lazy="select")
