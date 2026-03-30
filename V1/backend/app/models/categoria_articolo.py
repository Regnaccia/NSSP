from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CategoriaArticolo(Base):
    __tablename__ = "categorie_articolo"

    codice:      Mapped[str]            = mapped_column(String(20), primary_key=True)
    descrizione: Mapped[str | None]     = mapped_column(String(200), nullable=True)
    # 'standard' | 'speciali' | 'barre' | None (= escludi dai lanci)
    famiglia:    Mapped[str | None]     = mapped_column(String(20), nullable=True)
    synced_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)
