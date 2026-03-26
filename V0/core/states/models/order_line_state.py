from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class OrderLineState(Base):
    """
    Stato canonico persistente di una singola riga ordine.

    Derivato da computed_order_lines dopo che la FifoAllocationPolicy ha girato.
    Valori possibili: FULFILLED, PARTIALLY_FULFILLED, COVERABLE_NOW, NOT_COVERABLE_NOW, OPEN
    Priorità: FULFILLED > PARTIALLY_FULFILLED > COVERABLE_NOW / NOT_COVERABLE_NOW > OPEN
    """

    __tablename__ = "order_line_states"
    __table_args__ = (
        Index("ix_order_line_states_order_source_id", "order_source_id"),
    )

    state_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    state: Mapped[str] = mapped_column(String(25), nullable=False)
    trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
