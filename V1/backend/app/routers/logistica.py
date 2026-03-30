"""
Router Logistica — Ufficio Logistica.

Gestione spedizioni, policy cliente, calendario.

GET  /api/logistica/da-spedire                  — ordini pronti con policy e data suggerita
GET  /api/logistica/clienti                     — lista clienti con policy
PATCH /api/logistica/clienti/{id}               — aggiorna nickname cliente
GET  /api/logistica/clienti/{id}/policy         — policy di un cliente
PUT  /api/logistica/clienti/{id}/policy         — configura/aggiorna policy
POST /api/logistica/spedizioni                  — crea spedizione
GET  /api/logistica/spedizioni                  — lista spedizioni (filtri: stato, cliente_id)
GET  /api/logistica/spedizioni/{id}             — dettaglio spedizione
PATCH /api/logistica/spedizioni/{id}            — aggiorna spedizione
POST /api/logistica/spedizioni/{id}/spedita     — segna come spedita
GET  /api/logistica/calendario                  — vista calendario spedizioni pianificate
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.logistica import (
    PolicyClienteResponse,
    PolicyClienteRequest,
    OrdineDaSpedireResponse,
    ClienteLogisticaResponse,
    ClienteNicknamePatch,
    SpedizioneCreateRequest,
    SpedizionePatchRequest,
    SpedizioneResponse,
    CalendarioGiornoItem,
)
from app.deps import require_ruolo
from app.services import logistica as svc_log

router = APIRouter(
    prefix="/api/logistica",
    tags=["logistica"],
    dependencies=[Depends(require_ruolo("logistica"))],
)


# ---------------------------------------------------------------------------
# Ordini da spedire
# ---------------------------------------------------------------------------

@router.get("/da-spedire", response_model=list[OrdineDaSpedireResponse])
def get_da_spedire(session: Session = Depends(get_db)):
    """Ordini con evento ordine_pronto aperto, arricchiti con policy e data suggerita."""
    return svc_log.get_ordini_da_spedire(session)


# ---------------------------------------------------------------------------
# Clienti
# ---------------------------------------------------------------------------

@router.get("/clienti", response_model=list[ClienteLogisticaResponse])
def get_clienti(session: Session = Depends(get_db)):
    """Lista clienti con indicazione policy configurata."""
    return svc_log.get_clienti_con_policy(session)


@router.patch("/clienti/{cliente_id}", status_code=204)
def patch_nickname(
    cliente_id: str,
    body: ClienteNicknamePatch,
    session: Session = Depends(get_db),
):
    """Aggiorna il nickname operativo di un cliente (MRS-owned)."""
    try:
        svc_log.aggiorna_nickname(session, cliente_id, body.nickname)
    except svc_log.LogisticaError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Policy cliente
# ---------------------------------------------------------------------------

@router.get("/clienti/{cliente_id}/policy", response_model=PolicyClienteResponse)
def get_policy(cliente_id: str, session: Session = Depends(get_db)):
    policy = svc_log.get_policy(session, cliente_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy non configurata per questo cliente")
    return dict(policy)


@router.put("/clienti/{cliente_id}/policy", response_model=PolicyClienteResponse)
def upsert_policy(
    cliente_id: str,
    body: PolicyClienteRequest,
    session: Session = Depends(get_db),
):
    """Crea o aggiorna la policy di spedizione di un cliente."""
    try:
        result = svc_log.upsert_policy(session, cliente_id, body.model_dump(exclude_none=True))
        return dict(result)
    except svc_log.LogisticaError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Spedizioni
# ---------------------------------------------------------------------------

@router.post("/spedizioni", response_model=SpedizioneResponse, status_code=201)
def crea_spedizione(body: SpedizioneCreateRequest, session: Session = Depends(get_db)):
    """Crea una nuova spedizione per un ordine."""
    try:
        return svc_log.crea_spedizione(session, body.model_dump(exclude_none=True))
    except svc_log.LogisticaError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/spedizioni", response_model=list[SpedizioneResponse])
def get_spedizioni(
    stato: Optional[str] = Query(None),
    cliente_id: Optional[str] = Query(None),
    session: Session = Depends(get_db),
):
    """Lista spedizioni con filtri opzionali."""
    return svc_log.get_spedizioni(session, stato=stato, cliente_id=cliente_id)


@router.get("/spedizioni/{spedizione_id}", response_model=SpedizioneResponse)
def get_spedizione(spedizione_id: str, session: Session = Depends(get_db)):
    rows = svc_log.get_spedizioni(session)
    match = next((s for s in rows if s["id"] == spedizione_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Spedizione non trovata")
    return match


@router.patch("/spedizioni/{spedizione_id}", response_model=SpedizioneResponse)
def aggiorna_spedizione(
    spedizione_id: str,
    body: SpedizionePatchRequest,
    session: Session = Depends(get_db),
):
    """Aggiorna corriere, data pianificata, colli, peso di una spedizione."""
    try:
        return svc_log.aggiorna_spedizione(
            session, spedizione_id, body.model_dump(exclude_none=True)
        )
    except svc_log.LogisticaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/spedizioni/{spedizione_id}/spedita", response_model=SpedizioneResponse)
def segna_spedita(spedizione_id: str, session: Session = Depends(get_db)):
    """Segna la spedizione come spedita (data_spedizione = oggi)."""
    try:
        return svc_log.segna_spedita(session, spedizione_id)
    except svc_log.LogisticaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# ---------------------------------------------------------------------------
# Calendario
# ---------------------------------------------------------------------------

@router.get("/calendario", response_model=list[CalendarioGiornoItem])
def get_calendario(
    data_da: date = Query(default_factory=date.today),
    data_a: date = Query(default_factory=lambda: date.today().replace(day=28)),
    session: Session = Depends(get_db),
):
    """Vista calendario spedizioni pianificate in un range di date."""
    if data_a < data_da:
        raise HTTPException(status_code=400, detail="data_a deve essere >= data_da")
    return svc_log.get_calendario(session, data_da, data_a)
