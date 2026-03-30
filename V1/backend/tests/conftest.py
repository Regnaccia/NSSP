"""
Fixtures condivise per tutti i test del backend MRS V1.

Pattern isolamento DB:
  - engine  (session)  → crea le tabelle una volta sola
  - db      (function) → connessione con outer transaction che si fa sempre rollback
  - seed    (function) → inserisce dati minimi DENTRO quella transazione
  - client  (function) → TestClient con override get_db e scheduler moccato

Ogni test parte con un DB vuoto e torna a DB vuoto dopo.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.services.auth import create_token, hash_password

# ── Test DB ──────────────────────────────────────────────────────────────────
TEST_DB_URL = os.getenv(
    "MRS_TEST_DB_URL",
    "postgresql+psycopg2://nssp_user:nssp_password@localhost:5432/mrs_test",
)

# ── ID fissi per seed ────────────────────────────────────────────────────────
ADMIN_ID = "a0000000-0000-0000-0000-000000000001"
PROD_ID  = "a0000000-0000-0000-0000-000000000002"
LOG_ID   = "a0000000-0000-0000-0000-000000000003"
MAG_ID   = "a0000000-0000-0000-0000-000000000004"

ART_ID   = "b0000000-0000-0000-0000-000000000001"
CLI_ID   = "c0000000-0000-0000-0000-000000000001"
ORD_ID   = "d0000000-0000-0000-0000-000000000001"
RIGA_ID  = "e0000000-0000-0000-0000-000000000001"
MAC_ID   = "f0000000-0000-0000-0000-000000000001"
COM_ID   = "a1000000-0000-0000-0000-000000000001"  # commessa in_coda
COM_DONE = "a1000000-0000-0000-0000-000000000002"  # commessa completata


# ── Engine (session-scoped) ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """Crea le tabelle sul DB di test una volta sola per tutta la sessione pytest."""
    import app.models  # noqa: registra tutti i modelli su Base.metadata
    from app.database import Base

    e = create_engine(TEST_DB_URL, pool_pre_ping=True)
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


# ── DB (function-scoped, con rollback) ───────────────────────────────────────

@pytest.fixture
def db(engine):
    """
    Ogni test riceve una connessione con una outer transaction che viene
    sempre rollbackata al termine. Le commit dei servizi vengono catturate
    da savepoint (begin_nested), lasciando intatta la outer transaction.
    """
    connection = engine.connect()
    transaction = connection.begin()
    nested = connection.begin_nested()

    session = Session(connection)

    @sa_event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── Seed (function-scoped) ───────────────────────────────────────────────────

@pytest.fixture
def seed(db):
    """Inserisce dati minimi dentro la transazione del test corrente."""
    from app.models.utente import Utente
    from app.models.articolo import Articolo
    from app.models.cliente import Cliente
    from app.models.ordine import Ordine
    from app.models.riga_ordine import RigaOrdine
    from app.models.macchina import Macchina
    from app.models.commessa import Commessa

    now   = datetime.now(timezone.utc)
    today = date.today()
    consegna = today + timedelta(days=14)

    # ── Utenti ────────────────────────────────────────────────────────────────
    db.add(Utente(id=ADMIN_ID, username="admin_test", password_hash=hash_password("admin123"),
                  ruolo="admin", attivo=True, created_at=now))
    db.add(Utente(id=PROD_ID, username="prod_test", password_hash=hash_password("prod123"),
                  ruolo="produzione", attivo=True, created_at=now))
    db.add(Utente(id=LOG_ID, username="log_test", password_hash=hash_password("log123"),
                  ruolo="logistica", attivo=True, created_at=now))
    db.add(Utente(id=MAG_ID, username="mag_test", password_hash=hash_password("mag123"),
                  ruolo="magazzino", attivo=True, created_at=now))

    # ── Articolo ──────────────────────────────────────────────────────────────
    db.add(Articolo(
        id=ART_ID, codice="TST001", codice_upper="TST001",
        descrizione="Articolo di test", categoria="CAT_X",
        tipo_produzione="PEZZO", scorta_mensile=10, mesi_scorta=3,
        storico_sufficiente=True, prd_pari=False, synced_at=now,
    ))

    # ── Cliente ───────────────────────────────────────────────────────────────
    db.add(Cliente(
        id=CLI_ID, codice_easyjob="CL0001",
        ragione_sociale="Cliente Test SRL", nickname="CT", synced_at=now,
    ))

    # ── Ordine ────────────────────────────────────────────────────────────────
    db.add(Ordine(
        id=ORD_ID, numero_ordine="T-001", cliente_id=CLI_ID,
        data_ordine=today, data_consegna=consegna,
        stato="aperto", synced_at=now,
    ))

    # ── Riga ordine: qty_da_produrre = 100 - 20 - 0 = 80 ───────────────────
    db.add(RigaOrdine(
        id=RIGA_ID, ordine_id=ORD_ID, articolo_id=ART_ID,
        riga_ej_id="EJ-T001",
        qty_ordinata=100, qty_disponibile=20, qty_in_produzione=0, qty_consegnata=0,
        stato="aperto", synced_at=now,
    ))

    # ── Macchina ──────────────────────────────────────────────────────────────
    db.add(Macchina(
        id=MAC_ID, codice="CNC-01", nome="Tornio CNC 1",
        operazioni_eseguibili=["tornitura", "fresatura"],
        stato="disponibile", attiva=True,
    ))

    # ── Commessa in_coda ──────────────────────────────────────────────────────
    db.add(Commessa(
        id=COM_ID, riga_ordine_id=RIGA_ID, articolo_id=ART_ID,
        qty_cliente=80, qty_scorta=0,
        qty_prodotta_cliente=0, qty_prodotta_scorta=0,
        stato="in_coda", created_at=now, created_by="test",
    ))

    # ── Commessa completata (per magazzino) ───────────────────────────────────
    db.add(Commessa(
        id=COM_DONE, riga_ordine_id=RIGA_ID, articolo_id=ART_ID,
        qty_cliente=50, qty_scorta=5,
        qty_prodotta_cliente=50, qty_prodotta_scorta=5,
        stato="completata", completata_at=now, created_at=now, created_by="test",
    ))

    db.flush()

    return {
        "admin_id": ADMIN_ID, "prod_id": PROD_ID,
        "log_id": LOG_ID, "mag_id": MAG_ID,
        "art_id": ART_ID, "cli_id": CLI_ID,
        "ord_id": ORD_ID, "riga_id": RIGA_ID,
        "mac_id": MAC_ID, "com_id": COM_ID, "com_done": COM_DONE,
    }


# ── TestClient (function-scoped) ─────────────────────────────────────────────

@pytest.fixture
def client(db, monkeypatch):
    """TestClient con get_db overridato e scheduler moccato."""
    from app.main import app
    from app.database import get_db

    monkeypatch.setattr("app.main.start_scheduler", lambda: None)
    monkeypatch.setattr("app.main.stop_scheduler", lambda: None)

    app.dependency_overrides[get_db] = lambda: db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


# ── Token helper fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def admin_token():
    return create_token(ADMIN_ID, "admin_test", "admin")


@pytest.fixture
def prod_token():
    return create_token(PROD_ID, "prod_test", "produzione")


@pytest.fixture
def log_token():
    return create_token(LOG_ID, "log_test", "logistica")


@pytest.fixture
def mag_token():
    return create_token(MAG_ID, "mag_test", "magazzino")


def auth(token: str) -> dict:
    """Restituisce l'header Authorization per le richieste HTTP."""
    return {"Authorization": f"Bearer {token}"}
