"""
Schemi Pydantic per commesse, macchine, reparto (Fase 2).
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Macchine
# ---------------------------------------------------------------------------

class MacchinaResponse(BaseModel):
    id: str
    codice: str
    nome: str
    stato: str                        # disponibile | in_lavorazione | in_setup | in_manutenzione
    attiva: bool
    operazioni_eseguibili: list[str]
    setup_corrente: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Commessa — response
# ---------------------------------------------------------------------------

class CommessaResponse(BaseModel):
    id: str
    articolo_id: str
    codice_articolo: str
    descrizione_articolo: Optional[str]

    riga_ordine_id: Optional[str]
    numero_ordine: Optional[str]      # da join ordine via riga_ordine

    macchina_id: Optional[str]
    macchina_codice: Optional[str]
    ldp_easyjob: Optional[str]

    qty_cliente: int
    qty_scorta: int
    qty_prodotta_cliente: int
    qty_prodotta_scorta: int
    qty_ciclo_corrente: Optional[int]
    qty_totale: int                   # qty_cliente + qty_scorta
    qty_residua: int                  # qty_totale - qty_prodotta

    stato: str                        # in_coda | in_produzione | sospesa | completata
    posizione_coda: Optional[int]
    priorita_suggerita: Optional[int] # 1=urgenza, 2=normale

    sospesa_at: Optional[datetime]
    sospesa_nota: Optional[str]
    completata_at: Optional[datetime]
    created_at: datetime
    created_by: Optional[str]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Schedulazione (ufficio produzione — F2)
# ---------------------------------------------------------------------------

class AssegnaMacchinaRequest(BaseModel):
    macchina_id: str


class RiordinaVoce(BaseModel):
    commessa_id: str
    posizione: int


class RiordinaCodaRequest(BaseModel):
    ordine: list[RiordinaVoce]


class RiordinaCodaResponse(BaseModel):
    aggiornate: int


# ---------------------------------------------------------------------------
# Reparto terminale
# ---------------------------------------------------------------------------

class SospendiRequest(BaseModel):
    nota: Optional[str] = None


class AggiornaQtyRequest(BaseModel):
    qty_prodotta_cliente: Optional[int] = None
    qty_prodotta_scorta: Optional[int] = None
