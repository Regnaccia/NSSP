"""
Router reparto — Terminale Reparto Produzione.

L'operatore usa questo router dal tablet/terminale in reparto per:
  - vedere le commesse assegnate alla sua macchina
  - avviare/sospendere/riprendere/completare una commessa
  - aggiornare le qty prodotte durante la lavorazione

GET  /api/reparto/macchine                        — lista macchine (selezione all'avvio)
GET  /api/reparto/macchine/{macchina_id}/coda     — commesse assegnate a quella macchina
GET  /api/reparto/commesse/{commessa_id}          — dettaglio singola commessa
POST /api/reparto/commesse/{commessa_id}/avvia    — in_coda → in_produzione
POST /api/reparto/commesse/{commessa_id}/sospendi — in_produzione → sospesa
POST /api/reparto/commesse/{commessa_id}/riprendi — sospesa → in_produzione
POST /api/reparto/commesse/{commessa_id}/aggiorna-qty
POST /api/reparto/commesse/{commessa_id}/completa — in_produzione → completata
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.macchina import Macchina
from app.schemas.commessa import (
    CommessaResponse,
    MacchinaResponse,
    SospendiRequest,
    AggiornaQtyRequest,
)
from app.services import commesse as svc_commesse

router = APIRouter(prefix="/api/reparto", tags=["reparto"])


# ---------------------------------------------------------------------------
# Macchine
# ---------------------------------------------------------------------------

@router.get("/macchine", response_model=list[MacchinaResponse])
def get_macchine(session: Session = Depends(get_db)):
    """Lista macchine attive (per selezione operatore all'avvio del terminale)."""
    macchine = (
        session.query(Macchina)
        .filter(Macchina.attiva.is_(True))
        .order_by(Macchina.codice)
        .all()
    )
    return [MacchinaResponse.model_validate(m) for m in macchine]


# ---------------------------------------------------------------------------
# Coda macchina
# ---------------------------------------------------------------------------

@router.get("/macchine/{macchina_id}/coda", response_model=list[CommessaResponse])
def get_coda_macchina(macchina_id: str, session: Session = Depends(get_db)):
    """Commesse assegnate a questa macchina, non ancora completate."""
    macchina = session.get(Macchina, macchina_id)
    if not macchina:
        raise HTTPException(status_code=404, detail="Macchina non trovata")
    return svc_commesse.get_commesse_macchina(session, macchina_id)


# ---------------------------------------------------------------------------
# Dettaglio commessa
# ---------------------------------------------------------------------------

@router.get("/commesse/{commessa_id}", response_model=CommessaResponse)
def get_commessa(commessa_id: str, session: Session = Depends(get_db)):
    detail = svc_commesse.get_commessa_detail(session, commessa_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Commessa non trovata")
    return detail


# ---------------------------------------------------------------------------
# Transizioni stato
# ---------------------------------------------------------------------------

@router.post("/commesse/{commessa_id}/avvia", response_model=CommessaResponse)
def avvia(commessa_id: str, session: Session = Depends(get_db)):
    """Avvia lavorazione: in_coda → in_produzione."""
    try:
        return svc_commesse.transizione(session, commessa_id, "avvia")
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/commesse/{commessa_id}/sospendi", response_model=CommessaResponse)
def sospendi(
    commessa_id: str,
    body: SospendiRequest,
    session: Session = Depends(get_db),
):
    """Sospende lavorazione: in_produzione → sospesa."""
    try:
        return svc_commesse.transizione(session, commessa_id, "sospendi", nota=body.nota)
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/commesse/{commessa_id}/riprendi", response_model=CommessaResponse)
def riprendi(commessa_id: str, session: Session = Depends(get_db)):
    """Riprende lavorazione: sospesa → in_produzione."""
    try:
        return svc_commesse.transizione(session, commessa_id, "riprendi")
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/commesse/{commessa_id}/completa", response_model=CommessaResponse)
def completa(commessa_id: str, session: Session = Depends(get_db)):
    """Completa lavorazione: in_produzione → completata."""
    try:
        return svc_commesse.transizione(session, commessa_id, "completa")
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---------------------------------------------------------------------------
# Aggiornamento qty prodotte
# ---------------------------------------------------------------------------

@router.post("/commesse/{commessa_id}/aggiorna-qty", response_model=CommessaResponse)
def aggiorna_qty(
    commessa_id: str,
    body: AggiornaQtyRequest,
    session: Session = Depends(get_db),
):
    """Aggiorna le quantità prodotte durante la lavorazione."""
    try:
        return svc_commesse.aggiorna_qty(
            session,
            commessa_id,
            qty_prodotta_cliente=body.qty_prodotta_cliente,
            qty_prodotta_scorta=body.qty_prodotta_scorta,
        )
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
