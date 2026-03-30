import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Articolo(Base):
    __tablename__ = "articoli"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codice: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    codice_upper: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    descrizione: Mapped[str | None] = mapped_column(Text, nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capienza: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Parametri operativi MRS
    scorta_mensile: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mesi_scorta: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    tipo_produzione: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PEZZO"
    )  # PEZZO | BARRA | FASCI | SPECIALE | BARRA_GREZZA
    materia_prima_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("materie_prime.id", ondelete="SET NULL"), nullable=True
    )
    lunghezza_barra: Mapped[int | None] = mapped_column(Integer, nullable=True)   # override manuale
    multipli_taglio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mm_materiale: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prd_pari: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Computed persistito — ricalcolo mensile
    storico_sufficiente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scorta_calcolata_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Dati dimensionali (da ANAART, sync-owned)
    giacenza_attuale: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    misura:    Mapped[str | None] = mapped_column(String(100), nullable=True)   # ART_MISURA
    immagine:  Mapped[str | None] = mapped_column(String(50),  nullable=True)   # COD_IMM

    # Sync
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
