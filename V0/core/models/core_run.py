from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, String, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class CoreRun(Base):
    """
    Traccia ogni esecuzione del layer core (full rebuild o targeted rebuild).
    Stati: STARTED | COMPLETED | FAILED | COMPLETED_WITH_WARNINGS
    Tipi:  FULL | TARGETED
    """

    __tablename__ = "core_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    rebuild_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sync_run_id_from: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sync_run_id_to: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    aggregates_rebuilt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    records_rebuilt: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
