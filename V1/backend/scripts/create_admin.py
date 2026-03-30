"""
Script one-shot: crea il primo utente admin in MRS V1.

Esecuzione (dalla cartella V1/backend):
    python scripts/create_admin.py

Chiede username e password interattivamente.
Se l'utente esiste già, aggiorna solo la password.
"""
import sys
import os
import getpass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.services.auth import crea_utente, aggiorna_utente, AuthError
from sqlalchemy import text


def main():
    print("=== MRS V1 — Crea utente admin ===\n")
    username = input("Username [admin]: ").strip() or "admin"
    password = getpass.getpass("Password: ")
    if not password:
        print("Errore: password non può essere vuota.")
        sys.exit(1)

    confirm = getpass.getpass("Conferma password: ")
    if password != confirm:
        print("Errore: le password non coincidono.")
        sys.exit(1)

    session = SessionLocal()
    try:
        esistente = session.execute(
            text("SELECT id FROM utenti WHERE username = :u"), {"u": username}
        ).fetchone()

        if esistente:
            aggiorna_utente(session, esistente[0], {"password": password, "ruolo": "admin", "attivo": True})
            print(f"\nUtente '{username}' aggiornato con ruolo admin.")
        else:
            crea_utente(session, username, password, "admin")
            print(f"\nUtente '{username}' creato con ruolo admin.")

        print("Login disponibile su: POST /api/auth/login")
    except AuthError as exc:
        print(f"Errore: {exc}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
