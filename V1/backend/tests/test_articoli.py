"""
Test GET /api/articoli, GET /api/articoli/{id}, PATCH /api/articoli/{id}.
"""
from tests.conftest import auth, ART_ID


def test_list_articoli(client, seed, admin_token):
    r = client.get("/api/articoli", headers=auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert any(a["codice"] == "TST001" for a in data)


def test_list_articoli_filter_categoria(client, seed, admin_token):
    r = client.get("/api/articoli?categoria=CAT_X", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(a["categoria"] == "CAT_X" for a in r.json())


def test_list_articoli_filter_tipo_produzione(client, seed, admin_token):
    r = client.get("/api/articoli?tipo_produzione=PEZZO", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(a["tipo_produzione"] == "PEZZO" for a in r.json())


def test_list_articoli_filter_storico_sufficiente(client, seed, admin_token):
    r = client.get("/api/articoli?storico_sufficiente=true", headers=auth(admin_token))
    assert r.status_code == 200
    assert all(a["storico_sufficiente"] is True for a in r.json())


def test_list_articoli_no_token(client, seed):
    r = client.get("/api/articoli")
    assert r.status_code == 401


def test_get_articolo_found(client, seed, admin_token):
    r = client.get(f"/api/articoli/{ART_ID}", headers=auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert data["codice"] == "TST001"
    assert data["id"] == ART_ID


def test_get_articolo_not_found(client, seed, admin_token):
    r = client.get("/api/articoli/00000000-dead-beef-0000-000000000000", headers=auth(admin_token))
    assert r.status_code == 404


def test_patch_articolo_mrs_fields(client, seed, admin_token):
    r = client.patch(
        f"/api/articoli/{ART_ID}",
        json={"mesi_scorta": 6, "tipo_produzione": "BARRA"},
        headers=auth(admin_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["mesi_scorta"] == 6
    assert data["tipo_produzione"] == "BARRA"


def test_patch_articolo_not_found(client, seed, admin_token):
    r = client.patch(
        "/api/articoli/00000000-dead-beef-0000-000000000000",
        json={"mesi_scorta": 3},
        headers=auth(admin_token),
    )
    assert r.status_code == 404


def test_patch_articolo_no_token(client, seed):
    r = client.patch(f"/api/articoli/{ART_ID}", json={"mesi_scorta": 3})
    assert r.status_code == 401
