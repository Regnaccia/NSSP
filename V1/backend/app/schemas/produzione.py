from datetime import date, datetime
from pydantic import BaseModel, field_validator
from typing import Optional


# ---------------------------------------------------------------------------
# F1a — Righe ordine da processare
# ---------------------------------------------------------------------------

class RigaF1aResponse(BaseModel):
    riga_ordine_id: str
    ordine_id: str
    numero_ordine: str
    data_consegna: Optional[date]
    flag_data_scaduta: bool           # data_consegna < today
    flag_urgenza: bool                # evento urgenza_formale aperto su questo ordine

    codice_articolo: str
    descrizione_articolo: Optional[str]

    cliente: str                      # nickname || ragione_sociale (DL-ARCH-017)
    cliente_id: str

    qty_ordinata: int
    qty_disponibile: int
    qty_in_produzione: int
    giacenza_attuale: int             # stock magazzino articolo (da MAG_REALE)
    qty_da_produrre: int              # calcolato live

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# F1a — Richiesta genera commesse
# ---------------------------------------------------------------------------

class RigaSelezionataInput(BaseModel):
    riga_ordine_id: str
    qty_ciclo_corrente: Optional[int] = None   # None = tutto il residuo
    qty_scorta: int = 0


class GeneraCommesseRequest(BaseModel):
    righe: list[RigaSelezionataInput]
    created_by: Optional[str] = None


class GeneraCommesseResponse(BaseModel):
    commesse_create: int
    file_excel_base64: str            # file Excel encodato base64 per download frontend


# ---------------------------------------------------------------------------
# F1b — Articoli sotto scorta target
# ---------------------------------------------------------------------------

class ArticoloF1bResponse(BaseModel):
    articolo_id: str
    codice: str
    descrizione: Optional[str]
    tipo_produzione: str

    scorta_mensile: int
    mesi_scorta: int
    target_scorta: int                # scorta_mensile * mesi_scorta
    qty_disponibile_futura: int       # calcolato live
    qty_da_produrre_scorta: int       # target_scorta - qty_disponibile_futura
    scorta_calcolata_at: Optional[datetime]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# F1b — Richiesta ricalcolo scorte
# ---------------------------------------------------------------------------

class RicalcolaScorteRequest(BaseModel):
    articolo_id: Optional[str] = None   # None = tutti gli articoli


class RicalcolaScorteResponse(BaseModel):
    aggiornati: int


# ---------------------------------------------------------------------------
# Articoli — PATCH body
# ---------------------------------------------------------------------------

class ArticoloPatchRequest(BaseModel):
    mesi_scorta: Optional[int] = None
    tipo_produzione: Optional[str] = None
    multipli_taglio: Optional[int] = None
    capienza: Optional[int] = None
    prd_pari: Optional[bool] = None
    lunghezza_barra: Optional[int] = None


class ArticoloResponse(BaseModel):
    id: str
    codice: str
    descrizione: Optional[str]
    categoria: Optional[str]
    tipo_produzione: str
    scorta_mensile: int
    mesi_scorta: int
    storico_sufficiente: bool
    scorta_calcolata_at: Optional[datetime]
    capienza: Optional[int]
    giacenza_attuale: int = 0
    lunghezza_barra: Optional[int]
    multipli_taglio: Optional[int]
    prd_pari: bool
    synced_at: datetime

    class Config:
        from_attributes = True
