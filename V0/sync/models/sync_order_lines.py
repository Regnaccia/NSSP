from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, String, Numeric, PrimaryKeyConstraint
from decimal import Decimal
from typing import Optional
from db.session import Base
from sync.models.mixins import SyncMetaMixin


class SyncOrderLine(Base, SyncMetaMixin):
    """
    Righe ordini clienti attivi — source: V_TORDCLI.
    PK composta: (order_source_id, line_number) = (ID_TESTATA, NUM_PROGR).

    Le righe con COLL_RIGA_PREC=True vengono assorbite dall'extractor:
    la loro ART_DESCR viene concatenata alla riga precedente (DL-ARCH-004).
    """

    __tablename__ = "sync_order_lines"
    __table_args__ = (
        PrimaryKeyConstraint("order_source_id", "line_number"),
    )

    order_source_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    article_source_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    article_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    qty_ordered: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_shipped: Mapped[Optional[Decimal]] = mapped_column(Numeric(13, 5), nullable=True)
    qty_packed: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 5), nullable=True)
    customer_line_ref: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
