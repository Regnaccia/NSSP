"""
Servizi per il modulo Magazzino.

Flusso:
  1. Il magazzino vede le commesse completate da approntare (raggruppate per ordine)
  2. Per ogni commessa, registra la consegna (qty_cliente, qty_scorta)
  3. Quando un ordine è pronto, crea l'evento ordine_pronto per la logistica
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.consegna_magazzino import ConsegnaMagazzino
from app.models.evento import Evento


class MagazzinoError(Exception):
    pass


# ---------------------------------------------------------------------------
# Vista ordini da approntare
# ---------------------------------------------------------------------------

def get_ordini_da_approntare(session: Session) -> list[dict]:
    """
    Ritorna gli ordini che hanno almeno una commessa completata
    non ancora registrata come consegna magazzino.
    Raggruppa per ordine con la lista degli articoli pronti.
    """
    rows = session.execute(text("""
        SELECT
            o.id            AS ordine_id,
            o.numero_ordine,
            o.data_consegna,
            COALESCE(cl.nickname, cl.ragione_sociale) AS cliente,
            cl.id           AS cliente_id,
            c.id            AS commessa_id,
            a.id            AS articolo_id,
            a.codice        AS codice_articolo,
            a.descrizione   AS descrizione_articolo,
            c.qty_prodotta_cliente,
            c.qty_prodotta_scorta,
            (c.qty_prodotta_cliente + c.qty_prodotta_scorta) AS qty_totale,
            (cm.id IS NOT NULL) AS gia_registrata,
            EXISTS (
                SELECT 1 FROM eventi e
                WHERE e.ref_ordine_id = o.id
                  AND e.tipo = 'urgenza_formale'
                  AND e.stato = 'aperto'
            ) AS flag_urgenza
        FROM commesse c
        JOIN articoli a       ON a.id = c.articolo_id
        JOIN righe_ordine ro  ON ro.id = c.riga_ordine_id
        JOIN ordini o         ON o.id = ro.ordine_id
        JOIN clienti cl       ON cl.id = o.cliente_id
        LEFT JOIN consegne_magazzino cm ON cm.commessa_id = c.id
        WHERE c.stato = 'completata'
          AND c.qty_prodotta_cliente > 0
          AND c.riga_ordine_id IS NOT NULL
        ORDER BY o.data_consegna NULLS LAST, o.numero_ordine, a.codice
    """)).mappings().all()

    # Raggruppa per ordine
    ordini: dict[str, dict] = {}
    for r in rows:
        oid = r["ordine_id"]
        if oid not in ordini:
            ordini[oid] = {
                "ordine_id": oid,
                "numero_ordine": r["numero_ordine"],
                "data_consegna": r["data_consegna"],
                "cliente": r["cliente"],
                "cliente_id": r["cliente_id"],
                "flag_urgenza": r["flag_urgenza"],
                "articoli": [],
            }
        ordini[oid]["articoli"].append({
            "commessa_id": r["commessa_id"],
            "articolo_id": r["articolo_id"],
            "codice_articolo": r["codice_articolo"],
            "descrizione_articolo": r["descrizione_articolo"],
            "qty_prodotta_cliente": r["qty_prodotta_cliente"],
            "qty_prodotta_scorta": r["qty_prodotta_scorta"],
            "qty_totale": r["qty_totale"],
            "gia_registrata": bool(r["gia_registrata"]),
        })

    # Aggiunge flag tutte_registrate per ordine
    result = []
    for o in ordini.values():
        o["tutte_registrate"] = all(a["gia_registrata"] for a in o["articoli"])
        result.append(o)

    return result


# ---------------------------------------------------------------------------
# Registra consegna
# ---------------------------------------------------------------------------

def registra_consegna(
    session: Session,
    commessa_id: str,
    qty_cliente: int,
    qty_scorta: int,
) -> dict:
    """
    Registra che il magazzino ha messo da parte i pezzi di una commessa.
    Una sola consegna per commessa — errore se già registrata.
    """
    # Verifica commessa completata
    row = session.execute(text("""
        SELECT c.id, c.stato, c.qty_prodotta_cliente, c.qty_prodotta_scorta,
               a.id AS articolo_id, a.codice AS codice_articolo, a.descrizione AS descrizione_articolo
        FROM commesse c
        JOIN articoli a ON a.id = c.articolo_id
        WHERE c.id = :cid
    """), {"cid": commessa_id}).mappings().fetchone()

    if not row:
        raise MagazzinoError(f"Commessa {commessa_id} non trovata")
    if row["stato"] != "completata":
        raise MagazzinoError(f"Commessa non completata (stato: '{row['stato']}')")

    # Verifica che non sia già registrata
    esistente = session.execute(
        text("SELECT id FROM consegne_magazzino WHERE commessa_id = :cid"),
        {"cid": commessa_id},
    ).fetchone()
    if esistente:
        raise MagazzinoError(f"Commessa {commessa_id} già registrata in consegna")

    # Determina quota
    if qty_cliente > 0 and qty_scorta > 0:
        quota = "mista"
    elif qty_scorta > 0:
        quota = "scorta"
    else:
        quota = "cliente"

    consegna = ConsegnaMagazzino(
        id=str(uuid.uuid4()),
        commessa_id=commessa_id,
        articolo_id=row["articolo_id"],
        qty_consegnata=qty_cliente + qty_scorta,
        quota=quota,
        qty_cliente=qty_cliente,
        qty_scorta=qty_scorta,
        stato="in_attesa",
    )
    session.add(consegna)
    session.commit()
    session.refresh(consegna)

    return {
        "id": consegna.id,
        "commessa_id": consegna.commessa_id,
        "articolo_id": consegna.articolo_id,
        "codice_articolo": row["codice_articolo"],
        "descrizione_articolo": row["descrizione_articolo"],
        "qty_consegnata": consegna.qty_consegnata,
        "quota": consegna.quota,
        "qty_cliente": consegna.qty_cliente,
        "qty_scorta": consegna.qty_scorta,
        "stato": consegna.stato,
        "registrata_ej_at": consegna.registrata_ej_at,
        "created_at": consegna.created_at,
    }


def get_consegne_ordine(session: Session, ordine_id: str) -> list[dict]:
    """Lista consegne registrate per un ordine."""
    rows = session.execute(text("""
        SELECT
            cm.id, cm.commessa_id, cm.articolo_id,
            a.codice AS codice_articolo, a.descrizione AS descrizione_articolo,
            cm.qty_consegnata, cm.quota, cm.qty_cliente, cm.qty_scorta,
            cm.stato, cm.registrata_ej_at, cm.created_at
        FROM consegne_magazzino cm
        JOIN commesse c ON c.id = cm.commessa_id
        JOIN righe_ordine ro ON ro.id = c.riga_ordine_id
        JOIN articoli a ON a.id = cm.articolo_id
        WHERE ro.ordine_id = :oid
        ORDER BY cm.created_at
    """), {"oid": ordine_id}).mappings().all()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Segnala ordine pronto per logistica
# ---------------------------------------------------------------------------

def segna_ordine_pronto(
    session: Session,
    ordine_id: str,
    nota: str | None = None,
    created_by: str | None = None,
) -> Evento:
    """
    Crea evento ordine_pronto (mittente: magazzino, destinatario: logistica).
    Idempotente: se esiste già un evento aperto per questo ordine, lo ritorna senza crearne un altro.
    """
    esistente = session.execute(text("""
        SELECT id FROM eventi
        WHERE ref_ordine_id = :oid
          AND tipo = 'ordine_pronto'
          AND stato IN ('aperto', 'in_lavorazione')
        LIMIT 1
    """), {"oid": ordine_id}).fetchone()

    if esistente:
        ev = session.get(Evento, esistente[0])
        return ev  # type: ignore[return-value]

    # Verifica che l'ordine esista
    ordine = session.execute(
        text("SELECT id FROM ordini WHERE id = :oid"), {"oid": ordine_id}
    ).fetchone()
    if not ordine:
        raise MagazzinoError(f"Ordine {ordine_id} non trovato")

    ev = Evento(
        id=str(uuid.uuid4()),
        tipo="ordine_pronto",
        mittente="magazzino",
        destinatario="logistica",
        ref_ordine_id=ordine_id,
        stato="aperto",
        nota=nota,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev
