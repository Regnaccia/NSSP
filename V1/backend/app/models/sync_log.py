import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SyncLog(Base):
    __tablename__ = "sync_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tabella: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_updated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sync_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
