from typing import Optional
from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from db.session import Base
from core.facts.models.mixins import FactMetaMixin


class FactArticle(Base, FactMetaMixin):
    """Articolo canonico — derivato da sync_articles."""

    __tablename__ = "fact_articles"

    fact_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(25), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description_2: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    unit_of_measure: Mapped[Optional[str]] = mapped_column(String(3), nullable=True)
    is_blocked: Mapped[Optional[bool]] = mapped_column(nullable=True)
    material_code: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
