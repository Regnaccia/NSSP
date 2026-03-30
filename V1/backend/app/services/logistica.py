"""
Servizi per il modulo Logistica.

Flusso:
  1. Logistica riceve eventi ordine_pronto dal magazzino
  2. Consulta la policy del cliente per decidere quando e come spedire
  3. Crea la spedizione con corriere, data, colli, peso
  4. Segna come spedita quando il corriere ritira
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.policy_cliente import PolicyCliente
from app.models.spedizione import Spedizione
from app.models.cliente import Cliente


class LogisticaError(Exception):
    pass


# ---------------------------------------------------------------------------
# Policy cliente
# ---------------------------------------------------------------------------

def get_policy(session: Session, cliente_id: str) -> PolicyCliente | None:
    return session.execute(
        text("SELECT * FROM policy_clienti WHERE cliente_id = :cid"),
        {"cid": cliente_id},
    ).mappings().fetchone()  # type: ignore[return-value]


def upsert_policy(session: Session, cliente_id: str, data: dict) -> PolicyCliente:
    """Crea o aggiorna la policy di un cliente."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise LogisticaError(f"Cliente {cliente_id} non trovato")

    existing = session.execute(
        text("SELECT id FROM policy_clienti WHERE cliente_id = :cid"),
        {"cid": cliente_id},
    ).fetchone()

    if existing:
        set_parts = ", ".join(f"{k} = :{k}" for k in data if k not in ("cliente_id",))
        set_parts += ", updated_at = :updated_at"
        params = {k: v for k, v in data.items() if k not in ("cliente_id",)}
        params["updated_at"] = datetime.now(timezone.utc)
        params["cid"] = cliente_id
        session.execute(
            text(f"UPDATE policy_clienti SET {set_parts} WHERE cliente_id = :cid"),
            params,
        )
        session.commit()
    else:
        policy = PolicyCliente(
            id=str(uuid.uuid4()),
            cliente_id=cliente_id,
            **{k: v for k, v in data.items() if k not in ("cliente_id",)},
        )
        session.add(policy)
        session.commit()
        session.refresh(policy)

    return session.execute(
        text("SELECT * FROM policy_clienti WHERE cliente_id = :cid"),
        {"cid": cliente_id},
    ).mappings().fetchone()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Calcolo data spedizione suggerita
# ---------------------------------------------------------------------------

