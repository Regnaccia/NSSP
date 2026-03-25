"""
Test connessioni DB — eseguire dalla root V0/:
    python -m debug.test_connections
"""

from config.settings import MRS_DB_URL, EASY_DB_URL


def test_postgres():
    from sqlalchemy import create_engine, text
    print("[ Postgres ]")
    print(f"  URL: {MRS_DB_URL}")
    try:
        engine = create_engine(MRS_DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).scalar()
        print(f"  OK — {result}")
        return True
    except Exception as e:
        print(f"  ERRORE — {e}")
        return False


def test_easy():
    from sync.easy.connector import test_connection
    print("[ Easy / SQL Server ]")
    print(f"  URL: {EASY_DB_URL}")
    try:
        test_connection()
        print("  OK")
        return True
    except Exception as e:
        print(f"  ERRORE — {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    pg = test_postgres()
    print()
    easy = test_easy()
    print("=" * 50)
    print(f"Postgres: {'OK' if pg else 'FAIL'}  |  Easy: {'OK' if easy else 'FAIL'}")
