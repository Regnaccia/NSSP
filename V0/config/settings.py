from dotenv import load_dotenv
from pathlib import Path
import os
import urllib.parse

_env_dir = Path(__file__).parent.parent / "env"

load_dotenv(_env_dir / "postgres.env")
load_dotenv(_env_dir / "easy.env")

# Internal DB (Postgres)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

MRS_DB_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Easy external DB (SQL Server via pyodbc)
EASY_DB_DRIVER = os.getenv("EASY_DB_DRIVER", "SQL Server")
EASY_DB_SERVER = os.getenv("EASY_DB_SERVER")
EASY_DB_NAME = os.getenv("EASY_DB_NAME")
EASY_DB_USER = os.getenv("EASY_DB_USER")
EASY_DB_PASSWORD = os.getenv("EASY_DB_PASSWORD")

_easy_odbc = (
    f"DRIVER={{{EASY_DB_DRIVER}}};"
    f"SERVER={EASY_DB_SERVER};"
    f"DATABASE={EASY_DB_NAME};"
    f"UID={EASY_DB_USER};"
    f"PWD={EASY_DB_PASSWORD}"
)

EASY_DB_URL = (
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(_easy_odbc)}"
    if all([EASY_DB_SERVER, EASY_DB_NAME, EASY_DB_USER])
    else None
)
