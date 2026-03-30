"""
Schemi Pydantic per il modulo Logistica (Fase 3).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Policy cliente
# ---------------------------------------------------------------------------

class PolicyClienteResponse(BaseModel):
    id: str
    cliente_id: str
    tipo_policy: str              # GIORNO_FISSO | DATA_TASSATIVA | SOGLIA_VALORE | DEFAULT
    giorno_fisso: Optional[int]   # 1=Lun … 7=Dom (solo GIORNO_FISSO)
    soglia_valore: Optional[Decimal]  # (solo SOGLIA_VALORE)
    corriere_preferito: Optional[str]
    note_spedizione: Optional[str]
    policy_json: Optional[Any]    # JSONB per estensioni future
    configurata_da: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


class PolicyClienteRequest(BaseModel):
    tipo_policy: str
    giorno_fisso: Optional[int] = None
    soglia_valore: Optional[Decimal] = None
    corriere_preferito: Optional[str] = None
    note_spedizione: Optional[str] = None
    policy_json: Optional[Any] = None
    configurata_da: Optional[str] = None


# ---------------------------------------------------------------------------
# Vista ordini da spedire
# ---------------------------------------------------------------------------

class OrdineDaSpedireResponse(BaseModel):
    ordine_id: str
    numero_ordine: str
    data_consegna: Optional[date]
    cliente: str                  # nickname || ragione_sociale
    cliente_id: str
    tipo_policy: Optional[str]
    corriere_suggerito: Optional[str]
    data_spedizione_suggerita: Optional[date]
    soglia_raggiunta: Optional[bool]      # solo per SOGLIA_VALORE: True se pronta per spedire
    flag_urgenza: bool
    evento_id: str                        # ID evento ordine_pronto


# ---------------------------------------------------------------------------
# Clienti con policy (vista logistica)
# ---------------------------------------------------------------------------

class ClienteLogisticaResponse(BaseModel):
    id: str
    codice_easyjob: str
    ragione_sociale: str
    nickname: Optional[str]
    email: Optional[str]
    ha_policy: bool
    tipo_policy: Optional[str]
    corriere_preferito: Optional[str]


class ClienteNicknamePatch(BaseModel):
    nickname: Optional[str] = None


# ---------------------------------------------------------------------------
# Spedizioni
# ---------------------------------------------------------------------------

class SpedizioneCreateRequest(BaseModel):
    ordine_id: str
    tipo: str                     # totale | parziale | urgenza
    corriere: Optional[str] = None
    data_pianificata: Optional[date] = None
    colli: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    note: Optional[str] = None


class SpedizionePatchRequest(BaseModel):
    corriere: Optional[str] = None
    data_pianificata: Optional[date] = None
    colli: Optional[int] = None
    peso_kg: Optional[Decimal] = None
    note: Optional[str] = None


class SpedizioneResponse(BaseModel):
    id: str
    ordine_id: str
    numero_ordine: Optional[str]  # da join
    cliente: Optional[str]        # da join
    tipo: str
    stato: str
    corriere: Optional[str]
    data_pianificata: Optional[date]
    data_spedizione: Optional[date]
    colli: Optional[int]
    peso_kg: Optional[Decimal]
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Calendario spedizioni
# ---------------------------------------------------------------------------

class CalendarioGiornoItem(BaseModel):
    data: date
    spedizioni: list[SpedizioneResponse]
