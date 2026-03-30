"""
Test router /api/eventi — Urgenza, feedback, risolvi, rifiuta.

Copre:
  - POST /urgenza: crea urgenza_formale, ricalcola coda
  - POST /urgenza: ordine not found (404)
  - GET /eventi: lista con filtri
  - GET /eventi/{id}: dettaglio
  - GET /eventi/{id}: not found (404)
  - POST /{id}/feedback: risposta produzione (accettata / non_fattibile)
  - POST /{id}/feedback: tipo evento sbagliato (409)
  - POST /{id}/risolvi: risolve evento, ricalcola coda
  - POST /{id}/risolvi: già risolto (409)
  - POST /{id}/rifiuta: rifiuta evento
  - POST /{id}/rifiuta: già rifiutato (409)
  - Guard JWT: 401 senza token
"""
from tests.conftest import auth, ORD_ID


# ────────────────────────────────────────────────────────────────────────────
# POST /urgenza
# ────────────────────────────────────────────────────────────────────────────

def test_crea_urgenza(client, seed, log_token):
    r = client.post(
        "/api/eventi/urgenza",
        json={"ordine_id": ORD_ID, "nota": "urgente per cliente VIP"},
        headers=auth(log_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["tipo"] == "urgenza_formale"
    assert data["mittente"] == "logistica"
    assert data["destinatario"] == "produzione"
    assert data["stato"] == "aperto"
    assert data["ref_ordine_id"] == ORD_ID
    assert data["nota"] == "urgente per cliente VIP"


def test_crea_urgenza_ordine_not_found(client, seed, log_token):
    r = client.post(
        "/api/eventi/urgenza",
        json={"ordine_id": "00000000-dead-beef-0000-000000000000"},
        headers=auth(log_token),
    )
    assert r.status_code == 404


def test_crea_urgenza_no_token(client, seed):
    r = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID})
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# GET /eventi — lista
# ────────────────────────────────────────────────────────────────────────────

def test_get_eventi_lista_vuota(client, seed, admin_token):
    r = client.get("/api/eventi", headers=auth(admin_token))
    assert r.status_code == 200
    assert r.json() == []


