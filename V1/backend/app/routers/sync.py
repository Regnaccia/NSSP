"""
Router sync: stato e controllo sync EasyJob → MRS.

Endpoints:
  GET  /api/sync/status           — stato sync tutte le tabelle
  POST /api/sync/force/{tabella}  — forza sync immediato
  POST /api/sync/force-all        — forza sync completo
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.sync_log import SyncLog
from app.sync.handlers import sync_tabella, sync_all, HANDLER_MAP
from app.sync.easyjob import test_easyjob_connection

router = APIRouter(
    prefix="/api/sync",
    tags=["sync"],
    dependencies=[Depends(require_admin)],
)


@router.get("/status")
def get_sync_status(session: Session = Depends(get_db)):
    """
    Ritorna lo stato di sync per ogni tabella + stato connessione EasyJob.

    Frontend usa last_sync_at per determinare il colore indicatore:
    - verde  < 10 min
    - giallo 10–30 min
    - rosso  > 30 min o last_error non null
    """
    logs = session.query(SyncLog).all()
    easyjob_ok = test_easyjob_connection()

    return {
        "easyjob_connesso": easyjob_ok,
        "tabelle": [
            {
                "tabella": log.tabella,
                "last_sync_at": log.last_sync_at.isoformat() if log.last_sync_at else None,
                "last_error": log.last_error,
                "records_updated": log.records_updated,
                "sync_duration_ms": log.sync_duration_ms,
            }
            for log in logs
        ],
    }


@router.post("/force/{tabella}")
def force_sync_tabella(tabella: str, session: Session = Depends(get_db)):
    """Forza sync immediato di una tabella specifica."""
    if tabella not in HANDLER_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Tabella '{tabella}' non supportata. Tabelle valide: {list(HANDLER_MAP.keys())}",
        )
    try:
        records = sync_tabella(session, tabella)
        return {"tabella": tabella, "records_updated": records, "status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/force-all")
def force_sync_all(session: Session = Depends(get_db)):
    """Forza sync completo di tutte le tabelle (in ordine dipendenze)."""
    try:
        results = sync_all(session)
        return {"status": "ok", "results": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
