"""
Router eventi — Comunicazioni inter-reparto.

Logistica crea urgenze → Produzione vede e risponde con feedback → Logistica risolve.

GET  /api/eventi                        — lista eventi (filtri: tipo, destinatario, stato, ordine)
GET  /api/eventi/{id}                   — dettaglio evento
POST /api/eventi/urgenza                — logistica crea urgenza_formale su un ordine
POST /api/eventi/{id}/feedback          — produzione risponde all'urgenza
POST /api/eventi/{id}/risolvi           — segna evento come risolto
POST /api/eventi/{id}/rifiuta           — rifiuta/annulla evento
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.schemas.evento import (
    EventoResponse,
    UrgenzaRequest,
    FeedbackRequest,
    RisolviRequest,
)
from app.services import eventi as svc_ev

router = APIRouter(
    prefix="/api/eventi",
    tags=["eventi"],
    dependencies=[Depends(get_current_user)],
)


# ---------------------------------------------------------------------------
# Lista e dettaglio
# ---------------------------------------------------------------------------

@router.get("", response_model=list[EventoResponse])
def get_eventi(
    tipo: Optional[str] = Query(None),
    destinatario: Optional[str] = Query(None),
    stato: Optional[str] = Query(None),
    ref_ordine_id: Optional[str] = Query(None),
    session: Session = Depends(get_db),
):
    """Lista eventi con filtri opzionali."""
    return svc_ev.get_eventi(
        session,
        tipo=tipo,
        destinatario=destinatario,
        stato=stato,
        ref_ordine_id=ref_ordine_id,
    )


@router.get("/{evento_id}", response_model=EventoResponse)
def get_evento(evento_id: str, session: Session = Depends(get_db)):
    detail = svc_ev.get_evento_detail(session, evento_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Evento non trovato")
    return detail


# ---------------------------------------------------------------------------
# Urgenza formale (logistica → produzione)
# ---------------------------------------------------------------------------

@router.post("/urgenza", response_model=EventoResponse, status_code=201)
def crea_urgenza(body: UrgenzaRequest, session: Session = Depends(get_db)):
    """
    Crea urgenza_formale su un ordine.
    La coda di lavorazione viene ricalcolata automaticamente.
    """
    try:
        return svc_ev.crea_urgenza(
            session,
            ordine_id=body.ordine_id,
            nota=body.nota,
            created_by=body.created_by,
        )
    except svc_ev.EventoError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Feedback urgenza (produzione → logistica)
# ---------------------------------------------------------------------------

@router.post("/{evento_id}/feedback", response_model=EventoResponse)
def dai_feedback(
    evento_id: str,
    body: FeedbackRequest,
    session: Session = Depends(get_db),
):
    """
    La produzione risponde a un'urgenza:
    - accettata: la produzione accelererà
    - non_fattibile: impossibile rispettare la scadenza (con nota e data prevista realistica)
    """
    try:
        return svc_ev.dai_feedback(
            session,
            evento_id=evento_id,
            feedback_stato=body.feedback_stato,
            feedback_data_prevista=body.feedback_data_prevista,
            feedback_nota=body.feedback_nota,
            corriere_override=body.corriere_override,
        )
    except svc_ev.EventoError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---------------------------------------------------------------------------
# Risolvi / Rifiuta
# ---------------------------------------------------------------------------

@router.post("/{evento_id}/risolvi", response_model=EventoResponse)
def risolvi(
    evento_id: str,
    body: RisolviRequest,
    session: Session = Depends(get_db),
):
    """
    Segna l'evento come risolto.
    Per urgenze: ricalcola la coda (l'urgenza non è più attiva).
    """
    try:
        return svc_ev.risolvi_evento(session, evento_id, nota=body.nota)
    except svc_ev.EventoError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{evento_id}/rifiuta", response_model=EventoResponse)
def rifiuta(
    evento_id: str,
    body: RisolviRequest,
    session: Session = Depends(get_db),
):
    """Rifiuta o annulla un evento aperto."""
    try:
        return svc_ev.rifiuta_evento(session, evento_id, nota=body.nota)
    except svc_ev.EventoError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