def test_get_eventi_dopo_urgenza(client, seed, log_token, admin_token):
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))
    r = client.get("/api/eventi", headers=auth(admin_token))
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_eventi_filter_tipo(client, seed, log_token, admin_token):
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))
    r = client.get("/api/eventi?tipo=urgenza_formale", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(e["tipo"] == "urgenza_formale" for e in r.json())


def test_get_eventi_filter_destinatario(client, seed, log_token, admin_token):
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))
    r = client.get("/api/eventi?destinatario=produzione", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(e["destinatario"] == "produzione" for e in r.json())


def test_get_eventi_filter_stato(client, seed, log_token, admin_token):
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))
    r = client.get("/api/eventi?stato=aperto", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(e["stato"] == "aperto" for e in r.json())


def test_get_eventi_filter_ref_ordine(client, seed, log_token, admin_token):
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))
    r = client.get(f"/api/eventi?ref_ordine_id={ORD_ID}", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(e["ref_ordine_id"] == ORD_ID for e in r.json())


def test_get_eventi_no_token(client, seed):
    r = client.get("/api/eventi")
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# GET /eventi/{id} — dettaglio
# ────────────────────────────────────────────────────────────────────────────

def test_get_evento_dettaglio(client, seed, log_token, admin_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    r = client.get(f"/api/eventi/{ev_id}", headers=auth(admin_token))
    assert r.status_code == 200
    assert r.json()["id"] == ev_id
    assert r.json()["numero_ordine"] == "T-001"


def test_get_evento_not_found(client, seed, admin_token):
    r = client.get("/api/eventi/00000000-dead-beef-0000-000000000000",
                   headers=auth(admin_token))
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# POST /{id}/feedback
# ────────────────────────────────────────────────────────────────────────────

def test_feedback_accettata(client, seed, log_token, prod_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    r = client.post(
        f"/api/eventi/{ev_id}/feedback",
        json={"feedback_stato": "accettata", "feedback_nota": "ci proviamo"},
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["stato"] == "in_lavorazione"
    assert data["feedback_stato"] == "accettata"
    assert data["feedback_nota"] == "ci proviamo"


def test_feedback_non_fattibile(client, seed, log_token, prod_token):
    from datetime import date, timedelta
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    data_prevista = (date.today() + timedelta(days=10)).isoformat()
    r = client.post(
        f"/api/eventi/{ev_id}/feedback",
        json={
            "feedback_stato": "non_fattibile",
            "feedback_data_prevista": data_prevista,
            "feedback_nota": "macchina guasta",
        },
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    assert r.json()["feedback_stato"] == "non_fattibile"
    assert r.json()["feedback_data_prevista"] == data_prevista


def test_feedback_stato_invalido(client, seed, log_token, prod_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    r = client.post(
        f"/api/eventi/{ev_id}/feedback",
        json={"feedback_stato": "forse"},
        headers=auth(prod_token),
    )
    assert r.status_code == 409


def test_feedback_on_ordine_pronto_fails(client, seed, prod_token):
    """Il feedback si applica solo a urgenza_formale, non a ordine_pronto."""
    pronto = client.post(f"/api/magazzino/ordini/{ORD_ID}/pronto", json={}).json()
    ev_id = pronto["id"]
    r = client.post(
        f"/api/eventi/{ev_id}/feedback",
        json={"feedback_stato": "accettata"},
        headers=auth(prod_token),
    )
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# POST /{id}/risolvi
# ────────────────────────────────────────────────────────────────────────────

def test_risolvi_evento(client, seed, log_token, admin_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    r = client.post(
        f"/api/eventi/{ev_id}/risolvi",
        json={"nota": "problema risolto"},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["stato"] == "risolto"
    assert data["resolved_at"] is not None


def test_risolvi_gia_risolto(client, seed, log_token, admin_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    client.post(f"/api/eventi/{ev_id}/risolvi", json={}, headers=auth(admin_token))
    r = client.post(f"/api/eventi/{ev_id}/risolvi", json={}, headers=auth(admin_token))
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# POST /{id}/rifiuta
# ────────────────────────────────────────────────────────────────────────────

def test_rifiuta_evento(client, seed, log_token, admin_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    r = client.post(
        f"/api/eventi/{ev_id}/rifiuta",
        json={"nota": "non necessaria"},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["stato"] == "rifiutato"


def test_rifiuta_gia_rifiutato(client, seed, log_token, admin_token):
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    client.post(f"/api/eventi/{ev_id}/rifiuta", json={}, headers=auth(admin_token))
    r = client.post(f"/api/eventi/{ev_id}/rifiuta", json={}, headers=auth(admin_token))
    assert r.status_code == 409


def test_rifiuta_evento_risolto(client, seed, log_token, admin_token):
    """Non si può rifiutare un evento già risolto."""
    ev_id = client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                        headers=auth(log_token)).json()["id"]
    client.post(f"/api/eventi/{ev_id}/risolvi", json={}, headers=auth(admin_token))
    r = client.post(f"/api/eventi/{ev_id}/rifiuta", json={}, headers=auth(admin_token))
    assert r.status_code == 409


# ────────────────────────────────────────────────────────────────────────────
# Ricalcolo coda automatico dopo urgenza
# ────────────────────────────────────────────────────────────────────────────

def test_urgenza_ricalcola_coda(client, seed, log_token, prod_token):
    """Dopo creazione urgenza, la commessa deve avere priorita_suggerita=1."""
    # Prima del evento urgenza
    coda_prima = client.get("/api/produzione/coda", headers=auth(prod_token)).json()
    commessa_prima = next((c for c in coda_prima if c["priorita_suggerita"] == 1), None)

    # Crea urgenza
    client.post("/api/eventi/urgenza", json={"ordine_id": ORD_ID},
                headers=auth(log_token))

    coda_dopo = client.get("/api/produzione/coda", headers=auth(prod_token)).json()
    commessa_dopo = next((c for c in coda_dopo if c["priorita_suggerita"] == 1), None)
    assert commessa_dopo is not None  # almeno una commessa urgente
