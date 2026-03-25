from typing import Optional
from decimal import Decimal
from sqlalchemy import BigInteger, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.computed_facts.models.mixins import ComputedMetaMixin


class ComputedArticleDemand(Base, ComputedMetaMixin):
    """
    Domanda netta per articolo — aggregato a livello articolo.

    Derivato da fact_order_lines e fact_stock_movements.

    total_stock       = SUM(qty_in - qty_out) su tutti i depositi
    total_open_demand = SUM(qty_ordered - qty_shipped) su righe aperte (qty_remaining > 0)
    net_available_raw = total_stock - total_open_demand
    """

    __tablename__ = "computed_article_demand"

    computed_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    article_source_id: Mapped[str] = mapped_column(String(25), nullable=False, unique=True, index=True)
    total_stock: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    total_open_demand: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    net_available_raw: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
