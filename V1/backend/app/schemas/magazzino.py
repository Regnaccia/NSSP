"""
Schemi Pydantic per il modulo Magazzino (Fase 3).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Vista ordini da approntare
# ---------------------------------------------------------------------------

class ArticoloProntoItem(BaseModel):
    commessa_id: str
    articolo_id: str
    codice_articolo: str
    descrizione_articolo: Optional[str]
    qty_prodotta_cliente: int
    qty_prodotta_scorta: int
    qty_totale: int
    gia_registrata: bool          # True se esiste già una ConsegnaMagazzino per questa commessa


class OrdineApprontareResponse(BaseModel):
    ordine_id: str
    numero_ordine: str
    data_consegna: Optional[datetime]
    cliente: str                  # nickname || ragione_sociale (DL-ARCH-017)
    cliente_id: str
    flag_urgenza: bool
    articoli: list[ArticoloProntoItem]
    tutte_registrate: bool        # True se tutti gli articoli hanno già una consegna registrata


# ---------------------------------------------------------------------------
# Registra consegna dal magazzino
# ---------------------------------------------------------------------------

class RegistraConsegnaRequest(BaseModel):
    commessa_id: str
    qty_cliente: int
    qty_scorta: int


class ConsegnaResponse(BaseModel):
    id: str
    commessa_id: str
    articolo_id: str
    codice_articolo: str
    descrizione_articolo: Optional[str]
    qty_consegnata: int
    quota: str                    # cliente | scorta | mista
    qty_cliente: int
    qty_scorta: int
    stato: str                    # in_attesa | registrata_ej
    registrata_ej_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Segnala ordine pronto per logistica
# ---------------------------------------------------------------------------

class OrdineProontoRequest(BaseModel):
    nota: Optional[str] = None
    created_by: Optional[str] = None


class EventoResponse(BaseModel):
    id: str
    tipo: str
    mittente: str
    destinatario: str
    stato: str
    nota: Optional[str]
    ref_ordine_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
