from typing import Optional
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactCustomer(Base, FactMetaMixin):
    """Cliente canonico — derivato da sync_customers."""

    __tablename__ = "fact_customers"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(110), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    vat_number: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(70), nullable=True)
