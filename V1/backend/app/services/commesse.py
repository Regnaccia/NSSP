"""
State machine per le commesse.

Transizioni valide:
  in_coda       → in_produzione  (avvia)
  in_produzione → sospesa        (sospendi)
  sospesa       → in_produzione  (riprendi)
  in_produzione → completata     (completa)
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.commessa import Commessa


TRANSIZIONI_VALIDE: dict[str, tuple[str, str]] = {
    "avvia":    ("in_coda",       "in_produzione"),
    "sospendi": ("in_produzione", "sospesa"),
    "riprendi": ("sospesa",       "in_produzione"),
    "completa": ("in_produzione", "completata"),
}


class CommessaError(Exception):
    pass


# ---------------------------------------------------------------------------
# Helpers interni
# ---------------------------------------------------------------------------

def _get_or_raise(session: Session, commessa_id: str) -> Commessa:
    c = session.get(Commessa, commessa_id)
    if not c:
        raise CommessaError(f"Commessa {commessa_id} non trovata")
    return c


def _row_to_dict(r) -> dict:
    qty_totale = (r["qty_cliente"] or 0) + (r["qty_scorta"] or 0)
    qty_prodotta = (r["qty_prodotta_cliente"] or 0) + (r["qty_prodotta_scorta"] or 0)
    return {
        **dict(r),
        "qty_totale": qty_totale,
        "qty_residua": max(0, qty_totale - qty_prodotta),
    }


_BASE_SQL = """
    SELECT
        c.id, c.stato, c.posizione_coda, c.priorita_suggerita,
        c.qty_cliente, c.qty_scorta, c.qty_prodotta_cliente, c.qty_prodotta_scorta,
        c.qty_ciclo_corrente, c.created_at, c.created_by,
        c.sospesa_at, c.sospesa_nota, c.completata_at, c.ldp_easyjob,
        c.riga_ordine_id, c.articolo_id, c.macchina_id,
        a.codice  AS codice_articolo,
        a.descrizione AS descrizione_articolo,
        m.codice  AS macchina_codice,
        o.numero_ordine
    FROM commesse c
    JOIN articoli a       ON a.id = c.articolo_id
    LEFT JOIN macchine m  ON m.id = c.macchina_id
    LEFT JOIN righe_ordine ro ON ro.id = c.riga_ordine_id
    LEFT JOIN ordini o    ON o.id = ro.ordine_id
"""


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

def get_commesse_attive(session: Session) -> list[dict]:
    """Commesse in_coda, in_produzione, sospesa ordinate per posizione coda."""
    rows = session.execute(text(
        _BASE_SQL + """
        WHERE c.stato IN ('in_coda', 'in_produzione', 'sospesa')
        ORDER BY c.posizione_coda NULLS LAST, c.created_at
        """
    )).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_commesse_macchina(session: Session, macchina_id: str) -> list[dict]:
    """Commesse assegnate a una macchina specifica, non completate."""
    rows = session.execute(
        text(_BASE_SQL + """
        WHERE c.macchina_id = :mid
          AND c.stato IN ('in_coda', 'in_produzione', 'sospesa')
        ORDER BY c.posizione_coda NULLS LAST, c.created_at
        """),
        {"mid": macchina_id},
    ).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_commessa_detail(session: Session, commessa_id: str) -> dict | None:
    row = session.execute(
        text(_BASE_SQL + "WHERE c.id = :cid"),
        {"cid": commessa_id},
    ).mappings().fetchone()
    return _row_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# Mutazioni state machine
# ---------------------------------------------------------------------------

def transizione(session: Session, commessa_id: str, azione: str, **kwargs) -> dict:
    """Esegue una transizione di stato e ritorna il dict aggiornato."""
    stato_da, stato_a = TRANSIZIONI_VALIDE[azione]
    c = _get_or_raise(session, commessa_id)

    if c.stato != stato_da:
        raise CommessaError(
            f"Transizione '{azione}' non valida: stato corrente='{c.stato}', atteso='{stato_da}'"
        )

    now = datetime.now(timezone.utc)
    c.stato = stato_a

    if azione == "sospendi":
        c.sospesa_at = now
        c.sospesa_nota = kwargs.get("nota")
    elif azione == "riprendi":
        c.sospesa_at = None
        c.sospesa_nota = None
    elif azione == "completa":
        c.completata_at = now

    session.commit()
    detail = get_commessa_detail(session, commessa_id)
    return detail  # type: ignore[return-value]


def assegna_macchina(session: Session, commessa_id: str, macchina_id: str) -> dict:
    """Assegna una macchina alla commessa (solo se in_coda o sospesa)."""
    c = _get_or_raise(session, commessa_id)
    if c.stato not in ("in_coda", "sospesa"):
        raise CommessaError(
            f"Impossibile assegnare macchina: commessa in stato '{c.stato}'"
        )
    c.macchina_id = macchina_id
    session.commit()
    return get_commessa_detail(session, commessa_id)  # type: ignore[return-value]


def aggiorna_qty(
    session: Session,
    commessa_id: str,
    qty_prodotta_cliente: int | None,
    qty_prodotta_scorta: int | None,
) -> dict:
    """Aggiorna le qty prodotte (solo se in_produzione o sospesa)."""
    c = _get_or_raise(session, commessa_id)
    if c.stato not in ("in_produzione", "sospesa"):
        raise CommessaError(
            f"Impossibile aggiornare qty: commessa in stato '{c.stato}'"
        )
    if qty_prodotta_cliente is not None:
        c.qty_prodotta_cliente = max(0, qty_prodotta_cliente)
    if qty_prodotta_scorta is not None:
        c.qty_prodotta_scorta = max(0, qty_prodotta_scorta)

    session.commit()
    return get_commessa_detail(session, commessa_id)  # type: ignore[return-value]
