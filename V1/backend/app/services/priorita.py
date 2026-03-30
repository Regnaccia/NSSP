"""
Calcolo priorità e posizione coda per le commesse in_coda.

Algoritmo:
  1. Commesse con evento urgenza_formale aperto → top (priorita_suggerita=1)
  2. Poi data_consegna ASC (prima le più vicine)
  3. Poi FIFO (created_at ASC)
  4. Commesse senza riga ordine (pure scorta) → in coda al fondo

Il risultato aggiorna commesse.posizione_coda e commesse.priorita_suggerita.
Commesse in_produzione e sospesa NON vengono riposizionate (mantengono il loro slot).
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def ricalcola_coda(session: Session) -> int:
    """
    Ricalcola posizione_coda per tutte le commesse in_coda.
    Ritorna il numero di commesse aggiornate.
    """
    rows = session.execute(text("""
        SELECT
            c.id,
            c.created_at,
            o.data_consegna,
            EXISTS (
                SELECT 1 FROM eventi e
                WHERE e.ref_ordine_id = ro.ordine_id
                  AND e.tipo = 'urgenza_formale'
                  AND e.stato = 'aperto'
            ) AS flag_urgenza
        FROM commesse c
        LEFT JOIN righe_ordine ro ON ro.id = c.riga_ordine_id
        LEFT JOIN ordini o        ON o.id  = ro.ordine_id
        WHERE c.stato = 'in_coda'
        ORDER BY
            flag_urgenza DESC,
            o.data_consegna ASC NULLS LAST,
            c.created_at ASC
    """)).mappings().all()

    for pos, r in enumerate(rows, start=1):
        priorita = 1 if r["flag_urgenza"] else 2
        session.execute(
            text("""
                UPDATE commesse
                   SET posizione_coda      = :pos,
                       priorita_suggerita  = :prio
                 WHERE id = :cid
            """),
            {"pos": pos, "prio": priorita, "cid": r["id"]},
        )

    session.commit()
    return len(rows)
