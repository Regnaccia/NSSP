from typing import Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.computed_facts.models.mixins import ComputedMetaMixin


class ComputedProductionStatus(Base, ComputedMetaMixin):
    """
    Quantità in produzione per articolo.

    Derivato da fact_productions (solo ordini aperti: is_closed=False).
    qty_in_production = SUM(qty_to_produce - qty_produced)
    """

    __tablename__ = "computed_production_status"

    computed_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_source_id: Mapped[str] = mapped_column(String(25), nullable=False, unique=True, index=True)
    qty_in_production: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    open_order_count: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
