# IMPLEMENTATION V1 — Fase 0: Scaffold backend + schema DB + sync EasyJob

*Data: 2026-03-27*

---

## Obiettivo

Costruire l'infrastruttura base di MRS V1: schema DB completo, layer sync EasyJob e entry point FastAPI con scheduler. Nessuna business logic — solo i dati ci sono e il sistema gira.

---

## Cosa è stato fatto

### 1. Struttura progetto

```
V1/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point + lifespan scheduler
│   │   ├── config.py            # Settings da env/ (pattern V0)
│   │   ├── database.py          # SQLAlchemy engine + SessionLocal + Base
│   │   ├── models/              # 12 ORM models SQLAlchemy 2.x
│   │   ├── routers/sync.py      # /api/sync/status + /force/*
│   │   ├── services/__init__.py # placeholder Fase 1+
│   │   └── sync/
│   │       ├── easyjob.py       # Connessione SQL Server
│   │       ├── handlers.py      # Sync handlers per tabella
│   │       └── scheduler.py     # APScheduler background jobs
│   ├── alembic/                 # Migration Alembic
│   │   └── versions/20260327_001_initial_schema.py
│   ├── alembic.ini
│   └── requirements.txt
├── env/
│   ├── easy.env                 # Credenziali EasyJob (da V0)
│   ├── easy.env.example
│   ├── postgres.env             # Credenziali PostgreSQL
│   └── postgres.env.example
└── docker/
    └── compose.yml              # Non usato in Fase 0 — si riusa il container V0
```

### 2. Schema DB — 12 tabelle

Tutte con UUID PK, timestamp UTC.

| Tabella | Tipo | Proprietario |
|---|---|---|
| `articoli` | Sync-owned | `sync/handlers.py` |
| `clienti` | Sync-owned | `sync/handlers.py` |
| `ordini` | Sync-owned | `sync/handlers.py` |
| `righe_ordine` | Sync-owned | `sync/handlers.py` |
| `commesse` | MRS-owned | `services/commesse.py` (Fase 2) |
| `policy_clienti` | MRS-owned | `services/logistica.py` (Fase 3) |
| `eventi` | MRS-owned | `services/eventi.py` (Fase 4) |
| `macchine` | MRS-owned | `services/reparto.py` (Fase 2) |
| `sync_log` | Infra | `sync/handlers.py` |
| `consegne_magazzino` | MRS-owned | `services/reparto.py` (Fase 2) |
| `spedizioni` | MRS-owned | `services/logistica.py` (Fase 3) |
| `utenti` | MRS-owned | Auth (Fase 1+) |

### 3. Sync EasyJob

**Sorgenti EasyJob → tabelle MRS:**

| Handler | Sorgente EasyJob | Tabelle aggiornate | Frequenza |
|---|---|---|---|
| `sync_articoli` | `ANAART` | `articoli` | 60 min |
| `sync_clienti` | `ANACLI` | `clienti` | 60 min |
| `sync_ordini_e_righe` | `V_TORDCLI` + `DPRE_PROD` | `ordini` + `righe_ordine` | 5 min |

**Logiche di normalizzazione applicate nel sync (DL-ARCH-004):**
- Righe `COLL_RIGA_PREC=1` scartate (righe descrizione collaterali EasyJob)
- `qty_disponibile` = `DOC_QTAP` (appartato da EasyJob, per riga)
- `qty_in_produzione` = `SUM(DOC_QTOR - DOC_QTEV)` da `DPRE_PROD` per articolo (LDP aperti)
- `qty_consegnata` = `DOC_QTEV`
- `qty_da_produrre` NON è una colonna — calcolata live: `max(0, qty_ordinata - qty_disponibile - qty_in_produzione)`
- `nickname` su `clienti` mai toccato dal sync (MRS-owned, DL-ARCH-017)

### 4. API sync

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/sync/status` | Stato sync + connessione EasyJob |
| `POST` | `/api/sync/force/{tabella}` | Forza sync immediato |
| `POST` | `/api/sync/force-all` | Forza sync completo (ordine dipendenze) |
| `GET` | `/health` | Health check |

### 5. Decisioni architetturali applicate

| Decisione | DL | Come implementato |
|---|---|---|
| Separazione sync / services / routers | DL-001 | Nessun router scrive DB direttamente |
| Sync senza business logic | DL-003 | handlers.py fa solo normalizzazione tecnica |
| Sync assorbe complessità sorgente | DL-004 | COLL_RIGA_PREC gestito in handlers |
| Computed facts live | DL-007 | qty_da_produrre non è colonna |
| Native facts MRS-owned | DL-008 | commesse/eventi/policy non toccate dal sync |
| Autenticazione ibrida | DL-016 | Tabella utenti creata, JWT Fase 1+ |
| Nickname cliente | DL-017 | Campo nickname su clienti, sync non lo tocca |

---

## Setup e avvio

### Prerequisiti
- Container postgres V0 già attivo (`nssp_postgres` su porta 5432)
- `.venv` con dipendenze installate da `requirements.txt`

### Prima volta

```bash
# 1. Crea database mrs_v1 nel container V0
docker exec -it nssp_postgres psql -U nssp_user -d nssp_db -c "CREATE DATABASE mrs_v1 OWNER nssp_user;"

# 2. Installa dipendenze
cd V1/backend
pip install -r requirements.txt

# 3. Migra schema
alembic upgrade head

# 4. Avvia backend
uvicorn app.main:app --reload
```

### Avvio normale

```bash
cd V1/backend
uvicorn app.main:app --reload
```

Backend disponibile su `http://127.0.0.1:8000`
Docs API: `http://127.0.0.1:8000/docs`

### File env

| File | Contenuto |
|---|---|
| `V1/env/easy.env` | Credenziali EasyJob (EASYJOB_SERVER, _DATABASE, _USER, _PASSWORD, JWT_SECRET) |
| `V1/env/postgres.env` | POSTGRES_HOST=localhost, PORT=5432, DB=mrs_v1 |

---

## Fase successiva — Fase 1

```
services/disponibilita.py   # qty_da_produrre, qty_disponibile_futura
services/scorte.py          # algoritmo scorta_mensile
routers/produzione.py       # F1a (Fabisogno ordini), F1b (Fabisogno scorte)
```

Dipendenza: i dati sync devono essere presenti (tabelle articoli, clienti, ordini, righe_ordine popolate).
