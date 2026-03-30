"""
Servizi per eventi inter-reparto.

Tipi di eventi:
  urgenza_formale  — logistica → produzione: ordine urgente, va avanti in coda
  ordine_pronto    — magazzino → logistica: ordine pronto per la spedizione (vedi services/magazzino.py)
  feedback_urgenza — produzione → logistica: risposta a urgenza_formale

Quando un'urgenza viene creata o risolta, la coda di lavorazione viene automaticamente
ricalcolata (le commesse relative salgono/scendono in priorità).
"""
import uuid
from datetime import datetime, timezone, date

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.evento import Evento


class EventoError(Exception):
    pass


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------

_BASE_SQL = """
    SELECT
        e.id, e.tipo, e.mittente, e.destinatario, e.stato, e.nota,
        e.ref_ordine_id, e.ref_commessa_id, e.ref_articolo_id,
        e.feedback_stato, e.feedback_data_prevista, e.feedback_nota, e.corriere_override,
        e.created_at, e.updated_at, e.resolved_at,
        o.numero_ordine,
        COALESCE(cl.nickname, cl.ragione_sociale) AS cliente
    FROM eventi e
    LEFT JOIN ordini o   ON o.id = e.ref_ordine_id
    LEFT JOIN clienti cl ON cl.id = o.cliente_id
"""


def get_eventi(
    session: Session,
    tipo: str | None = None,
    destinatario: str | None = None,
    stato: str | None = None,
    ref_ordine_id: str | None = None,
) -> list[dict]:
    filters = ["1=1"]
    params: dict = {}
    if tipo:
        filters.append("e.tipo = :tipo")
        params["tipo"] = tipo
    if destinatario:
        filters.append("e.destinatario = :destinatario")
        params["destinatario"] = destinatario
    if stato:
        filters.append("e.stato = :stato")
        params["stato"] = stato
    if ref_ordine_id:
        filters.append("e.ref_ordine_id = :ref_ordine_id")
        params["ref_ordine_id"] = ref_ordine_id

    rows = session.execute(
        text(_BASE_SQL + f"WHERE {' AND '.join(filters)} ORDER BY e.created_at DESC"),
        params,
    ).mappings().all()
    return [dict(r) for r in rows]


def get_evento_detail(session: Session, evento_id: str) -> dict | None:
    row = session.execute(
        text(_BASE_SQL + "WHERE e.id = :eid"),
        {"eid": evento_id},
    ).mappings().fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Urgenza formale
# ---------------------------------------------------------------------------

def crea_urgenza(
    session: Session,
    ordine_id: str,
    nota: str | None = None,
    created_by: str | None = None,
) -> dict:
    """
    Logistica crea urgenza_formale su un ordine.
    Ricalcola la coda dopo la creazione (l'ordine sale in priorità).
    """
    # Verifica che l'ordine esista
    ordine = session.execute(
        text("SELECT id FROM ordini WHERE id = :oid"), {"oid": ordine_id}
    ).fetchone()
    if not ordine:
        raise EventoError(f"Ordine {ordine_id} non trovato")

    ev = Evento(
        id=str(uuid.uuid4()),
        tipo="urgenza_formale",
        mittente="logistica",
        destinatario="produzione",
        ref_ordine_id=ordine_id,
        stato="aperto",
        nota=nota,
    )
    session.add(ev)
    session.commit()

    # Ricalcola la coda — le commesse di questo ordine salgono in priorità
    _ricalcola_coda(session)

    return get_evento_detail(session, ev.id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Feedback urgenza (produzione → logistica)
# ---------------------------------------------------------------------------

def dai_feedback(
    session: Session,
    evento_id: str,
    feedback_stato: str,
    feedback_data_prevista: date | None = None,
    feedback_nota: str | None = None,
    corriere_override: str | None = None,
) -> dict:
    """
    La produzione risponde a un'urgenza:
      - feedback_stato = 'accettata'    → prenderà in carico
      - feedback_stato = 'non_fattibile' → non può rispettare la scadenza
    L'evento passa a stato 'in_lavorazione'.
    """
    ev = session.get(Evento, evento_id)
    if not ev:
        raise EventoError(f"Evento {evento_id} non trovato")
    if ev.tipo != "urgenza_formale":
        raise EventoError("Il feedback si applica solo a eventi di tipo 'urgenza_formale'")
    if ev.stato not in ("aperto", "in_lavorazione"):
        raise EventoError(f"Evento non in stato modificabile (stato: '{ev.stato}')")
    if feedback_stato not in ("accettata", "non_fattibile"):
        raise EventoError("feedback_stato deve essere 'accettata' o 'non_fattibile'")

    ev.feedback_stato = feedback_stato
    ev.feedback_data_prevista = feedback_data_prevista
    ev.feedback_nota = feedback_nota
    ev.corriere_override = corriere_override
    ev.stato = "in_lavorazione"
    ev.updated_at = datetime.now(timezone.utc)

    session.commit()
    return get_evento_detail(session, evento_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Risolvi / Rifiuta
# ---------------------------------------------------------------------------

def risolvi_evento(
    session: Session,
    evento_id: str,
    nota: str | None = None,
) -> dict:
    """
    Segna l'evento come risolto.
    Per urgenze: ricalcola la coda (l'urgenza non è più attiva).
    """
    ev = session.get(Evento, evento_id)
    if not ev:
        raise EventoError(f"Evento {evento_id} non trovato")
    if ev.stato in ("risolto", "rifiutato"):
        raise EventoError(f"Evento già in stato '{ev.stato}'")

    now = datetime.now(timezone.utc)
    ev.stato = "risolto"
    ev.resolved_at = now
    ev.updated_at = now
    if nota:
        ev.nota = (ev.nota or "") + f"\n[Risolto] {nota}"

    session.commit()

    if ev.tipo == "urgenza_formale":
        _ricalcola_coda(session)

    return get_evento_detail(session, evento_id)  # type: ignore[return-value]


def rifiuta_evento(
    session: Session,
    evento_id: str,
    nota: str | None = None,
) -> dict:
    ev = session.get(Evento, evento_id)
    if not ev:
        raise EventoError(f"Evento {evento_id} non trovato")
    if ev.stato in ("risolto", "rifiutato"):
        raise EventoError(f"Evento già in stato '{ev.stato}'")

    now = datetime.now(timezone.utc)
    ev.stato = "rifiutato"
    ev.resolved_at = now
    ev.updated_at = now
    if nota:
        ev.nota = (ev.nota or "") + f"\n[Rifiutato] {nota}"

    session.commit()
    return get_evento_detail(session, evento_id)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------

def _ricalcola_coda(session: Session) -> None:
    """Ricalcola posizione_coda dopo ogni cambio di urgenze (import lazy per evitare circular)."""
    from app.services.priorita import ricalcola_coda
    ricalcola_coda(session)
