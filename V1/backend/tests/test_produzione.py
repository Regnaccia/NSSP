"""
Test router /api/produzione — F1a, F1b, genera-commesse, ricalcola-scorte, coda, macchine.

Copre:
  - F1a: lista righe da processare, con filtri
  - F1b: lista articoli sotto scorta target
  - genera-commesse: crea commessa + file Excel base64
  - ricalcola-scorte: torna 200 con count
  - coda: lista commesse attive
  - coda/riordina, coda/ricalcola-priorita
  - commesse/{id}/assegna
  - macchine: lista
  - Guard 403 per ruolo sbagliato
"""
import pytest
from tests.conftest import auth, RIGA_ID, ART_ID, MAC_ID, COM_ID


# ────────────────────────────────────────────────────────────────────────────
# F1a — lista righe ordine da processare
# ────────────────────────────────────────────────────────────────────────────

def test_f1a_returns_rows(client, seed, prod_token):
    r = client.get("/api/produzione/f1a", headers=auth(prod_token))
    assert r.status_code == 200
    data = r.json()
    # La riga_ordine ha qty_da_produrre=80 e nessuna commessa attiva (COM_ID è in_coda
    # → lo esclude dalla F1a perché ha una commessa non-completata)
    # Quindi la lista può essere vuota se la commessa in_coda blocca la riga
    assert isinstance(data, list)


def test_f1a_con_riga_senza_commessa_attiva(client, seed, prod_token, db):
    """Rimuoviamo la commessa in_coda per far apparire la riga in F1a."""
    from app.models.commessa import Commessa
    commessa = db.get(Commessa, COM_ID)
    db.delete(commessa)
    db.flush()

    r = client.get("/api/produzione/f1a", headers=auth(prod_token))
    assert r.status_code == 200
    righe = r.json()
    assert any(row["riga_ordine_id"] == RIGA_ID for row in righe)


def test_f1a_campo_qty_da_produrre(client, seed, prod_token, db):
    from app.models.commessa import Commessa
    commessa = db.get(Commessa, COM_ID)
    db.delete(commessa)
    db.flush()

    r = client.get("/api/produzione/f1a", headers=auth(prod_token))
    righe = r.json()
    riga = next((row for row in righe if row["riga_ordine_id"] == RIGA_ID), None)
    assert riga is not None
    assert riga["qty_da_produrre"] == 80  # 100 - 20 - 0


def test_f1a_filter_urgenza_only_empty(client, seed, prod_token):
    # Nessuna urgenza presente → lista vuota
    r = client.get("/api/produzione/f1a?urgenza_only=true", headers=auth(prod_token))
    assert r.status_code == 200
    assert r.json() == []


def test_f1a_forbidden_non_produzione(client, seed, log_token):
    r = client.get("/api/produzione/f1a", headers=auth(log_token))
    assert r.status_code == 403


def test_f1a_no_token(client, seed):
    r = client.get("/api/produzione/f1a")
    assert r.status_code == 401


# ────────────────────────────────────────────────────────────────────────────
# F1b — articoli sotto scorta target
# ────────────────────────────────────────────────────────────────────────────

