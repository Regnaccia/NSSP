"""
Test router /api/magazzino — Terminale kiosk, nessun JWT.

Copre:
  - GET /da-approntare: ordini con commesse completate
  - POST /consegne: registra consegna (201)
  - POST /consegne: duplicato (409)
  - POST /consegne: commessa non completata (409)
  - GET /ordini/{id}/consegne
  - POST /ordini/{id}/pronto: crea evento ordine_pronto (201)
  - POST /ordini/{id}/pronto: idempotente (secondo call = stesso evento)
  - POST /ordini/{id}/pronto: ordine not found (404)
"""
from tests.conftest import COM_DONE, ORD_ID, COM_ID


# ────────────────────────────────────────────────────────────────────────────
# GET /da-approntare
# ────────────────────────────────────────────────────────────────────────────

def test_da_approntare_contiene_commessa_completata(client, seed):
    r = client.get("/api/magazzino/da-approntare")
    assert r.status_code == 200
    data = r.json()
    # COM_DONE è completata con qty_prodotta_cliente=50 → deve comparire
    ordini = {o["ordine_id"] for o in data}
    assert ORD_ID in ordini


def test_da_approntare_campo_articoli(client, seed):
    r = client.get("/api/magazzino/da-approntare")
    data = r.json()
    ordine = next((o for o in data if o["ordine_id"] == ORD_ID), None)
    assert ordine is not None
    assert len(ordine["articoli"]) > 0
    art = ordine["articoli"][0]
    assert art["codice_articolo"] == "TST001"


def test_da_approntare_flag_tutte_registrate_false(client, seed):
    r = client.get("/api/magazzino/da-approntare")
    data = r.json()
    ordine = next((o for o in data if o["ordine_id"] == ORD_ID), None)
    assert ordine["tutte_registrate"] is False


def test_magazzino_no_auth_needed(client, seed):
    r = client.get("/api/magazzino/da-approntare")
    assert r.status_code == 200  # non 401


# ────────────────────────────────────────────────────────────────────────────
# POST /consegne
# ────────────────────────────────────────────────────────────────────────────

def test_registra_consegna_ok(client, seed):
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 50, "qty_scorta": 5},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["commessa_id"] == COM_DONE
    assert data["qty_cliente"] == 50
    assert data["qty_scorta"] == 5
    assert data["quota"] == "mista"


def test_registra_consegna_solo_cliente(client, seed):
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 50, "qty_scorta": 0},
    )
    assert r.status_code == 201
    assert r.json()["quota"] == "cliente"


def test_registra_consegna_solo_scorta(client, seed):
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 0, "qty_scorta": 5},
    )
    assert r.status_code == 201
    assert r.json()["quota"] == "scorta"


def test_registra_consegna_duplicata(client, seed):
    """Seconda registrazione della stessa commessa → 409."""
    client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 50, "qty_scorta": 5},
    )
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 10, "qty_scorta": 0},
    )
    assert r.status_code == 409


def test_registra_consegna_commessa_non_completata(client, seed):
    """Commessa in_coda → non si può registrare in consegna."""
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_ID, "qty_cliente": 10, "qty_scorta": 0},
    )
    assert r.status_code == 409


def test_registra_consegna_not_found(client, seed):
    r = client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": "00000000-dead-beef-0000-000000000000",
              "qty_cliente": 10, "qty_scorta": 0},
    )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# GET /ordini/{id}/consegne
# ────────────────────────────────────────────────────────────────────────────

def test_get_consegne_ordine_after_registrazione(client, seed):
    client.post(
        "/api/magazzino/consegne",
        json={"commessa_id": COM_DONE, "qty_cliente": 50, "qty_scorta": 5},
    )
    r = client.get(f"/api/magazzino/ordini/{ORD_ID}/consegne")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["commessa_id"] == COM_DONE


def test_get_consegne_ordine_empty(client, seed):
    r = client.get(f"/api/magazzino/ordini/{ORD_ID}/consegne")
    assert r.status_code == 200
    assert r.json() == []


# ────────────────────────────────────────────────────────────────────────────
# POST /ordini/{id}/pronto
# ────────────────────────────────────────────────────────────────────────────

def test_segna_ordine_pronto(client, seed):
    r = client.post(f"/api/magazzino/ordini/{ORD_ID}/pronto", json={"nota": "tutto ok"})
    assert r.status_code == 201
    data = r.json()
    assert data["tipo"] == "ordine_pronto"
    assert data["mittente"] == "magazzino"
    assert data["destinatario"] == "logistica"
    assert data["stato"] == "aperto"
    assert data["ref_ordine_id"] == ORD_ID


def test_segna_ordine_pronto_idempotente(client, seed):
    """Secondo call restituisce lo stesso evento senza crearne uno nuovo."""
    r1 = client.post(f"/api/magazzino/ordini/{ORD_ID}/pronto", json={})
    r2 = client.post(f"/api/magazzino/ordini/{ORD_ID}/pronto", json={"nota": "di nuovo"})
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


def test_segna_ordine_pronto_not_found(client, seed):
    r = client.post(
        "/api/magazzino/ordini/00000000-dead-beef-0000-000000000000/pronto",
        json={},
    )
    assert r.status_code == 404
