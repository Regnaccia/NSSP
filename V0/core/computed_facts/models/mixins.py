from datetime import datetime
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class ComputedMetaMixin:
    """Metadati comuni a tutti i computed_* del layer core."""

    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
