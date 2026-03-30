"""
Router articoli — Anagrafica articoli MRS.

GET   /api/articoli
GET   /api/articoli/{id}
PATCH /api/articoli/{id}   — aggiorna campi MRS-owned (mai i campi sync-owned)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.articolo import Articolo
from app.schemas.produzione import ArticoloResponse, ArticoloPatchRequest

router = APIRouter(
    prefix="/api/articoli",
    tags=["articoli"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[ArticoloResponse])
def list_articoli(
    q: Optional[str] = Query(None),                     # ricerca per codice
    famiglia: Optional[str] = Query(None),              # standard | speciali | barre
    tipo_produzione: Optional[str] = Query(None),
    storico_sufficiente: Optional[bool] = Query(None),
    session: Session = Depends(get_db),
):
    sql = text("""
        SELECT * FROM articoli
        WHERE (:q IS NULL                  OR codice_upper LIKE :q_like)
          AND (:tipo_produzione IS NULL    OR tipo_produzione = :tipo_produzione)
          AND (:storico_suff IS NULL       OR storico_sufficiente = :storico_suff)
          AND (
              :famiglia IS NULL
              OR (:famiglia = 'barre'    AND categoria IN ('M','L'))
              OR (:famiglia = 'speciali' AND (categoria = 'S' OR codice_upper LIKE 'S%'))
              OR (:famiglia = 'standard' AND categoria NOT IN ('M','L','S','0','Z','MC','U')
                                        AND codice_upper NOT LIKE 'S%'
                                        AND codice_upper NOT LIKE 'BCL%'
                                        AND codice_upper NOT LIKE 'CERT%'
                                        AND codice_upper NOT IN ('XS','CONF','0'))
          )
        ORDER BY codice
        LIMIT 200
    """)
    rows = session.execute(sql, {
        "q": q,
        "q_like": f"{(q or '').upper()}%",
        "tipo_produzione": tipo_produzione,
        "storico_suff": storico_sufficiente,
        "famiglia": famiglia,
    }).mappings().all()
    return [ArticoloResponse(**dict(r)) for r in rows]


@router.get("/{articolo_id}", response_model=ArticoloResponse)
def get_articolo(articolo_id: str, session: Session = Depends(get_db)):
    art = session.get(Articolo, articolo_id)
    if not art:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    return ArticoloResponse.model_validate(art)


@router.patch("/{articolo_id}", response_model=ArticoloResponse)
def patch_articolo(
    articolo_id: str,
    body: ArticoloPatchRequest,
    session: Session = Depends(get_db),
):
    """Aggiorna solo i campi MRS-owned dell'articolo. I campi sync (codice, descrizione, synced_at) non vengono mai toccati."""
    art = session.get(Articolo, articolo_id)
    if not art:
        raise HTTPException(status_code=404, detail="Articolo non trovato")

    updates = body.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(art, field, value)

    session.commit()
    session.refresh(art)
    return ArticoloResponse.model_validate(art)
