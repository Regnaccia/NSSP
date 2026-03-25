from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column


class FactMetaMixin:
    """Metadati comuni a tutti i fact_* del layer core."""

    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sync_run_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
