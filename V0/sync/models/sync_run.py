from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, String, Integer, Text
from datetime import datetime
from typing import Optional
from db.session import Base


class SyncRun(Base):
    """
    Traccia ogni esecuzione del layer sync.
    Stati: STARTED | COMPLETED | FAILED | COMPLETED_WITH_WARNINGS
    """

    __tablename__ = "sync_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)

    records_read: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_inserted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_deleted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
