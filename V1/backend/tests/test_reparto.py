"""
Test router /api/reparto — Terminale kiosk, nessun JWT richiesto.

Copre la state machine completa:
  in_coda → in_produzione (avvia)
  in_produzione → sospesa  (sospendi)
  sospesa → in_produzione  (riprendi)
  in_produzione → completata (completa)

Inoltre:
  - Transizione invalida → 409
  - aggiorna-qty durante in_produzione
  - GET macchine, GET macchine/{id}/coda, GET commesse/{id}
"""
from tests.conftest import COM_ID, MAC_ID


# ────────────────────────────────────────────────────────────────────────────
# Macchine
# ────────────────────────────────────────────────────────────────────────────

def test_get_macchine_reparto(client, seed):
    r = client.get("/api/reparto/macchine")
    assert r.status_code == 200
    data = r.json()
    assert any(m["codice"] == "CNC-01" for m in data)


def test_get_macchine_coda(client, seed):
    """Coda della macchina: vuota se nessuna commessa è assegnata."""
    r = client.get(f"/api/reparto/macchine/{MAC_ID}/coda")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_get_macchine_coda_not_found(client, seed):
    r = client.get("/api/reparto/macchine/00000000-dead-beef-0000-000000000000/coda")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Dettaglio commessa
# ────────────────────────────────────────────────────────────────────────────

def test_get_commessa_detail(client, seed):
    r = client.get(f"/api/reparto/commesse/{COM_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == COM_ID
    assert data["stato"] == "in_coda"
    assert data["qty_totale"] == 80


def test_get_commessa_not_found(client, seed):
    r = client.get("/api/reparto/commesse/00000000-dead-beef-0000-000000000000")
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# State machine — percorso completo
# ────────────────────────────────────────────────────────────────────────────

def test_avvia_commessa(client, seed):
    r = client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    assert r.status_code == 200
    assert r.json()["stato"] == "in_produzione"


def test_sospendi_commessa(client, seed):
    # Prima avvia
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    r = client.post(f"/api/reparto/commesse/{COM_ID}/sospendi",
                    json={"nota": "manutenzione urgente"})
    assert r.status_code == 200
    data = r.json()
    assert data["stato"] == "sospesa"
    assert data["sospesa_nota"] == "manutenzione urgente"


def test_riprendi_commessa(client, seed):
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    client.post(f"/api/reparto/commesse/{COM_ID}/sospendi", json={"nota": "stop"})
    r = client.post(f"/api/reparto/commesse/{COM_ID}/riprendi")
    assert r.status_code == 200
    assert r.json()["stato"] == "in_produzione"


def test_completa_commessa(client, seed):
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    r = client.post(f"/api/reparto/commesse/{COM_ID}/completa")
    assert r.status_code == 200
    data = r.json()
    assert data["stato"] == "completata"
    assert data["completata_at"] is not None


def test_state_machine_percorso_completo(client, seed):
    """Esegue l'intero ciclo: in_coda→in_produzione→sospesa→in_produzione→completata."""
    com = COM_ID

    r = client.post(f"/api/reparto/commesse/{com}/avvia")
    assert r.json()["stato"] == "in_produzione"

    r = client.post(f"/api/reparto/commesse/{com}/sospendi", json={"nota": "pausa"})
    assert r.json()["stato"] == "sospesa"

    r = client.post(f"/api/reparto/commesse/{com}/riprendi")
    assert r.json()["stato"] == "in_produzione"

    r = client.post(f"/api/reparto/commesse/{com}/completa")
    assert r.json()["stato"] == "completata"


# ────────────────────────────────────────────────────────────────────────────
# Transizioni invalide → 409
# ────────────────────────────────────────────────────────────────────────────

def test_sospendi_da_in_coda_fails(client, seed):
    """Non si può sospendere una commessa in_coda (deve essere in_produzione)."""
    r = client.post(f"/api/reparto/commesse/{COM_ID}/sospendi", json={"nota": ""})
    assert r.status_code == 409


def test_completa_da_in_coda_fails(client, seed):
    r = client.post(f"/api/reparto/commesse/{COM_ID}/completa")
    assert r.status_code == 409


def test_riprendi_da_in_coda_fails(client, seed):
    r = client.post(f"/api/reparto/commesse/{COM_ID}/riprendi")
    assert r.status_code == 409


def test_avvia_gia_in_produzione_fails(client, seed):
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    r = client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    assert r.status_code == 409


def test_transizione_commessa_not_found(client, seed):
    r = client.post("/api/reparto/commesse/00000000-dead-beef-0000-000000000000/avvia")
    assert r.status_code == 409  # CommessaError → 409


# ────────────────────────────────────────────────────────────────────────────
# aggiorna-qty
# ────────────────────────────────────────────────────────────────────────────

def test_aggiorna_qty_in_produzione(client, seed):
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    r = client.post(
        f"/api/reparto/commesse/{COM_ID}/aggiorna-qty",
        json={"qty_prodotta_cliente": 40, "qty_prodotta_scorta": 0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["qty_prodotta_cliente"] == 40


def test_aggiorna_qty_non_negative(client, seed):
    """Valori negativi vengono normalizzati a 0."""
    client.post(f"/api/reparto/commesse/{COM_ID}/avvia")
    r = client.post(
        f"/api/reparto/commesse/{COM_ID}/aggiorna-qty",
        json={"qty_prodotta_cliente": -5, "qty_prodotta_scorta": 0},
    )
    assert r.status_code == 200
    assert r.json()["qty_prodotta_cliente"] == 0


def test_aggiorna_qty_da_in_coda_fails(client, seed):
    """Non si può aggiornare qty se la commessa non è in_produzione/sospesa."""
    r = client.post(
        f"/api/reparto/commesse/{COM_ID}/aggiorna-qty",
        json={"qty_prodotta_cliente": 10, "qty_prodotta_scorta": 0},
    )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# Kiosk: nessun token richiesto
# ────────────────────────────────────────────────────────────────────────────

def test_reparto_no_auth_needed(client, seed):
    """Il router reparto è accessibile senza token (terminale kiosk fisso)."""
    r = client.get("/api/reparto/macchine")
    assert r.status_code == 200  # non 401
