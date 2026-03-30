# MRS Backend — Setup e Avvio

## Indice
1. [Requisiti](#1-requisiti)
2. [Struttura directory](#2-struttura-directory)
3. [Configurazione ambiente](#3-configurazione-ambiente)
4. [Avvio con Docker](#4-avvio-con-docker)
5. [Avvio sviluppo locale](#5-avvio-sviluppo-locale)
6. [Migrazioni database](#6-migrazioni-database)
7. [Creare il primo utente admin](#7-creare-il-primo-utente-admin)
8. [Eseguire i test](#8-eseguire-i-test)
9. [Variabili d'ambiente — riferimento completo](#9-variabili-dambiente--riferimento-completo)

---

## 1. Requisiti

| Componente | Versione minima |
|---|---|
| Python | 3.11+ |
| PostgreSQL | 15+ |
| Docker Desktop | 4.x (opzionale ma consigliato) |
| pyodbc + ODBC Driver 18 | Solo per sync EasyJob (opzionale in sviluppo) |

---

## 2. Struttura directory

```
V1/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── config.py            # Variabili d'ambiente
│   │   ├── database.py          # Engine SQLAlchemy + get_db
│   │   ├── deps.py              # Dipendenze JWT (get_current_user, require_ruolo)
│   │   ├── models/              # ORM SQLAlchemy (12 modelli)
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── routers/             # FastAPI routers (8 router)
│   │   ├── services/            # Business logic
│   │   └── sync/                # Sync EasyJob + scheduler APScheduler
│   ├── alembic/                 # Migrazioni DB
│   │   └── versions/
│   │       └── 20260327_001_initial_schema.py
│   ├── scripts/
│   │   └── create_admin.py      # Script creazione primo admin
│   ├── tests/                   # Test pytest (150 test)
│   ├── requirements.txt
│   ├── requirements-test.txt
│   └── pytest.ini
├── docker/
│   └── docker-compose.yml       # PostgreSQL containerizzato
└── env/
    ├── postgres.env             # Credenziali PostgreSQL
    └── easy.env                 # Credenziali EasyJob (SQL Server)
```

---

## 3. Configurazione ambiente

### 3.1 postgres.env

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=mrs_v1
POSTGRES_USER=nssp_user
POSTGRES_PASSWORD=nssp_password
```

### 3.2 easy.env

```env
EASYJOB_SERVER=<IP o hostname SQL Server>
EASYJOB_PORT=1433
EASYJOB_DATABASE=<nome DB EasyJob>
EASYJOB_USER=<utente SQL Server>
EASYJOB_PASSWORD=<password SQL Server>
EASYJOB_DRIVER=ODBC Driver 18 for SQL Server
```

> **Nota:** Se `easy.env` non è configurato o il server EasyJob non è raggiungibile,
> il backend parte comunque. Il sync sarà disabilitato e `GET /api/sync/status`
> mostrerà `easyjob_connesso: false`. La funzionalità `ricalcola-scorte` tornerà
> `aggiornati: 0` silenziosamente.

### 3.3 Variabili opzionali (in postgres.env o variabili d'ambiente)

```env
JWT_SECRET=<stringa segreta lunga e random — CAMBIARE IN PRODUZIONE>
JWT_EXPIRE_HOURS=8
KIOSK_CONTEXT=reparto   # o: magazzino (terminali fissi, non usato attivamente in MVP)
```

---

## 4. Avvio con Docker

```bash
# Avvia solo il container PostgreSQL
cd V1/docker/
docker compose up -d

# Verifica che sia healthy
docker ps
# STATUS: Up X minutes (healthy)
```

Il container mappa la porta `5432` sull'host locale.

---

## 5. Avvio sviluppo locale

```bash
# 1. Crea e attiva virtual environment
cd V1/backend/
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 2. Installa dipendenze
pip install -r requirements.txt

# 3. Applica migrazioni (vedi sezione 6)
alembic upgrade head

# 4. Crea admin (vedi sezione 7)
python scripts/create_admin.py

# 5. Avvia il server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

L'API sarà disponibile su:
- `http://localhost:8000` — base URL
- `http://localhost:8000/docs` — Swagger UI interattiva
- `http://localhost:8000/redoc` — ReDoc
- `http://localhost:8000/health` — health check

---

## 6. Migrazioni database

```bash
cd V1/backend/

# Applica tutte le migrazioni (crea le tabelle)
alembic upgrade head

# Verifica stato corrente
alembic current

# Rollback di una migrazione
alembic downgrade -1

# Rollback totale
alembic downgrade base
```

**Migrazioni esistenti:**

| Revisione | Data | Contenuto |
|---|---|---|
| `001` | 2026-03-27 | Schema iniziale completo (12 tabelle) |

---

## 7. Creare il primo utente admin

```bash
cd V1/backend/
python scripts/create_admin.py
```

Il script è interattivo: chiede username e password. È idempotente — se l'utente esiste già aggiorna la password e garantisce il ruolo `admin`.

Successivamente altri utenti si creano via API (`POST /api/auth/utenti`, solo admin).

**Ruoli disponibili:**

| Ruolo | Accesso |
|---|---|
| `admin` | Tutto, incluso sync, gestione utenti |
| `produzione` | Router `/api/produzione` + `/api/articoli` + `/api/eventi` |
| `logistica` | Router `/api/logistica` + `/api/eventi` |
| `magazzino` | (ruolo previsto, router `/api/magazzino` è kiosk senza auth) |

---

## 8. Eseguire i test

```bash
cd V1/backend/

# Installa dipendenze di test
pip install -r requirements-test.txt

# Crea il DB di test (una volta sola)
python -c "
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432,
                        user='nssp_user', password='nssp_password', dbname='postgres')
conn.autocommit = True
conn.cursor().execute('CREATE DATABASE mrs_test')
conn.close()
print('DB mrs_test creato')
"

# Lancia tutti i test
pytest -v

# Test specifico
pytest tests/test_auth.py -v

# Con coverage
pytest --cov=app --cov-report=term-missing
```

**Risultato atteso:** 150 test, tutti verdi, ~2 minuti.

Per usare un DB di test diverso:
```bash
MRS_TEST_DB_URL="postgresql+psycopg2://user:pass@host:port/dbname" pytest
```

---

## 9. Variabili d'ambiente — riferimento completo

| Variabile | Default | Descrizione |
|---|---|---|
| `POSTGRES_HOST` | `localhost` | Host PostgreSQL |
| `POSTGRES_PORT` | `5432` | Porta PostgreSQL |
| `POSTGRES_DB` | `mrs_v1` | Nome database MRS |
| `POSTGRES_USER` | `nssp_user` | Utente PostgreSQL |
| `POSTGRES_PASSWORD` | *(vuoto)* | Password PostgreSQL |
| `JWT_SECRET` | `insecure-dev-secret-change-in-production` | Chiave firma JWT — **cambiare in produzione** |
| `JWT_EXPIRE_HOURS` | `8` | Durata token JWT in ore |
| `KIOSK_CONTEXT` | *(vuoto)* | Contesto terminale kiosk (non usato attivamente in MVP) |
| `EASYJOB_SERVER` | *(vuoto)* | Hostname/IP SQL Server EasyJob |
| `EASYJOB_PORT` | `1433` | Porta SQL Server |
| `EASYJOB_DATABASE` | *(vuoto)* | Nome DB EasyJob |
| `EASYJOB_USER` | *(vuoto)* | Utente SQL Server |
| `EASYJOB_PASSWORD` | *(vuoto)* | Password SQL Server |
| `EASYJOB_DRIVER` | `ODBC Driver 18 for SQL Server` | Driver ODBC installato |
| `MRS_TEST_DB_URL` | `postgresql+psycopg2://nssp_user:nssp_password@localhost:5432/mrs_test` | URL DB di test per pytest |