def calcola_data_spedizione_suggerita(
    tipo_policy: str,
    giorno_fisso: int | None,
    data_consegna: date | None,
) -> date | None:
    """
    Calcola la data di spedizione suggerita in base al tipo di policy.

    GIORNO_FISSO:   prossimo giorno della settimana (1=Lun..7=Dom) dalla data odierna,
                    non oltre data_consegna
    DATA_TASSATIVA: data_consegna dell'ordine
    SOGLIA_VALORE:  calcolata separatamente (richiede dati in DB)
    DEFAULT:        None (operatore decide)
    """
    today = date.today()

    if tipo_policy == "DATA_TASSATIVA":
        return data_consegna

    if tipo_policy == "GIORNO_FISSO" and giorno_fisso:
        # Trova il prossimo giorno della settimana >= oggi
        # isoweekday(): Lun=1 … Dom=7
        days_ahead = (giorno_fisso - today.isoweekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # non oggi: il prossimo della settimana
        candidate = today + timedelta(days=days_ahead)
        if data_consegna and candidate > data_consegna:
            return data_consegna  # meglio anticipare se il giorno fisso supera la scadenza
        return candidate

    return None


def _soglia_raggiunta(
    session: Session,
    cliente_id: str,
    soglia_valore: Decimal | None,
) -> bool:
    """
    Verifica se il valore totale degli ordini pronti (con evento ordine_pronto aperto)
    supera la soglia configurata. Usa qty_ordinata come proxy del valore (no prezzi in MRS).
    """
    if not soglia_valore:
        return False
    row = session.execute(text("""
        SELECT COALESCE(SUM(ro.qty_ordinata), 0) AS totale
        FROM eventi e
        JOIN ordini o  ON o.id = e.ref_ordine_id
        JOIN righe_ordine ro ON ro.ordine_id = o.id
        WHERE o.cliente_id = :cid
          AND e.tipo = 'ordine_pronto'
          AND e.stato = 'aperto'
    """), {"cid": cliente_id}).mappings().fetchone()
    if not row:
        return False
    return (row["totale"] or 0) >= float(soglia_valore)


# ---------------------------------------------------------------------------
# Vista ordini da spedire
# ---------------------------------------------------------------------------

def get_ordini_da_spedire(session: Session) -> list[dict]:
    """
    Ordini con evento ordine_pronto aperto, arricchiti con policy e data suggerita.
    """
    rows = session.execute(text("""
        SELECT
            o.id            AS ordine_id,
            o.numero_ordine,
            o.data_consegna,
            COALESCE(cl.nickname, cl.ragione_sociale) AS cliente,
            cl.id           AS cliente_id,
            e.id            AS evento_id,
            pc.tipo_policy,
            pc.giorno_fisso,
            pc.soglia_valore,
            pc.corriere_preferito,
            EXISTS (
                SELECT 1 FROM eventi urg
                WHERE urg.ref_ordine_id = o.id
                  AND urg.tipo = 'urgenza_formale'
                  AND urg.stato = 'aperto'
            ) AS flag_urgenza
        FROM eventi e
        JOIN ordini o  ON o.id = e.ref_ordine_id
        JOIN clienti cl ON cl.id = o.cliente_id
        LEFT JOIN policy_clienti pc ON pc.cliente_id = cl.id
        WHERE e.tipo = 'ordine_pronto'
          AND e.stato = 'aperto'
        ORDER BY o.data_consegna NULLS LAST, o.numero_ordine
    """)).mappings().all()

    result = []
    for r in rows:
        tipo_policy = r["tipo_policy"]
        data_suggerita = calcola_data_spedizione_suggerita(
            tipo_policy or "DEFAULT",
            r["giorno_fisso"],
            r["data_consegna"],
        )
        soglia_ok = None
        if tipo_policy == "SOGLIA_VALORE":
            soglia_ok = _soglia_raggiunta(session, r["cliente_id"], r["soglia_valore"])

        result.append({
            "ordine_id": r["ordine_id"],
            "numero_ordine": r["numero_ordine"],
            "data_consegna": r["data_consegna"],
            "cliente": r["cliente"],
            "cliente_id": r["cliente_id"],
            "tipo_policy": tipo_policy,
            "corriere_suggerito": r["corriere_preferito"],
            "data_spedizione_suggerita": data_suggerita,
            "soglia_raggiunta": soglia_ok,
            "flag_urgenza": r["flag_urgenza"],
            "evento_id": r["evento_id"],
        })

    return result


# ---------------------------------------------------------------------------
# Clienti
# ---------------------------------------------------------------------------

def get_clienti_con_policy(session: Session) -> list[dict]:
    rows = session.execute(text("""
        SELECT
            cl.id, cl.codice_easyjob, cl.ragione_sociale, cl.nickname, cl.email,
            pc.tipo_policy, pc.corriere_preferito
        FROM clienti cl
        LEFT JOIN policy_clienti pc ON pc.cliente_id = cl.id
        ORDER BY COALESCE(cl.nickname, cl.ragione_sociale)
    """)).mappings().all()

    return [
        {
            "id": r["id"],
            "codice_easyjob": r["codice_easyjob"],
            "ragione_sociale": r["ragione_sociale"],
            "nickname": r["nickname"],
            "email": r["email"],
            "ha_policy": r["tipo_policy"] is not None,
            "tipo_policy": r["tipo_policy"],
            "corriere_preferito": r["corriere_preferito"],
        }
        for r in rows
    ]


def aggiorna_nickname(session: Session, cliente_id: str, nickname: str | None) -> None:
    """Aggiorna il nickname operativo di un cliente (MRS-owned, DL-ARCH-017)."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise LogisticaError(f"Cliente {cliente_id} non trovato")
    cliente.nickname = nickname
    session.commit()


# ---------------------------------------------------------------------------
# Spedizioni
# ---------------------------------------------------------------------------

def crea_spedizione(session: Session, data: dict) -> dict:
    ordine_id = data["ordine_id"]
    ordine = session.execute(
        text("SELECT id FROM ordini WHERE id = :oid"), {"oid": ordine_id}
    ).fetchone()
    if not ordine:
        raise LogisticaError(f"Ordine {ordine_id} non trovato")

    sped = Spedizione(
        id=str(uuid.uuid4()),
        ordine_id=ordine_id,
        tipo=data["tipo"],
        stato="in_preparazione",
        corriere=data.get("corriere"),
        data_pianificata=data.get("data_pianificata"),
        colli=data.get("colli"),
        peso_kg=data.get("peso_kg"),
        note=data.get("note"),
    )
    session.add(sped)
    session.commit()
    session.refresh(sped)
    return _spedizione_to_dict(session, sped)


def aggiorna_spedizione(session: Session, spedizione_id: str, data: dict) -> dict:
    sped = session.get(Spedizione, spedizione_id)
    if not sped:
        raise LogisticaError(f"Spedizione {spedizione_id} non trovata")
    if sped.stato in ("spedita", "annullata"):
        raise LogisticaError(f"Spedizione già in stato '{sped.stato}', non modificabile")

    for field in ("corriere", "data_pianificata", "colli", "peso_kg", "note"):
        if field in data and data[field] is not None:
            setattr(sped, field, data[field])

    session.commit()
    session.refresh(sped)
    return _spedizione_to_dict(session, sped)


def segna_spedita(session: Session, spedizione_id: str) -> dict:
    sped = session.get(Spedizione, spedizione_id)
    if not sped:
        raise LogisticaError(f"Spedizione {spedizione_id} non trovata")
    if sped.stato == "spedita":
        raise LogisticaError("Spedizione già segnata come spedita")
    if sped.stato == "annullata":
        raise LogisticaError("Impossibile segnare come spedita una spedizione annullata")

    sped.stato = "spedita"
    sped.data_spedizione = date.today()
    session.commit()
    session.refresh(sped)
    return _spedizione_to_dict(session, sped)


def get_spedizioni(
    session: Session,
    stato: str | None = None,
    cliente_id: str | None = None,
) -> list[dict]:
    filters = ["1=1"]
    params: dict = {}
    if stato:
        filters.append("s.stato = :stato")
        params["stato"] = stato
    if cliente_id:
        filters.append("o.cliente_id = :cliente_id")
        params["cliente_id"] = cliente_id

    rows = session.execute(text(f"""
        SELECT
            s.id, s.ordine_id, s.tipo, s.stato, s.corriere,
            s.data_pianificata, s.data_spedizione,
            s.colli, s.peso_kg, s.note, s.created_at,
            o.numero_ordine,
            COALESCE(cl.nickname, cl.ragione_sociale) AS cliente
        FROM spedizioni s
        JOIN ordini o  ON o.id = s.ordine_id
        JOIN clienti cl ON cl.id = o.cliente_id
        WHERE {' AND '.join(filters)}
        ORDER BY s.data_pianificata NULLS LAST, s.created_at DESC
    """), params).mappings().all()

    return [dict(r) for r in rows]


def get_calendario(session: Session, data_da: date, data_a: date) -> list[dict]:
    """Spedizioni pianificate in un range di date, raggruppate per giorno."""
    rows = session.execute(text("""
        SELECT
            s.id, s.ordine_id, s.tipo, s.stato, s.corriere,
            s.data_pianificata, s.data_spedizione,
            s.colli, s.peso_kg, s.note, s.created_at,
            o.numero_ordine,
            COALESCE(cl.nickname, cl.ragione_sociale) AS cliente
        FROM spedizioni s
        JOIN ordini o  ON o.id = s.ordine_id
        JOIN clienti cl ON cl.id = o.cliente_id
        WHERE s.data_pianificata BETWEEN :da AND :a
        ORDER BY s.data_pianificata, cl.ragione_sociale
    """), {"da": data_da, "a": data_a}).mappings().all()

    giorni: dict[date, list] = {}
    for r in rows:
        d = r["data_pianificata"]
        if d not in giorni:
            giorni[d] = []
        giorni[d].append(dict(r))

    return [{"data": d, "spedizioni": speds} for d, speds in sorted(giorni.items())]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _spedizione_to_dict(session: Session, sped: Spedizione) -> dict:
    row = session.execute(text("""
        SELECT o.numero_ordine,
               COALESCE(cl.nickname, cl.ragione_sociale) AS cliente
        FROM ordini o
        JOIN clienti cl ON cl.id = o.cliente_id
        WHERE o.id = :oid
    """), {"oid": sped.ordine_id}).mappings().fetchone()

    return {
        "id": sped.id,
        "ordine_id": sped.ordine_id,
        "numero_ordine": row["numero_ordine"] if row else None,
        "cliente": row["cliente"] if row else None,
        "tipo": sped.tipo,
        "stato": sped.stato,
        "corriere": sped.corriere,
        "data_pianificata": sped.data_pianificata,
        "data_spedizione": sped.data_spedizione,
        "colli": sped.colli,
        "peso_kg": sped.peso_kg,
        "note": sped.note,
        "created_at": sped.created_at,
    }
