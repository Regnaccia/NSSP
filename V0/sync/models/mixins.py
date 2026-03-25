from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, String, BigInteger
from datetime import datetime
from typing import Optional


class SyncMetaMixin:
    """Campi comuni a tutti i modelli sync_* — tracciabilità e change detection."""

    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    row_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
