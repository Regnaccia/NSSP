from sqlalchemy import create_engine, text
from config.settings import EASY_DB_URL


def get_easy_engine():
    if not EASY_DB_URL:
        raise RuntimeError(
            "EASY_DB_URL non configurato. Compilare env/easy.env."
        )
    return create_engine(EASY_DB_URL)


def test_connection() -> bool:
    engine = get_easy_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
