from typing import Optional
from sqlalchemy import BigInteger, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactDestination(Base, FactMetaMixin):
    """
    Destinazione di consegna canonica.

    Derivata da sync_destinations (is_derived_from_customer=False).
    Oppure derivata da sync_customers quando il cliente non ha destinazioni
    esplicite (is_derived_from_customer=True) — regola di dominio v0.2.
    """

    __tablename__ = "fact_destinations"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(6), nullable=True, index=True)
    customer_source_id: Mapped[str] = mapped_column(String(6), nullable=False, index=True)
    code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(55), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    province: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    is_default: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_derived_from_customer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
