import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Cliente(Base):
    __tablename__ = "clienti"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codice_easyjob: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    ragione_sociale: Mapped[str] = mapped_column(Text, nullable=False)
    # DL-ARCH-017: nickname operativo — MRS-owned, mai toccato dal sync
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
