"""
Test router /api/logistica — Policy, clienti, spedizioni, calendario.

Copre:
  - GET /clienti: lista clienti con policy
  - PATCH /clienti/{id}: aggiorna nickname
  - GET /clienti/{id}/policy: 404 se non configurata
  - PUT /clienti/{id}/policy: crea e aggiorna (idempotente)
  - GET /da-spedire: ordini con evento ordine_pronto aperto
  - POST /spedizioni: crea spedizione
  - GET /spedizioni: lista
  - GET /spedizioni/{id}: dettaglio
  - PATCH /spedizioni/{id}: aggiorna
  - POST /spedizioni/{id}/spedita: segna come spedita
  - GET /calendario: vista per range date
  - Guard 403 per ruolo sbagliato
"""
from datetime import date, timedelta
import pytest
from tests.conftest import auth, CLI_ID, ORD_ID


# ────────────────────────────────────────────────────────────────────────────
# Clienti
# ────────────────────────────────────────────────────────────────────────────

def test_get_clienti(client, seed, log_token):
    r = client.get("/api/logistica/clienti", headers=auth(log_token))
    assert r.status_code == 200
    data = r.json()
    assert any(c["id"] == CLI_ID for c in data)


def test_get_clienti_forbidden(client, seed, prod_token):
    r = client.get("/api/logistica/clienti", headers=auth(prod_token))
    assert r.status_code == 403


def test_get_clienti_no_token(client, seed):
    r = client.get("/api/logistica/clienti")
    assert r.status_code == 401


def test_patch_nickname(client, seed, log_token):
    r = client.patch(
        f"/api/logistica/clienti/{CLI_ID}",
        json={"nickname": "NuovoNick"},
        headers=auth(log_token),
    )
    assert r.status_code == 204


def test_patch_nickname_not_found(client, seed, log_token):
    r = client.patch(
        "/api/logistica/clienti/00000000-dead-beef-0000-000000000000",
        json={"nickname": "x"},
        headers=auth(log_token),
    )
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Policy cliente
# ────────────────────────────────────────────────────────────────────────────

def test_get_policy_not_configured(client, seed, log_token):
    r = client.get(f"/api/logistica/clienti/{CLI_ID}/policy", headers=auth(log_token))
    assert r.status_code == 404


