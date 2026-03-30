import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MateriaPrima(Base):
    __tablename__ = "materie_prime"

    id:           Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codice:       Mapped[str]           = mapped_column(String(50), nullable=False, unique=True)
    codice_upper: Mapped[str]           = mapped_column(String(50), nullable=False, unique=True)
    descrizione:  Mapped[str | None]    = mapped_column(Text, nullable=True)
    lunghezza_mm: Mapped[int | None]    = mapped_column(Integer, nullable=True)   # configurabile MRS
    synced_at:    Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False,
                                                        default=lambda: datetime.now(timezone.utc))
