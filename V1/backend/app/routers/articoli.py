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
from app.utils import codice_sort_key

router = APIRouter(
    prefix="/api/articoli",
    tags=["articoli"],
    dependencies=[Depends(get_current_user)],
)

_SELECT_WITH_MP = """
    SELECT a.*,
           mp.codice AS materia_prima_codice,
           COALESCE(a.lunghezza_barra, mp.lunghezza_mm) AS lunghezza_effettiva
    FROM articoli a
    LEFT JOIN materie_prime mp ON mp.id = a.materia_prima_id
"""


@router.get("", response_model=list[ArticoloResponse])
def list_articoli(
    q: Optional[str] = Query(None),                     # ricerca per codice
    famiglia: Optional[str] = Query(None),              # standard | speciali | barre
    tipo_produzione: Optional[str] = Query(None),
    storico_sufficiente: Optional[bool] = Query(None),
    session: Session = Depends(get_db),
):
    sql = text(_SELECT_WITH_MP + """
        LEFT JOIN categorie_articolo ca ON ca.codice = a.categoria
        WHERE (:q IS NULL              OR a.codice_upper LIKE :q_like)
          AND (:tipo_produzione IS NULL OR a.tipo_produzione = :tipo_produzione)
          AND (:storico_suff IS NULL    OR a.storico_sufficiente = :storico_suff)
          AND (:famiglia IS NULL        OR ca.famiglia = :famiglia)
        ORDER BY a.codice
    """)
    rows = session.execute(sql, {
        "q": q,
        "q_like": f"{(q or '').upper()}%",
        "tipo_produzione": tipo_produzione,
        "storico_suff": storico_sufficiente,
        "famiglia": famiglia,
    }).mappings().all()
    result = [ArticoloResponse(**dict(r)) for r in rows]
    result.sort(key=lambda r: codice_sort_key(r.codice))
    return result


@router.get("/{articolo_id}/impegni-produzioni")
def get_impegni_produzioni(articolo_id: str, session: Session = Depends(get_db)):
    """
    Dati di dettaglio per il modal di lancio:
    - giacenza_attuale, impegni aperti, in_produzione, qty_disponibile_futura
    - Lista impegni (righe ordine aperte)
    - Lista produzioni attive (commesse non completate)
    """
    art_row = session.execute(
        text("SELECT giacenza_attuale FROM articoli WHERE id = :aid"),
        {"aid": articolo_id},
    ).fetchone()
    giacenza = int(art_row[0]) if art_row else 0

    impegni_rows = session.execute(
        text("""
            SELECT ro.id, o.numero_ordine,
                   COALESCE(c.nickname, c.ragione_sociale) AS cliente,
                   o.data_consegna,
                   (ro.qty_ordinata - ro.qty_consegnata) AS qty_da_evadere
            FROM righe_ordine ro
            JOIN ordini o  ON o.id = ro.ordine_id
            JOIN clienti c ON c.id = o.cliente_id
            WHERE ro.articolo_id = :aid
              AND ro.stato NOT IN ('spedito', 'chiuso')
              AND ro.qty_ordinata > ro.qty_consegnata
            ORDER BY o.data_consegna ASC NULLS LAST
        """),
        {"aid": articolo_id},
    ).mappings().all()

    impegni_totali = sum(int(r["qty_da_evadere"]) for r in impegni_rows)

    produzioni_rows = session.execute(
        text("""
            SELECT cm.id, cm.stato, cm.qty_cliente, cm.qty_scorta,
                   (cm.qty_cliente + cm.qty_scorta) AS qty_totale,
                   cm.created_at
            FROM commesse cm
            WHERE cm.articolo_id = :aid
              AND cm.stato NOT IN ('completata', 'annullata')
            ORDER BY cm.created_at DESC
        """),
        {"aid": articolo_id},
    ).mappings().all()

    in_produzione = sum(int(r["qty_totale"]) for r in produzioni_rows)
    qty_disponibile_futura = max(0, giacenza - impegni_totali)

    return {
        "giacenza_attuale": giacenza,
        "impegni_totali": impegni_totali,
        "in_produzione": in_produzione,
        "qty_disponibile_futura": qty_disponibile_futura,
        "impegni": [
            {
                "riga_id": r["id"],
                "numero_ordine": r["numero_ordine"],
                "cliente": r["cliente"],
                "data_consegna": r["data_consegna"].isoformat() if r["data_consegna"] else None,
                "qty_da_evadere": int(r["qty_da_evadere"]),
            }
            for r in impegni_rows
        ],
        "produzioni_attive": [
            {
                "commessa_id": r["id"],
                "stato": r["stato"],
                "qty_cliente": r["qty_cliente"],
                "qty_scorta": r["qty_scorta"],
                "qty_totale": int(r["qty_totale"]),
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in produzioni_rows
        ],
    }


@router.get("/{articolo_id}", response_model=ArticoloResponse)
def get_articolo(articolo_id: str, session: Session = Depends(get_db)):
    row = session.execute(
        text(_SELECT_WITH_MP + " WHERE a.id = :id"),
        {"id": articolo_id},
    ).mappings().fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    return ArticoloResponse(**dict(row))


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

    # exclude_unset=True: gestisce anche null espliciti (es. materia_prima_id=null per rimuovere)
    updates = body.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(art, field, value)

    session.commit()
    row = session.execute(
        text(_SELECT_WITH_MP + " WHERE a.id = :id"),
        {"id": articolo_id},
    ).mappings().fetchone()
    return ArticoloResponse(**dict(row))
