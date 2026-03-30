import uuid
from sqlalchemy import String, Text, Boolean, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Macchina(Base):
    __tablename__ = "macchine"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codice: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    operazioni_eseguibili: Mapped[list] = mapped_column(ARRAY(Text), nullable=False, default=list)
    stato: Mapped[str] = mapped_column(
        String(30), nullable=False, default="disponibile"
    )  # disponibile | in_lavorazione | in_setup | in_manutenzione
    setup_corrente: Mapped[str | None] = mapped_column(Text, nullable=True)
    attiva: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
