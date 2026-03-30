"""
Test per il modulo Auth — POST /api/auth/login, /me, /utenti CRUD.

Copre:
  - Login: successo, password sbagliata, utente disabilitato
  - GET /me: token valido, assente, invalido
  - POST /utenti: solo admin (201, 409 duplicato, 403 non-admin)
  - GET /utenti: solo admin
  - PATCH /utenti/{id}: password, ruolo, disabilita
  - 401 senza token su endpoint protetti
"""
import pytest
from tests.conftest import auth, ADMIN_ID, PROD_ID


# ────────────────────────────────────────────────────────────────────────────
# Login
# ────────────────────────────────────────────────────────────────────────────

def test_login_success(client, seed):
    r = client.post("/api/auth/login", json={"username": "admin_test", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["ruolo"] == "admin"
    assert data["username"] == "admin_test"


def test_login_wrong_password(client, seed):
    r = client.post("/api/auth/login", json={"username": "admin_test", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client, seed):
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_login_disabled_user(client, seed, db):
    from app.models.utente import Utente
    utente = db.get(Utente, PROD_ID)
    utente.attivo = False
    db.flush()

    r = client.post("/api/auth/login", json={"username": "prod_test", "password": "prod123"})
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# GET /me
# ────────────────────────────────────────────────────────────────────────────

def test_me_valid_token(client, seed, admin_token):
    r = client.get("/api/auth/me", headers=auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "admin_test"
    assert data["ruolo"] == "admin"


def test_me_no_token(client, seed):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_invalid_token(client, seed):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer INVALID.TOKEN.HERE"})
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# POST /utenti — crea utente (solo admin)
# ────────────────────────────────────────────────────────────────────────────

def test_crea_utente_admin_ok(client, seed, admin_token):
    r = client.post(
        "/api/auth/utenti",
        json={"username": "nuovo_user", "password": "pass123", "ruolo": "magazzino"},
        headers=auth(admin_token),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "nuovo_user"
    assert data["ruolo"] == "magazzino"
    assert data["attivo"] is True


def test_crea_utente_duplicate_username(client, seed, admin_token):
    r = client.post(
        "/api/auth/utenti",
        json={"username": "admin_test", "password": "x", "ruolo": "admin"},
        headers=auth(admin_token),
    )
    assert r.status_code == 409


def test_crea_utente_ruolo_invalido(client, seed, admin_token):
    r = client.post(
        "/api/auth/utenti",
        json={"username": "x", "password": "x", "ruolo": "superman"},
        headers=auth(admin_token),
    )
    assert r.status_code == 409


def test_crea_utente_forbidden_non_admin(client, seed, prod_token):
    r = client.post(
        "/api/auth/utenti",
        json={"username": "y", "password": "y", "ruolo": "produzione"},
        headers=auth(prod_token),
    )
    assert r.status_code == 403


def test_crea_utente_no_token(client, seed):
    r = client.post(
        "/api/auth/utenti",
        json={"username": "z", "password": "z", "ruolo": "produzione"},
    )
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# GET /utenti — lista (solo admin)
# ────────────────────────────────────────────────────────────────────────────

def test_get_utenti_admin(client, seed, admin_token):
    r = client.get("/api/auth/utenti", headers=auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    usernames = [u["username"] for u in data]
    assert "admin_test" in usernames


def test_get_utenti_forbidden(client, seed, log_token):
    r = client.get("/api/auth/utenti", headers=auth(log_token))
    assert r.status_code == 403


# ────────────────────────────────────────────────────────────────────────────
# PATCH /utenti/{id} — aggiorna utente
# ────────────────────────────────────────────────────────────────────────────

def test_patch_utente_password(client, seed, admin_token):
    r = client.patch(
        f"/api/auth/utenti/{PROD_ID}",
        json={"password": "nuovapass"},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    # Verifica login con nuova password
    r2 = client.post("/api/auth/login", json={"username": "prod_test", "password": "nuovapass"})
    assert r2.status_code == 200


def test_patch_utente_disabilita(client, seed, admin_token):
    r = client.patch(
        f"/api/auth/utenti/{PROD_ID}",
        json={"attivo": False},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["attivo"] is False


def test_patch_utente_not_found(client, seed, admin_token):
    r = client.patch(
        "/api/auth/utenti/00000000-ffff-ffff-ffff-000000000000",
        json={"attivo": False},
        headers=auth(admin_token),
    )
    assert r.status_code == 409


def test_patch_utente_forbidden(client, seed, prod_token):
    r = client.patch(
        f"/api/auth/utenti/{PROD_ID}",
        json={"attivo": False},
        headers=auth(prod_token),
    )
    assert r.status_code == 403
