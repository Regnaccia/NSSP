"""
Router Magazzino — Terminale Magazzino.

GET  /api/magazzino/da-approntare                    — ordini con commesse completate da approntare
POST /api/magazzino/consegne                         — registra consegna da commessa completata
GET  /api/magazzino/ordini/{ordine_id}/consegne      — consegne registrate per un ordine
POST /api/magazzino/ordini/{ordine_id}/pronto        — segnala ordine pronto alla logistica
"""
from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.magazzino import (
    OrdineApprontareResponse,
    ArticoloProntoItem,
    RegistraConsegnaRequest,
    ConsegnaResponse,
    OrdineProontoRequest,
    EventoResponse,
)
from app.services import magazzino as svc_mag

router = APIRouter(prefix="/api/magazzino", tags=["magazzino"])


# ---------------------------------------------------------------------------
# Vista ordini da approntare
# ---------------------------------------------------------------------------

@router.get("/da-approntare", response_model=list[OrdineApprontareResponse])
def get_da_approntare(session: Session = Depends(get_db)):
    """Ordini con commesse completate non ancora interamente registrate in consegna."""
    raw = svc_mag.get_ordini_da_approntare(session)
    result = []
    for o in raw:
        articoli = [ArticoloProntoItem(**a) for a in o["articoli"]]
        result.append(OrdineApprontareResponse(
            ordine_id=o["ordine_id"],
            numero_ordine=o["numero_ordine"],
            data_consegna=o["data_consegna"],
            cliente=o["cliente"],
            cliente_id=o["cliente_id"],
            flag_urgenza=o["flag_urgenza"],
            articoli=articoli,
            tutte_registrate=o["tutte_registrate"],
        ))
    return result


# ---------------------------------------------------------------------------
# Registra consegna
# ---------------------------------------------------------------------------

@router.post("/consegne", response_model=ConsegnaResponse, status_code=201)
def registra_consegna(body: RegistraConsegnaRequest, session: Session = Depends(get_db)):
    """
    Registra che il magazzino ha messo da parte i pezzi di una commessa completata.
    """
    try:
        return svc_mag.registra_consegna(
            session,
            commessa_id=body.commessa_id,
            qty_cliente=body.qty_cliente,
            qty_scorta=body.qty_scorta,
        )
    except svc_mag.MagazzinoError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---------------------------------------------------------------------------
# Consegne di un ordine
# ---------------------------------------------------------------------------

@router.get("/ordini/{ordine_id}/consegne", response_model=list[ConsegnaResponse])
def get_consegne_ordine(ordine_id: str, session: Session = Depends(get_db)):
    """Lista consegne magazzino registrate per un ordine specifico."""
    return svc_mag.get_consegne_ordine(session, ordine_id)


# ---------------------------------------------------------------------------
# Segnala ordine pronto per logistica
# ---------------------------------------------------------------------------

@router.post("/ordini/{ordine_id}/pronto", response_model=EventoResponse, status_code=201)
def segna_pronto(
    ordine_id: str,
    body: OrdineProontoRequest,
    session: Session = Depends(get_db),
):
    """
    Crea evento ordine_pronto destinato alla logistica.
    Idempotente: se l'evento esiste già, lo ritorna senza crearne un duplicato.
    """
    try:
        ev = svc_mag.segna_ordine_pronto(
            session,
            ordine_id=ordine_id,
            nota=body.nota,
            created_by=body.created_by,
        )
        return EventoResponse(
            id=ev.id,
            tipo=ev.tipo,
            mittente=ev.mittente,
            destinatario=ev.destinatario,
            stato=ev.stato,
            nota=ev.nota,
            ref_ordine_id=ev.ref_ordine_id,
            created_at=ev.created_at,
        )
    except svc_mag.MagazzinoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
