from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, String
from datetime import datetime
from db.session import Base


class SyncChangeItem(Base):
    """
    Registra ogni variazione rilevata durante una sync run.
    Tipi: INSERTED | UPDATED | DELETED
    Implementa il change contract verso il core (DL-ARCH-005).
    """

    __tablename__ = "sync_change_item"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sync_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
