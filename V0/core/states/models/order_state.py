from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, Integer, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base


class OrderState(Base):
    """
    Stato canonico persistente aggregato per ordine.

    Derivato dagli stati delle sue OrderLineState.
    Valori possibili: FULFILLED, FULLY_COVERABLE, PARTIALLY_COVERABLE, OPEN
    """

    __tablename__ = "order_states"
    __table_args__ = (
        Index("ix_order_states_order_source_id", "order_source_id"),
    )

    state_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    state: Mapped[str] = mapped_column(String(25), nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    open_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    coverable_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    fulfilled_lines: Mapped[int] = mapped_column(Integer, nullable=False)
    trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    built_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