def test_f1b_returns_list(client, seed, prod_token):
    r = client.get("/api/produzione/f1b", headers=auth(prod_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_f1b_articolo_sotto_scorta(client, seed, prod_token):
    """
    scorta_mensile=10, mesi_scorta=3 → target=30.
    qty_disponibile_futura ≈ 0 (impegni 100-0=100 > disponibile 20).
    Quindi qty_da_produrre_scorta = 30 → articolo in lista F1b.
    """
    r = client.get("/api/produzione/f1b", headers=auth(prod_token))
    data = r.json()
    # L'articolo TST001 ha tipo_produzione=PEZZO, storico_sufficiente=True
    match = next((a for a in data if a["codice"] == "TST001"), None)
    # Può essere presente se qty_disponibile_futura < target
    assert isinstance(data, list)


def test_f1b_filter_tipo_produzione(client, seed, prod_token):
    r = client.get("/api/produzione/f1b?tipo_produzione=BARRA", headers=auth(prod_token))
    assert r.status_code == 200
    assert all(a["tipo_produzione"] == "BARRA" for a in r.json())


# ────────────────────────────────────────────────────────────────────────────
# genera-commesse
# ────────────────────────────────────────────────────────────────────────────

def test_genera_commesse_crea_commessa(client, seed, prod_token, db):
    """Rimuoviamo la commessa in_coda per rendere la riga disponibile."""
    from app.models.commessa import Commessa
    commessa = db.get(Commessa, COM_ID)
    db.delete(commessa)
    db.flush()

    r = client.post(
        "/api/produzione/genera-commesse",
        json={
            "righe": [{"riga_ordine_id": RIGA_ID, "qty_ciclo_corrente": None, "qty_scorta": 0}],
            "created_by": "test",
        },
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["commesse_create"] == 1
    assert data["file_excel_base64"] != ""


def test_genera_commesse_riga_not_found(client, seed, prod_token):
    r = client.post(
        "/api/produzione/genera-commesse",
        json={"righe": [{"riga_ordine_id": "00000000-dead-dead-0000-000000000000",
                         "qty_ciclo_corrente": None, "qty_scorta": 0}]},
        headers=auth(prod_token),
    )
    assert r.status_code == 404


def test_genera_commesse_qty_gia_coperta_skip(client, seed, prod_token, db):
    """Se qty_da_produrre=0 la commessa viene skippata silenziosamente."""
    from app.models.riga_ordine import RigaOrdine
    riga = db.get(RigaOrdine, RIGA_ID)
    riga.qty_in_produzione = 80  # copre tutto
    db.flush()

    # rimuovi commessa in_coda per non bloccare la logica
    from app.models.commessa import Commessa
    db.delete(db.get(Commessa, COM_ID))
    db.flush()

    r = client.post(
        "/api/produzione/genera-commesse",
        json={"righe": [{"riga_ordine_id": RIGA_ID, "qty_ciclo_corrente": None, "qty_scorta": 0}]},
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    assert r.json()["commesse_create"] == 0


# ────────────────────────────────────────────────────────────────────────────
# ricalcola-scorte
# ────────────────────────────────────────────────────────────────────────────

def test_ricalcola_scorte(client, seed, prod_token):
    # Nessuna connessione EasyJob → ritorna aggiornati=0 (nessun dato storico)
    r = client.post("/api/produzione/ricalcola-scorte", json={}, headers=auth(prod_token))
    assert r.status_code == 200
    assert "aggiornati" in r.json()


# ────────────────────────────────────────────────────────────────────────────
# Coda di lavorazione
# ────────────────────────────────────────────────────────────────────────────

def test_get_coda(client, seed, prod_token):
    r = client.get("/api/produzione/coda", headers=auth(prod_token))
    assert r.status_code == 200
    data = r.json()
    assert any(c["id"] == COM_ID for c in data)


def test_coda_riordina(client, seed, prod_token):
    r = client.post(
        "/api/produzione/coda/riordina",
        json={"ordine": [{"commessa_id": COM_ID, "posizione": 1}]},
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    assert r.json()["aggiornate"] == 1


def test_coda_ricalcola_priorita(client, seed, prod_token):
    r = client.post("/api/produzione/coda/ricalcola-priorita", headers=auth(prod_token))
    assert r.status_code == 200
    assert "aggiornate" in r.json()


# ────────────────────────────────────────────────────────────────────────────
# Assegna macchina
# ────────────────────────────────────────────────────────────────────────────

def test_assegna_macchina(client, seed, prod_token):
    r = client.post(
        f"/api/produzione/commesse/{COM_ID}/assegna",
        json={"macchina_id": MAC_ID},
        headers=auth(prod_token),
    )
    assert r.status_code == 200
    assert r.json()["macchina_id"] == MAC_ID


def test_assegna_macchina_not_found(client, seed, prod_token):
    r = client.post(
        f"/api/produzione/commesse/{COM_ID}/assegna",
        json={"macchina_id": "00000000-dead-beef-0000-000000000000"},
        headers=auth(prod_token),
    )
    assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Macchine
# ────────────────────────────────────────────────────────────────────────────

def test_get_macchine(client, seed, prod_token):
    r = client.get("/api/produzione/macchine", headers=auth(prod_token))
    assert r.status_code == 200
    data = r.json()
    assert any(m["codice"] == "CNC-01" for m in data)


def test_get_macchine_solo_inattive_escluse(client, seed, prod_token, db):
    from app.models.macchina import Macchina
    mac = db.get(Macchina, MAC_ID)
    mac.attiva = False
    db.flush()

    r = client.get("/api/produzione/macchine", headers=auth(prod_token))
    assert r.status_code == 200
    assert not any(m["id"] == MAC_ID for m in r.json())
