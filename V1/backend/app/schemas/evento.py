"""
Schemi Pydantic per eventi inter-reparto (Fase 4).
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class UrgenzaRequest(BaseModel):
    ordine_id: str
    nota: Optional[str] = None
    created_by: Optional[str] = None


class FeedbackRequest(BaseModel):
    feedback_stato: str               # accettata | non_fattibile
    feedback_data_prevista: Optional[date] = None
    feedback_nota: Optional[str] = None
    corriere_override: Optional[str] = None   # per urgenze con spedizione parziale urgente


class RisolviRequest(BaseModel):
    nota: Optional[str] = None


class EventoResponse(BaseModel):
    id: str
    tipo: str
    mittente: str
    destinatario: str
    stato: str                        # aperto | in_lavorazione | risolto | rifiutato

    ref_ordine_id: Optional[str]
    numero_ordine: Optional[str]      # da join
    cliente: Optional[str]            # da join (nickname || ragione_sociale)

    ref_commessa_id: Optional[str]
    ref_articolo_id: Optional[str]

    nota: Optional[str]

    feedback_stato: Optional[str]     # accettata | non_fattibile
    feedback_data_prevista: Optional[date]
    feedback_nota: Optional[str]
    corriere_override: Optional[str]

    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
