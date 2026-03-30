"""
services/disponibilita.py — Computed facts meccanici (DL-ARCH-007).

Tutte le funzioni qui sono calcolate LIVE — nessun dato viene persistito
tranne giacenza e impegni già presenti nelle tabelle sync-owned.

Riusato da: routers/produzione (F1a, F1b), routers/magazzino (Fase 3+).
"""
from datetime import date
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.riga_ordine import RigaOrdine


# ---------------------------------------------------------------------------
# F1a: qty_da_produrre per riga singola
# ---------------------------------------------------------------------------

def get_qty_da_produrre(riga: RigaOrdine) -> int:
    """Quantità ancora da produrre per questa riga ordine."""
    return max(0, riga.qty_ordinata - riga.qty_disponibile - riga.qty_in_produzione)


# ---------------------------------------------------------------------------
# F1a: righe ordine da processare
# ---------------------------------------------------------------------------

def get_righe_da_processare(
    session: Session,
    cliente_id: str | None = None,
    data_da: date | None = None,
    data_a: date | None = None,
    urgenza_only: bool = False,
) -> list[dict]:
    """
    Ritorna le righe ordine che l'ufficio produzione deve ancora processare.

    Criteri (tutti devono essere soddisfatti):
    - qty_da_produrre > 0
    - nessuna commessa attiva (stato != 'completata') su quella riga
    - stato riga != 'spedito', 'chiuso'
    """
    sql = text("""
        SELECT
            ro.id              AS riga_ordine_id,
            ro.ordine_id,
            ro.articolo_id,
            ro.riga_ej_id,
            ro.qty_ordinata,
            ro.qty_disponibile,
            ro.qty_in_produzione,
            ro.qty_consegnata,
            ro.stato           AS stato_riga,
            o.numero_ordine,
            o.data_consegna,
            o.cliente_id,
            a.codice           AS codice_articolo,
            a.descrizione      AS descrizione_articolo,
            c.ragione_sociale,
            c.nickname
        FROM righe_ordine ro
        JOIN ordini o      ON o.id = ro.ordine_id
        JOIN articoli a    ON a.id = ro.articolo_id
        JOIN clienti c     ON c.id = o.cliente_id
        WHERE ro.stato NOT IN ('spedito', 'chiuso')
          AND (ro.qty_ordinata - ro.qty_disponibile - ro.qty_in_produzione) > 0
          AND NOT EXISTS (
              SELECT 1 FROM commesse cm
              WHERE cm.riga_ordine_id = ro.id
                AND cm.stato != 'completata'
          )
          AND (:cliente_id IS NULL OR o.cliente_id = :cliente_id)
          AND (:data_da IS NULL    OR o.data_consegna >= :data_da)
          AND (:data_a IS NULL     OR o.data_consegna <= :data_a)
        ORDER BY o.data_consegna ASC NULLS LAST, o.numero_ordine
    """)

    rows = session.execute(sql, {
        "cliente_id": cliente_id,
        "data_da": data_da,
        "data_a": data_a,
    }).mappings().all()

    today = date.today()
    result = []

    for r in rows:
        qty_da_produrre = max(
            0,
            r["qty_ordinata"] - r["qty_disponibile"] - r["qty_in_produzione"]
        )

        # flag_urgenza: esiste un evento urgenza_formale aperto su quest'ordine?
        urgenza = session.execute(
            text("""
                SELECT 1 FROM eventi
                WHERE tipo = 'urgenza_formale'
                  AND ref_ordine_id = :oid
                  AND stato = 'aperto'
                LIMIT 1
            """),
            {"oid": r["ordine_id"]},
        ).fetchone()
        has_urgenza = urgenza is not None

        if urgenza_only and not has_urgenza:
            continue

        result.append({
            "riga_ordine_id": r["riga_ordine_id"],
            "ordine_id": r["ordine_id"],
            "numero_ordine": r["numero_ordine"],
            "data_consegna": r["data_consegna"],
            "flag_data_scaduta": (
                r["data_consegna"] is not None and r["data_consegna"] < today
            ),
            "flag_urgenza": has_urgenza,
            "codice_articolo": r["codice_articolo"],
            "descrizione_articolo": r["descrizione_articolo"],
            "cliente": r["nickname"] or r["ragione_sociale"],
            "cliente_id": r["cliente_id"],
            "qty_ordinata": r["qty_ordinata"],
            "qty_disponibile": r["qty_disponibile"],
            "qty_in_produzione": r["qty_in_produzione"],
            "qty_da_produrre": qty_da_produrre,
        })

    return result


# ---------------------------------------------------------------------------
# F1b: qty_disponibile_futura per articolo
# ---------------------------------------------------------------------------

def get_qty_disponibile_futura(session: Session, articolo_id: str) -> int:
    """
    giacenza_attuale - impegni_ordini_aperti_futuri

    giacenza_attuale: approssimata come SUM(qty_disponibile) delle righe aperte
    di quell'articolo (già calcolata dal sync da MAG_REALE).

    impegni_aperti: SUM(qty_ordinata - qty_consegnata) righe aperte di quell'articolo.

    Nota: in Fase 0 qty_disponibile viene dalla sync EasyJob (DOC_QTAP),
    che rappresenta già la giacenza appartata per quel cliente. La giacenza
    "pura" per scorte si calcola come differenza rispetto agli impegni totali.
    """
    # Giacenza corrente aggregata per articolo (dal sync EasyJob via MAG_REALE)
    # Usiamo il MAX di qty_disponibile tra tutte le righe dello stesso articolo
    # come proxy della giacenza (è lo stesso valore su tutte le righe aperte).
    # In Fase 3+ sostituire con lettura diretta da MAG_REALE.
    giacenza_row = session.execute(
        text("""
            SELECT COALESCE(MAX(ro.qty_disponibile), 0) AS giacenza
            FROM righe_ordine ro
            JOIN ordini o ON o.id = ro.ordine_id
            WHERE ro.articolo_id = :aid
              AND ro.stato NOT IN ('spedito', 'chiuso')
        """),
        {"aid": articolo_id},
    ).fetchone()
    giacenza = int(giacenza_row[0]) if giacenza_row else 0

    # Impegni ordini aperti: quanto è già "promesso" agli ordini
    impegni_row = session.execute(
        text("""
            SELECT COALESCE(SUM(ro.qty_ordinata - ro.qty_consegnata), 0) AS impegni
            FROM righe_ordine ro
            JOIN ordini o ON o.id = ro.ordine_id
            WHERE ro.articolo_id = :aid
              AND ro.stato NOT IN ('spedito', 'chiuso')
              AND ro.qty_ordinata > ro.qty_consegnata
        """),
        {"aid": articolo_id},
    ).fetchone()
    impegni = int(impegni_row[0]) if impegni_row else 0

    return max(0, giacenza - impegni)
