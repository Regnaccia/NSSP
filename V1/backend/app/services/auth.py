"""
Servizi di autenticazione e gestione utenti (DL-ARCH-016).

- Hash password con bcrypt (passlib)
- JWT con PyJWT
- CRUD utenti (solo admin)
"""
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import JWT_SECRET, JWT_EXPIRE_HOURS
from app.models.utente import Utente

RUOLI_VALIDI = {"produzione", "magazzino", "logistica", "admin"}


class AuthError(Exception):
    pass


# ---------------------------------------------------------------------------
# Password
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_token(utente_id: str, username: str, ruolo: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": utente_id,
        "username": username,
        "ruolo": ruolo,
        "exp": exp,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """
    Decodifica il token JWT.
    Lancia AuthError se il token è scaduto o non valido.
    """
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token scaduto — effettuare nuovamente il login")
    except jwt.InvalidTokenError:
        raise AuthError("Token non valido")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def login(session: Session, username: str, password: str) -> dict:
    utente = (
        session.query(Utente)
        .filter(Utente.username == username, Utente.attivo.is_(True))
        .first()
    )
    if not utente or not verify_password(password, utente.password_hash):
        raise AuthError("Credenziali non valide")

    token = create_token(utente.id, utente.username, utente.ruolo)
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": utente.username,
        "ruolo": utente.ruolo,
    }


# ---------------------------------------------------------------------------
# CRUD utenti (solo admin)
# ---------------------------------------------------------------------------

def crea_utente(session: Session, username: str, password: str, ruolo: str) -> Utente:
    if ruolo not in RUOLI_VALIDI:
        raise AuthError(f"Ruolo '{ruolo}' non valido. Valori accettati: {RUOLI_VALIDI}")

    esistente = session.execute(
        text("SELECT id FROM utenti WHERE username = :u"), {"u": username}
    ).fetchone()
    if esistente:
        raise AuthError(f"Username '{username}' già in uso")

    utente = Utente(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=hash_password(password),
        ruolo=ruolo,
        attivo=True,
    )
    session.add(utente)
    session.commit()
    session.refresh(utente)
    return utente


def get_utenti(session: Session) -> list[Utente]:
    return session.query(Utente).order_by(Utente.username).all()


def aggiorna_utente(session: Session, utente_id: str, data: dict) -> Utente:
    utente = session.get(Utente, utente_id)
    if not utente:
        raise AuthError(f"Utente {utente_id} non trovato")

    if "password" in data and data["password"]:
        utente.password_hash = hash_password(data["password"])
    if "ruolo" in data and data["ruolo"]:
        if data["ruolo"] not in RUOLI_VALIDI:
            raise AuthError(f"Ruolo '{data['ruolo']}' non valido")
        utente.ruolo = data["ruolo"]
    if "attivo" in data and data["attivo"] is not None:
        utente.attivo = data["attivo"]

    session.commit()
    session.refresh(utente)
    return utente
