from datetime import date, datetime
from pydantic import BaseModel, field_validator
from typing import Optional


# ---------------------------------------------------------------------------
# F1a — Righe ordine da processare
# ---------------------------------------------------------------------------

class RigaF1aResponse(BaseModel):
    riga_ordine_id: str
    ordine_id: str
    articolo_id: str
    numero_ordine: str
    data_consegna: Optional[date]
    flag_data_scaduta: bool           # data_consegna < today
    flag_urgenza: bool                # evento urgenza_formale aperto su questo ordine

    codice_articolo: str
    descrizione_articolo: Optional[str]
    categoria: Optional[str]          # CAT_ART1 da EasyJob (M/L=barre, S=speciali, ...)

    cliente: str                      # nickname || ragione_sociale (DL-ARCH-017)
    cliente_id: str

    qty_ordinata: int
    qty_disponibile: int
    qty_in_produzione: int
    giacenza_attuale: int             # stock magazzino articolo (da MAG_REALE)
    qty_da_produrre: int              # calcolato live

    # Parametri produzione (da articoli + materie_prime)
    tipo_produzione: str
    multipli_taglio: Optional[int]
    mm_materiale: Optional[int]
    lunghezza_barra: Optional[int]        # override manuale
    lunghezza_effettiva: Optional[int]    # = lunghezza_barra ?? materia_prima.lunghezza_mm
    materia_prima_id: Optional[str]
    materia_prima_codice: Optional[str]
    capienza: Optional[int]

    # Flag warning
    flag_no_materia: bool                 # materia_prima_id IS NULL (tutti i tipi)

    # Qty suggerita calcolata (calcola_lotti)
    nr_lotti: int
    pezzi_per_lotto: int
    qty_suggerita: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# F1a — Richiesta genera commesse
# ---------------------------------------------------------------------------

class RigaSelezionataInput(BaseModel):
    riga_ordine_id: Optional[str] = None       # None per righe scorta pura (F1b)
    articolo_id: Optional[str] = None          # richiesto se riga_ordine_id è None
    qty_ciclo_corrente: Optional[int] = None   # None = tutto il residuo
    qty_scorta: int = 0


class GeneraCommesseRequest(BaseModel):
    righe: list[RigaSelezionataInput]
    created_by: Optional[str] = None


class GeneraCommesseResponse(BaseModel):
    commesse_create: int
    file_csv_base64: str              # CSV semicolon-delimited encodato base64 per download frontend


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
    giacenza_attuale: int

    # Parametri produzione (da articoli + materie_prime)
    multipli_taglio: Optional[int]
    mm_materiale: Optional[int]
    lunghezza_barra: Optional[int]
    lunghezza_effettiva: Optional[int]
    materia_prima_id: Optional[str]
    materia_prima_codice: Optional[str]
    capienza: Optional[int]

    # Flag warning
    flag_no_materia: bool

    # Qty suggerita calcolata (calcola_lotti)
    nr_lotti: int
    pezzi_per_lotto: int
    qty_suggerita: int

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
# Materie prime
# ---------------------------------------------------------------------------

class MateriaPrimaResponse(BaseModel):
    id: str
    codice: str
    descrizione: Optional[str]
    lunghezza_mm: Optional[int]
    synced_at: datetime

    class Config:
        from_attributes = True


class MateriaPrimaPatchRequest(BaseModel):
    lunghezza_mm: Optional[int] = None


# ---------------------------------------------------------------------------
# Articoli — PATCH body
# ---------------------------------------------------------------------------

class ArticoloPatchRequest(BaseModel):
    mesi_scorta: Optional[int] = None
    tipo_produzione: Optional[str] = None
    multipli_taglio: Optional[int] = None
    capienza: Optional[int] = None
    prd_pari: Optional[bool] = None
    lunghezza_barra: Optional[int] = None       # override manuale sulla lunghezza
    mm_materiale: Optional[int] = None
    materia_prima_id: Optional[str] = None


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
    materia_prima_id: Optional[str]
    materia_prima_codice: Optional[str] = None    # join, non su articoli
    lunghezza_barra: Optional[int]                # override manuale
    lunghezza_effettiva: Optional[int] = None     # = lunghezza_barra ?? materia_prima.lunghezza_mm
    multipli_taglio: Optional[int]
    mm_materiale: Optional[int]
    prd_pari: bool
    synced_at: datetime

    class Config:
        from_attributes = True