def test_upsert_policy_create(client, seed, log_token):
    r = client.put(
        f"/api/logistica/clienti/{CLI_ID}/policy",
        json={"tipo_policy": "DEFAULT", "corriere_preferito": "BRT"},
        headers=auth(log_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["tipo_policy"] == "DEFAULT"
    assert data["corriere_preferito"] == "BRT"


def test_upsert_policy_update_idempotente(client, seed, log_token):
    client.put(
        f"/api/logistica/clienti/{CLI_ID}/policy",
        json={"tipo_policy": "DEFAULT"},
        headers=auth(log_token),
    )
    r = client.put(
        f"/api/logistica/clienti/{CLI_ID}/policy",
        json={"tipo_policy": "GIORNO_FISSO", "giorno_fisso": 3},
        headers=auth(log_token),
    )
    assert r.status_code == 200
    assert r.json()["tipo_policy"] == "GIORNO_FISSO"
    assert r.json()["giorno_fisso"] == 3


def test_get_policy_after_create(client, seed, log_token):
    client.put(
        f"/api/logistica/clienti/{CLI_ID}/policy",
        json={"tipo_policy": "DATA_TASSATIVA"},
        headers=auth(log_token),
    )
    r = client.get(f"/api/logistica/clienti/{CLI_ID}/policy", headers=auth(log_token))
    assert r.status_code == 200
    assert r.json()["tipo_policy"] == "DATA_TASSATIVA"


def test_upsert_policy_cliente_not_found(client, seed, log_token):
    r = client.put(
        "/api/logistica/clienti/00000000-dead-beef-0000-000000000000/policy",
        json={"tipo_policy": "DEFAULT"},
        headers=auth(log_token),
    )
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# da-spedire
# ────────────────────────────────────────────────────────────────────────────

def _crea_evento_ordine_pronto(client, log_token):
    """Helper: crea un evento ordine_pronto via magazzino (no auth)."""
    client.post(f"/api/magazzino/ordini/{ORD_ID}/pronto", json={})


def test_da_spedire_vuota_senza_eventi(client, seed, log_token):
    r = client.get("/api/logistica/da-spedire", headers=auth(log_token))
    assert r.status_code == 200
    assert r.json() == []


def test_da_spedire_con_evento_pronto(client, seed, log_token):
    _crea_evento_ordine_pronto(client, log_token)
    r = client.get("/api/logistica/da-spedire", headers=auth(log_token))
    assert r.status_code == 200
    data = r.json()
    assert any(o["ordine_id"] == ORD_ID for o in data)


# ────────────────────────────────────────────────────────────────────────────
# Spedizioni
# ────────────────────────────────────────────────────────────────────────────

def _crea_spedizione(client, log_token, data_pianificata=None):
    if data_pianificata is None:
        data_pianificata = (date.today() + timedelta(days=3)).isoformat()
    return client.post(
        "/api/logistica/spedizioni",
        json={
            "ordine_id": ORD_ID,
            "tipo": "parziale",
            "corriere": "BRT",
            "data_pianificata": data_pianificata,
        },
        headers=auth(log_token),
    )


def test_crea_spedizione(client, seed, log_token):
    r = _crea_spedizione(client, log_token)
    assert r.status_code == 201
    data = r.json()
    assert data["ordine_id"] == ORD_ID
    assert data["stato"] == "in_preparazione"
    assert data["corriere"] == "BRT"


def test_crea_spedizione_ordine_not_found(client, seed, log_token):
    r = client.post(
        "/api/logistica/spedizioni",
        json={"ordine_id": "00000000-dead-beef-0000-000000000000", "tipo": "totale"},
        headers=auth(log_token),
    )
    assert r.status_code == 404


def test_get_spedizioni(client, seed, log_token):
    _crea_spedizione(client, log_token)
    r = client.get("/api/logistica/spedizioni", headers=auth(log_token))
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_get_spedizioni_filter_stato(client, seed, log_token):
    _crea_spedizione(client, log_token)
    r = client.get("/api/logistica/spedizioni?stato=in_preparazione", headers=auth(log_token))
    assert r.status_code == 200
    assert all(s["stato"] == "in_preparazione" for s in r.json())


def test_get_spedizione_by_id(client, seed, log_token):
    sped_id = _crea_spedizione(client, log_token).json()["id"]
    r = client.get(f"/api/logistica/spedizioni/{sped_id}", headers=auth(log_token))
    assert r.status_code == 200
    assert r.json()["id"] == sped_id


def test_get_spedizione_not_found(client, seed, log_token):
    r = client.get(
        "/api/logistica/spedizioni/00000000-dead-beef-0000-000000000000",
        headers=auth(log_token),
    )
    assert r.status_code == 404


def test_patch_spedizione(client, seed, log_token):
    sped_id = _crea_spedizione(client, log_token).json()["id"]
    r = client.patch(
        f"/api/logistica/spedizioni/{sped_id}",
        json={"corriere": "GLS", "colli": 3},
        headers=auth(log_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["corriere"] == "GLS"
    assert data["colli"] == 3


def test_patch_spedizione_non_esistente(client, seed, log_token):
    r = client.patch(
        "/api/logistica/spedizioni/00000000-dead-beef-0000-000000000000",
        json={"corriere": "GLS"},
        headers=auth(log_token),
    )
    assert r.status_code == 409


def test_segna_spedita(client, seed, log_token):
    sped_id = _crea_spedizione(client, log_token).json()["id"]
    r = client.post(f"/api/logistica/spedizioni/{sped_id}/spedita", headers=auth(log_token))
    assert r.status_code == 200
    data = r.json()
    assert data["stato"] == "spedita"
    assert data["data_spedizione"] is not None


def test_segna_spedita_gia_spedita(client, seed, log_token):
    sped_id = _crea_spedizione(client, log_token).json()["id"]
    client.post(f"/api/logistica/spedizioni/{sped_id}/spedita", headers=auth(log_token))
    r = client.post(f"/api/logistica/spedizioni/{sped_id}/spedita", headers=auth(log_token))
    assert r.status_code == 409


def test_patch_spedizione_gia_spedita(client, seed, log_token):
    sped_id = _crea_spedizione(client, log_token).json()["id"]
    client.post(f"/api/logistica/spedizioni/{sped_id}/spedita", headers=auth(log_token))
    r = client.patch(
        f"/api/logistica/spedizioni/{sped_id}",
        json={"corriere": "DHL"},
        headers=auth(log_token),
    )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# Calendario
# ────────────────────────────────────────────────────────────────────────────

def test_calendario_vuoto(client, seed, log_token):
    today = date.today()
    data_da = today.isoformat()
    data_a = (today + timedelta(days=30)).isoformat()
    r = client.get(
        f"/api/logistica/calendario?data_da={data_da}&data_a={data_a}",
        headers=auth(log_token),
    )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_calendario_con_spedizione(client, seed, log_token):
    data_sped = (date.today() + timedelta(days=5)).isoformat()
    _crea_spedizione(client, log_token, data_pianificata=data_sped)

    today = date.today()
    r = client.get(
        f"/api/logistica/calendario?data_da={today.isoformat()}"
        f"&data_a={(today + timedelta(days=10)).isoformat()}",
        headers=auth(log_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["data"] is not None


def test_calendario_date_invalide(client, seed, log_token):
    today = date.today()
    r = client.get(
        f"/api/logistica/calendario?data_da={(today + timedelta(days=10)).isoformat()}"
        f"&data_a={today.isoformat()}",
        headers=auth(log_token),
    )
    assert r.status_code == 400


# ────────────────────────────────────────────────────────────────────────────
# Guard — admin può accedere come logistica
# ────────────────────────────────────────────────────────────────────────────

def test_admin_accede_logistica(client, seed, admin_token):
    r = client.get("/api/logistica/clienti", headers=auth(admin_token))
    assert r.status_code == 200
