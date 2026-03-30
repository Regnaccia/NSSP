"""
Test unitari puri — nessuna connessione DB richiesta.

Copre:
  - auth.hash_password / verify_password
  - auth.create_token / decode_token (valido, scaduto, firma sbagliata)
  - disponibilita.get_qty_da_produrre
  - logistica.calcola_data_spedizione_suggerita
  - commesse._row_to_dict (qty_totale, qty_residua)
"""
import time
from datetime import date, timedelta

import pytest


# ────────────────────────────────────────────────────────────────────────────
# Auth — password
# ────────────────────────────────────────────────────────────────────────────

def test_hash_and_verify_correct_password():
    from app.services.auth import hash_password, verify_password
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed) is True


def test_verify_wrong_password():
    from app.services.auth import hash_password, verify_password
    hashed = hash_password("secret123")
    assert verify_password("wrong", hashed) is False


def test_hash_is_not_plain():
    from app.services.auth import hash_password
    assert hash_password("abc") != "abc"


def test_two_hashes_of_same_password_differ():
    from app.services.auth import hash_password
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt usa salt random


# ────────────────────────────────────────────────────────────────────────────
# Auth — JWT
# ────────────────────────────────────────────────────────────────────────────

def test_create_and_decode_token():
    from app.services.auth import create_token, decode_token
    token = create_token("uid-1", "mario", "produzione")
    payload = decode_token(token)
    assert payload["sub"] == "uid-1"
    assert payload["username"] == "mario"
    assert payload["ruolo"] == "produzione"


def test_decode_expired_token():
    from app.services.auth import AuthError
    import jwt, datetime, app.config as cfg

    expired_payload = {
        "sub": "uid-x",
        "username": "x",
        "ruolo": "admin",
        "exp": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1),
    }
    token = jwt.encode(expired_payload, cfg.JWT_SECRET, algorithm="HS256")
    with pytest.raises(AuthError, match="scaduto"):
        from app.services.auth import decode_token
        decode_token(token)


def test_decode_invalid_signature():
    from app.services.auth import create_token, decode_token, AuthError
    token = create_token("uid-1", "mario", "produzione")
    tampered = token[:-4] + "XXXX"
    with pytest.raises(AuthError):
        decode_token(tampered)


def test_decode_garbage_token():
    from app.services.auth import decode_token, AuthError
    with pytest.raises(AuthError):
        decode_token("not.a.jwt.at.all")


# ────────────────────────────────────────────────────────────────────────────
# Disponibilita — get_qty_da_produrre
# ────────────────────────────────────────────────────────────────────────────

class FakeRiga:
    def __init__(self, ordinata, disponibile, in_produzione):
        self.qty_ordinata = ordinata
        self.qty_disponibile = disponibile
        self.qty_in_produzione = in_produzione


def test_qty_da_produrre_positive():
    from app.services.disponibilita import get_qty_da_produrre
    riga = FakeRiga(100, 20, 10)
    assert get_qty_da_produrre(riga) == 70


def test_qty_da_produrre_zero_when_covered():
    from app.services.disponibilita import get_qty_da_produrre
    riga = FakeRiga(100, 60, 50)  # 100 - 60 - 50 = -10 → 0
    assert get_qty_da_produrre(riga) == 0


def test_qty_da_produrre_exact_zero():
    from app.services.disponibilita import get_qty_da_produrre
    riga = FakeRiga(100, 50, 50)
    assert get_qty_da_produrre(riga) == 0


# ────────────────────────────────────────────────────────────────────────────
# Logistica — calcola_data_spedizione_suggerita
# ────────────────────────────────────────────────────────────────────────────

def test_policy_data_tassativa():
    from app.services.logistica import calcola_data_spedizione_suggerita
    consegna = date.today() + timedelta(days=5)
    result = calcola_data_spedizione_suggerita("DATA_TASSATIVA", None, consegna)
    assert result == consegna


def test_policy_data_tassativa_none_consegna():
    from app.services.logistica import calcola_data_spedizione_suggerita
    result = calcola_data_spedizione_suggerita("DATA_TASSATIVA", None, None)
    assert result is None


def test_policy_default_returns_none():
    from app.services.logistica import calcola_data_spedizione_suggerita
    result = calcola_data_spedizione_suggerita("DEFAULT", None, None)
    assert result is None


def test_policy_soglia_valore_returns_none():
    from app.services.logistica import calcola_data_spedizione_suggerita
    result = calcola_data_spedizione_suggerita("SOGLIA_VALORE", None, None)
    assert result is None


def test_policy_giorno_fisso_returns_future_date():
    from app.services.logistica import calcola_data_spedizione_suggerita
    today = date.today()
    # Giorno fisso = lunedì (1). Risultato deve essere >= oggi e un lunedì (isoweekday==1)
    result = calcola_data_spedizione_suggerita("GIORNO_FISSO", 1, None)
    assert result is not None
    assert result > today
    assert result.isoweekday() == 1  # lunedì


def test_policy_giorno_fisso_capped_at_consegna():
    from app.services.logistica import calcola_data_spedizione_suggerita
    # data_consegna domani: il giorno fisso (lontano) deve essere cappato
    consegna = date.today() + timedelta(days=1)
    result = calcola_data_spedizione_suggerita("GIORNO_FISSO", 1, consegna)
    assert result is not None
    assert result <= consegna


# ────────────────────────────────────────────────────────────────────────────
# Commesse — _row_to_dict (qty_totale, qty_residua)
# ────────────────────────────────────────────────────────────────────────────

def test_row_to_dict_qty_totale_and_residua():
    from app.services.commesse import _row_to_dict

    row = {
        "id": "x", "stato": "in_produzione",
        "qty_cliente": 80, "qty_scorta": 10,
        "qty_prodotta_cliente": 30, "qty_prodotta_scorta": 5,
        "posizione_coda": 1, "priorita_suggerita": 2,
        "qty_ciclo_corrente": None,
        "created_at": None, "created_by": None,
        "sospesa_at": None, "sospesa_nota": None,
        "completata_at": None, "ldp_easyjob": None,
        "riga_ordine_id": None, "articolo_id": "a",
        "macchina_id": None, "codice_articolo": "ART1",
        "descrizione_articolo": "Desc", "macchina_codice": None,
        "numero_ordine": None,
    }
    result = _row_to_dict(row)
    assert result["qty_totale"] == 90   # 80 + 10
    assert result["qty_residua"] == 55  # 90 - (30+5)


def test_row_to_dict_residua_non_negative():
    from app.services.commesse import _row_to_dict

    row = {
        "id": "x", "stato": "completata",
        "qty_cliente": 50, "qty_scorta": 0,
        "qty_prodotta_cliente": 60, "qty_prodotta_scorta": 0,  # over-produced
        "posizione_coda": None, "priorita_suggerita": None,
        "qty_ciclo_corrente": None, "created_at": None, "created_by": None,
        "sospesa_at": None, "sospesa_nota": None, "completata_at": None,
        "ldp_easyjob": None, "riga_ordine_id": None,
        "articolo_id": "a", "macchina_id": None,
        "codice_articolo": "X", "descrizione_articolo": None,
        "macchina_codice": None, "numero_ordine": None,
    }
    result = _row_to_dict(row)
    assert result["qty_residua"] == 0  # max(0, ...)
