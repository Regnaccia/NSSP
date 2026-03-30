"""Connessione al database SQL Server di EasyJob."""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import EASYJOB_DB_URL


def get_easyjob_engine():
    if not EASYJOB_DB_URL:
        raise RuntimeError(
            "EasyJob non configurato: impostare EASYJOB_SERVER, EASYJOB_DATABASE, "
            "EASYJOB_USER e EASYJOB_PASSWORD in env/easy.env"
        )
    return create_engine(EASYJOB_DB_URL, pool_pre_ping=True)


def test_easyjob_connection() -> bool:
    """Verifica che la connessione a EasyJob sia attiva. Usato da /api/sync/status."""
    try:
        engine = get_easyjob_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def fetch_easyjob(query: str, params: dict | None = None) -> list[dict]:
    """Esegue una query su EasyJob e restituisce i risultati come lista di dict."""
    engine = get_easyjob_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query), params or {})
        cols = result.keys()
        return [dict(zip(cols, row)) for row in result.fetchall()]
