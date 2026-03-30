from pathlib import Path
import os
import urllib.parse
from dotenv import load_dotenv

_env_dir = Path(__file__).parent.parent.parent / "env"

load_dotenv(_env_dir / "postgres.env")
load_dotenv(_env_dir / "easy.env")

# PostgreSQL (database MRS)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mrs_v1")
POSTGRES_USER = os.getenv("POSTGRES_USER", "mrs_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

MRS_DB_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# EasyJob (SQL Server esterno)
EASYJOB_SERVER = os.getenv("EASYJOB_SERVER")
EASYJOB_PORT = os.getenv("EASYJOB_PORT", "1433")
EASYJOB_DATABASE = os.getenv("EASYJOB_DATABASE")
EASYJOB_USER = os.getenv("EASYJOB_USER")
EASYJOB_PASSWORD = os.getenv("EASYJOB_PASSWORD")
EASYJOB_DRIVER = os.getenv("EASYJOB_DRIVER", "ODBC Driver 18 for SQL Server")

# Per istanze named (es. SERVER\SQLEXPRESS) non aggiungere la porta:
# il SQL Server Browser Service risolve il numero di porta automaticamente.
# La porta esplicita si usa solo con istanze default (solo IP/hostname).
_server_str = (
    EASYJOB_SERVER
    if (EASYJOB_SERVER and "\\" in EASYJOB_SERVER)
    else f"{EASYJOB_SERVER},{EASYJOB_PORT}"
)

_easy_odbc = (
    f"DRIVER={{{EASYJOB_DRIVER}}};"
    f"SERVER={_server_str};"
    f"DATABASE={EASYJOB_DATABASE};"
    f"UID={EASYJOB_USER};"
    f"PWD={EASYJOB_PASSWORD};"
    "TrustServerCertificate=yes;"
)

EASYJOB_DB_URL = (
    f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(_easy_odbc)}"
    if all([EASYJOB_SERVER, EASYJOB_DATABASE, EASYJOB_USER])
    else None
)

# Auth
JWT_SECRET = os.getenv("JWT_SECRET", "insecure-dev-secret-change-in-production")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "8"))

# Kiosk
KIOSK_CONTEXT = os.getenv("KIOSK_CONTEXT")

# Frequenze sync (minuti)
SYNC_INTERVAL_FAST_MIN = 5    # ordini, righe_ordine
SYNC_INTERVAL_SLOW_MIN = 60   # articoli, clienti
