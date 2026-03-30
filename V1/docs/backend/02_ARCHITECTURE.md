# MRS Backend — Architettura

## Indice
1. [Stack tecnologico](#1-stack-tecnologico)
2. [Layer architetturali](#2-layer-architetturali)
3. [Schema database](#3-schema-database)
4. [Proprietà delle tabelle](#4-proprietà-delle-tabelle)
5. [Flusso dati — percorso completo](#5-flusso-dati--percorso-completo)
6. [Sync EasyJob](#6-sync-easyjob)
7. [Scheduler APScheduler](#7-scheduler-apscheduler)
8. [Principi di design](#8-principi-di-design)

---

## 1. Stack tecnologico

| Componente | Tecnologia | Versione |
|---|---|---|
| Framework API | FastAPI | 0.115.12 |
| Server ASGI | Uvicorn | 0.34.0 |
| ORM | SQLAlchemy | 2.0.40 |
| Migrazioni | Alembic | 1.15.2 |
| Database MRS | PostgreSQL | 15 |
| Sync EasyJob | pyodbc + SQLAlchemy | 5.3.0 |
| Scheduler | APScheduler | 3.11.0 |
| Autenticazione | PyJWT + bcrypt | 2.10.1 / 4.2.1 |
| Serializzazione | Pydantic | 2.11.1 |
| Export Excel | openpyxl | 3.1.5 |

---

## 2. Layer architetturali

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React)                  │
└─────────────────────────┬───────────────────────────┘
                          │ HTTP / JSON
┌─────────────────────────▼───────────────────────────┐
│               ROUTERS  (app/routers/)                │
│  Validazione input (Pydantic) · Guard JWT · HTTP 4xx │
│  Non contengono business logic — delegano ai service │
└─────────────────────────┬───────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────┐
│              SERVICES  (app/services/)               │
│  Tutta la business logic · State machine commesse    │
│  Calcoli live · Policy clienti · Priorità coda       │
└─────────────────────────┬───────────────────────────┘
                          │ SQLAlchemy ORM / raw SQL
┌─────────────────────────▼───────────────────────────┐
│              DATABASE  (PostgreSQL)                  │
│  12 tabelle · 5 sync-owned · 7 MRS-owned             │
└─────────────────────────────────────────────────────┘

                          ▲
┌─────────────────────────┴───────────────────────────┐
│              SYNC LAYER  (app/sync/)                 │
│  EasyJob (SQL Server) → PostgreSQL                   │
│  APScheduler: articoli/clienti ogni 60min            │
│               ordini/righe ogni 5min                 │
│               scorte ricalcolo 1° del mese ore 2:00  │
└─────────────────────────────────────────────────────┘
```

---

## 3. Schema database

### 3.1 Tabelle sync-owned (scritte solo da EasyJob → MRS)

#### `articoli`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | UUID generato da MRS al primo sync |
| `codice` | `VARCHAR(50)` UNIQUE | Codice articolo EasyJob (originale) |
| `codice_upper` | `VARCHAR(50)` UNIQUE | Versione uppercase per confronto case-insensitive |
| `descrizione` | `TEXT` | |
| `categoria` | `VARCHAR(50)` | |
| `capienza` | `INTEGER` | Pezzi per ciclo di produzione |
| `scorta_mensile` | `INTEGER` DEFAULT 0 | Calcolato da `services/scorte.py` |
| `mesi_scorta` | `INTEGER` DEFAULT 3 | **MRS-owned** — configurabile da operatore |
| `tipo_produzione` | `VARCHAR(20)` DEFAULT `PEZZO` | `PEZZO` \| `BARRA` \| `FASCI` |
| `lunghezza_barra` | `INTEGER` | Solo per `tipo_produzione=BARRA` |
| `multipli_taglio` | `INTEGER` | Multipli ammessi per il taglio |
| `prd_pari` | `BOOLEAN` DEFAULT false | Produzione solo a quantità pari |
| `storico_sufficiente` | `BOOLEAN` DEFAULT false | Aggiornato da `ricalcola_scorte_tutti` |
| `scorta_calcolata_at` | `TIMESTAMPTZ` | Timestamp ultimo calcolo scorta |
| `synced_at` | `TIMESTAMPTZ` NOT NULL | Ultimo sync da EasyJob |

#### `clienti`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `codice_easyjob` | `VARCHAR(50)` UNIQUE | |
| `ragione_sociale` | `TEXT` NOT NULL | |
| `nickname` | `VARCHAR(50)` | **MRS-owned** — nome breve operativo (DL-ARCH-017) |
| `email` | `VARCHAR(255)` | |
| `synced_at` | `TIMESTAMPTZ` NOT NULL | |

#### `ordini`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `numero_ordine` | `VARCHAR(50)` UNIQUE | |
| `cliente_id` | FK → `clienti` | |
| `data_ordine` | `DATE` NOT NULL | |
| `data_consegna` | `DATE` | Nullable — alcuni ordini non hanno scadenza |
| `stato` | `VARCHAR(30)` DEFAULT `aperto` | `aperto` \| `chiuso` |
| `note` | `TEXT` | |
| `synced_at` | `TIMESTAMPTZ` NOT NULL | |

#### `righe_ordine`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `ordine_id` | FK → `ordini` | Indicizzato |
| `articolo_id` | FK → `articoli` | Indicizzato |
| `riga_ej_id` | `VARCHAR(50)` NOT NULL | ID riga in EasyJob |
| `qty_ordinata` | `INTEGER` NOT NULL | |
| `qty_disponibile` | `INTEGER` DEFAULT 0 | Da MAG_REALE EasyJob (giacenza appartata) |
| `qty_in_produzione` | `INTEGER` DEFAULT 0 | Commesse attive in EasyJob |
| `qty_consegnata` | `INTEGER` DEFAULT 0 | Quantità già consegnata al cliente |
| `stato` | `VARCHAR(30)` DEFAULT `aperto` | `aperto` \| `spedito` \| `chiuso` |
| `synced_at` | `TIMESTAMPTZ` NOT NULL | |

> **qty_da_produrre** (calcolata live): `max(0, qty_ordinata - qty_disponibile - qty_in_produzione)`

#### `sync_log`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `tabella` | `VARCHAR(50)` UNIQUE | |
| `last_sync_at` | `TIMESTAMPTZ` | |
| `last_error` | `TEXT` | Null se ultimo sync OK |
| `records_updated` | `INTEGER` | |
| `sync_duration_ms` | `INTEGER` | |

---

### 3.2 Tabelle MRS-owned (create e gestite da MRS)

#### `commesse`
Lavoro di produzione associato a una riga ordine (o a una scorta).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `riga_ordine_id` | FK → `righe_ordine` NULLABLE | NULL per commesse pure scorta |
| `articolo_id` | FK → `articoli` | |
| `macchina_id` | FK → `macchine` NULLABLE | Assegnata dallo schedulatore |
| `ldp_easyjob` | `VARCHAR(50)` | LDP (Lavorazione Di Produzione) EasyJob (futuro) |
| `qty_cliente` | `INTEGER` DEFAULT 0 | Quantità da produrre per soddisfare l'ordine |
| `qty_scorta` | `INTEGER` DEFAULT 0 | Quantità aggiuntiva da produrre per scorta |
| `qty_prodotta_cliente` | `INTEGER` DEFAULT 0 | Aggiornata dall'operatore in reparto |
| `qty_prodotta_scorta` | `INTEGER` DEFAULT 0 | Aggiornata dall'operatore in reparto |
| `qty_ciclo_corrente` | `INTEGER` NULLABLE | Quantità per questo ciclo macchina |
| `stato` | `VARCHAR(30)` DEFAULT `in_coda` | Vedi state machine sotto |
| `posizione_coda` | `INTEGER` NULLABLE | Posizione in coda (1=prima) |
| `priorita_suggerita` | `INTEGER` NULLABLE | 1=urgente, 2=normale |
| `sospesa_at` | `TIMESTAMPTZ` | Quando è stata sospesa |
| `sospesa_nota` | `TEXT` | Motivo sospensione |
| `completata_at` | `TIMESTAMPTZ` | Quando è stata completata |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |
| `created_by` | `VARCHAR(50)` | Username che ha creato la commessa |

**State machine commesse** (DL-ARCH-019):
```
in_coda ──avvia──→ in_produzione ──sospendi──→ sospesa
                        │                          │
                     completa                    riprendi
                        │                          │
                    completata              in_produzione
```

| Transizione | Stato da | Stato a | Chi la esegue |
|---|---|---|---|
| `avvia` | `in_coda` | `in_produzione` | Reparto (kiosk) |
| `sospendi` | `in_produzione` | `sospesa` | Reparto (kiosk) |
| `riprendi` | `sospesa` | `in_produzione` | Reparto (kiosk) |
| `completa` | `in_produzione` | `completata` | Reparto (kiosk) |

#### `macchine`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `codice` | `VARCHAR(30)` UNIQUE | Es. `CNC-01` |
| `nome` | `TEXT` | |
| `operazioni_eseguibili` | `ARRAY(TEXT)` | Es. `["tornitura", "fresatura"]` |
| `stato` | `VARCHAR(30)` DEFAULT `disponibile` | `disponibile` \| `in_lavorazione` \| `in_setup` \| `in_manutenzione` |
| `setup_corrente` | `TEXT` | Articolo attualmente in setup |
| `attiva` | `BOOLEAN` DEFAULT true | Macchine disattivate non compaiono nel kiosk |

#### `policy_clienti`
Regole di spedizione per cliente (DL-ARCH-016).

| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `cliente_id` | FK → `clienti` UNIQUE | Una sola policy per cliente |
| `tipo_policy` | `VARCHAR(30)` | `GIORNO_FISSO` \| `DATA_TASSATIVA` \| `SOGLIA_VALORE` \| `DEFAULT` |
| `giorno_fisso` | `INTEGER` | Giorno settimana (1=Lun, 7=Dom) — solo per `GIORNO_FISSO` |
| `soglia_valore` | `NUMERIC(10,2)` | Soglia qty per spedire — solo per `SOGLIA_VALORE` |
| `corriere_preferito` | `VARCHAR(100)` | Es. `BRT`, `GLS`, `DHL` |
| `note_spedizione` | `TEXT` | |
| `policy_json` | `JSONB` | Estensioni future senza schema change |
| `configurata_da` | `VARCHAR(50)` | Username |
| `updated_at` | `TIMESTAMPTZ` NOT NULL | |

**Comportamento per tipo policy:**

| Tipo | Data spedizione suggerita | Logica |
|---|---|---|
| `DATA_TASSATIVA` | = `data_consegna` dell'ordine | Spedire esattamente alla data consegna |
| `GIORNO_FISSO` | Prossimo giorno X della settimana (non oltre `data_consegna`) | Es. sempre il mercoledì |
| `SOGLIA_VALORE` | `None` | Spedire quando la somma degli ordini pronti supera la soglia |
| `DEFAULT` | `None` | Operatore decide caso per caso |

#### `eventi`
Comunicazioni inter-reparto tracciate nel sistema.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `tipo` | `VARCHAR(50)` | Vedi tipi sotto |
| `mittente` | `VARCHAR(30)` | `logistica` \| `magazzino` \| `produzione` \| `sistema` |
| `destinatario` | `VARCHAR(30)` | |
| `ref_ordine_id` | FK → `ordini` NULLABLE | |
| `ref_commessa_id` | FK → `commesse` NULLABLE | |
| `ref_articolo_id` | FK → `articoli` NULLABLE | |
| `stato` | `VARCHAR(20)` DEFAULT `aperto` | `aperto` \| `in_lavorazione` \| `risolto` \| `rifiutato` |
| `nota` | `TEXT` | |
| `feedback_stato` | `VARCHAR(30)` | `accettata` \| `non_fattibile` |
| `feedback_data_prevista` | `DATE` | Data realistica proposta dalla produzione |
| `feedback_nota` | `TEXT` | |
| `corriere_override` | `VARCHAR(100)` | Corriere suggerito dalla produzione per urgenza parziale |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` NOT NULL | |
| `resolved_at` | `TIMESTAMPTZ` | |

**Tipi evento:**

| Tipo | Mittente | Destinatario | Scopo |
|---|---|---|---|
| `urgenza_formale` | `logistica` | `produzione` | Logistica richiede accelerazione su un ordine |
| `ordine_pronto` | `magazzino` | `logistica` | Magazzino ha approntato tutto l'ordine |

> Quando si crea o risolve una `urgenza_formale`, la coda di lavorazione viene **ricalcolata automaticamente**.

#### `consegne_magazzino`
Registrazione fisica di pezzi prodotti messi in magazzino.

| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `commessa_id` | FK → `commesse` | Una sola consegna per commessa (vincolo applicativo) |
| `articolo_id` | FK → `articoli` | |
| `qty_consegnata` | `INTEGER` | Totale consegnato |
| `quota` | `VARCHAR(10)` | `cliente` \| `scorta` \| `mista` |
| `qty_cliente` | `INTEGER` DEFAULT 0 | Pezzi destinati all'ordine cliente |
| `qty_scorta` | `INTEGER` DEFAULT 0 | Pezzi destinati a scorta |
| `stato` | `VARCHAR(20)` DEFAULT `in_attesa` | `in_attesa` \| `registrata_ej` |
| `registrata_ej_at` | `TIMESTAMPTZ` | Quando registrata in EasyJob (futuro) |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |

#### `spedizioni`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `ordine_id` | FK → `ordini` | Indicizzato |
| `tipo` | `VARCHAR(20)` | `totale` \| `parziale` |
| `stato` | `VARCHAR(30)` DEFAULT `in_preparazione` | `in_preparazione` \| `spedita` \| `annullata` |
| `corriere` | `VARCHAR(100)` | |
| `data_pianificata` | `DATE` | Data prevista ritiro corriere |
| `data_spedizione` | `DATE` | Data effettiva spedizione (impostata da `segna_spedita`) |
| `colli` | `INTEGER` | |
| `peso_kg` | `NUMERIC(8,2)` | |
| `evento_id` | FK → `eventi` NULLABLE | Collegamento all'evento `ordine_pronto` |
| `note` | `TEXT` | |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |

#### `utenti`
| Colonna | Tipo | Note |
|---|---|---|
| `id` | `VARCHAR(36)` PK | |
| `username` | `VARCHAR(50)` UNIQUE | |
| `password_hash` | `VARCHAR(255)` | bcrypt hash |
| `ruolo` | `VARCHAR(20)` | `admin` \| `produzione` \| `logistica` \| `magazzino` |
| `attivo` | `BOOLEAN` DEFAULT true | |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |

---

## 4. Proprietà delle tabelle

> Regola fondamentale: **nessun router scrive direttamente in nessuna tabella**. Tutti i write passano dai services.

| Tabella | Owner | Chi scrive | Chi legge |
|---|---|---|---|
| `articoli` | EasyJob | `sync/handlers.py` | Tutti |
| `clienti` | EasyJob | `sync/handlers.py` | Tutti; `nickname` solo da `services/logistica` |
| `ordini` | EasyJob | `sync/handlers.py` | Tutti |
| `righe_ordine` | EasyJob | `sync/handlers.py` | Tutti |
| `sync_log` | EasyJob | `sync/handlers.py` | `routers/sync` |
| `commesse` | MRS | `services/commesse.py`, `routers/produzione` (raw INSERT) | Tutti |
| `macchine` | MRS | Admin manualmente (no API di write in MVP) | Reparto, Produzione |
| `policy_clienti` | MRS | `services/logistica.py` | Logistica |
| `eventi` | MRS | `services/eventi.py`, `services/magazzino.py` | Tutti |
| `consegne_magazzino` | MRS | `services/magazzino.py` | Magazzino, Logistica |
| `spedizioni` | MRS | `services/logistica.py` | Logistica |
| `utenti` | MRS | `services/auth.py` | Auth |

---

## 5. Flusso dati — percorso completo

### Flusso ordine cliente (end-to-end)

```
EasyJob (registra ordine)
    │
    ▼ sync ogni 5 min
ordini + righe_ordine (PostgreSQL)
    │
    ▼ GET /api/produzione/f1a
Ufficio Produzione vede le righe da lanciare
    │
    ▼ POST /api/produzione/genera-commesse
commesse create (stato: in_coda)
    │
    ▼ Algoritmo priorità (urgenza → data → FIFO)
posizione_coda + priorita_suggerita aggiornati
    │
    ▼ GET /api/reparto/macchine/{id}/coda  (kiosk reparto)
Operatore reparto vede la sua coda
    │
    ▼ POST /api/reparto/commesse/{id}/avvia
stato: in_produzione
    │
    ▼ POST /api/reparto/commesse/{id}/aggiorna-qty (durante lavorazione)
    │
    ▼ POST /api/reparto/commesse/{id}/completa
stato: completata, completata_at = now
    │
    ▼ GET /api/magazzino/da-approntare  (kiosk magazzino)
Operatore magazzino vede i pezzi da mettere a posto
    │
    ▼ POST /api/magazzino/consegne
consegne_magazzino registrata
    │
    ▼ POST /api/magazzino/ordini/{id}/pronto  (idempotente)
evento ordine_pronto (mittente: magazzino → logistica)
    │
    ▼ GET /api/logistica/da-spedire
Logistica vede ordini pronti + data suggerita da policy
    │
    ▼ POST /api/logistica/spedizioni
spedizione creata (stato: in_preparazione)
    │
    ▼ POST /api/logistica/spedizioni/{id}/spedita
stato: spedita, data_spedizione = today
```

### Flusso urgenza

```
Logistica vede ritardo su un ordine
    │
    ▼ POST /api/eventi/urgenza
evento urgenza_formale (logistica → produzione)
+ ricalcolo automatico coda (commessa sale in priorità)
    │
    ▼ POST /api/eventi/{id}/feedback  (produzione risponde)
feedback_stato: accettata | non_fattibile
evento stato → in_lavorazione
    │
    ▼ POST /api/eventi/{id}/risolvi  (logistica chiude)
evento stato → risolto
+ ricalcolo automatico coda (commessa torna in posizione normale)
```

---

## 6. Sync EasyJob

**File:** `app/sync/handlers.py`

Il sync legge da SQL Server EasyJob via ODBC e aggiorna le tabelle sync-owned in PostgreSQL. Strategia: **upsert** (INSERT o UPDATE in base a chiave EasyJob).

| Handler | Tabelle scritte | Fonte EasyJob | Frequenza |
|---|---|---|---|
| `sync_articoli` | `articoli` | `ANAART` | 60 min |
| `sync_clienti` | `clienti` | `ANACLI` | 60 min |
| `sync_ordini_e_righe` | `ordini`, `righe_ordine` | `V_TORDCLI` | 5 min |

> Se EasyJob non è raggiungibile, il sync loga l'errore e scrive in `sync_log.last_error`. Il backend continua a funzionare con i dati dell'ultimo sync riuscito.

**Force sync manuale:** `POST /api/sync/force/{tabella}` (solo admin)

---

## 7. Scheduler APScheduler

**File:** `app/sync/scheduler.py`

Avviato nel lifespan FastAPI (`main.py`). In background, thread non-daemon.

| Job ID | Trigger | Funzione |
|---|---|---|
| `sync_articoli` | Ogni 60 min | `sync_articoli(session)` |
| `sync_clienti` | Ogni 60 min | `sync_clienti(session)` |
| `sync_ordini_e_righe` | Ogni 5 min | `sync_ordini_e_righe(session)` |
| `ricalcolo_scorte_mensile` | 1° del mese ore 2:00 | `ricalcola_scorte_tutti(session)` |

---

## 8. Principi di design

### 8.1 EasyJob è source of truth
In caso di conflitto tra dato locale MRS e dato EasyJob, **EasyJob vince**. Il sync sovrascrive i dati sync-owned a ogni ciclo.

### 8.2 MRS è read-only verso EasyJob
MRS non scrive mai su EasyJob in MVP. Il flusso inverso (commesse → EasyJob LDP) è previsto ma non implementato: si usa l'export Excel per ora.

### 8.3 Sistema suggerisce, operatore decide
Nessun cambio automatico senza conferma umana. La coda viene ricalcolata e **suggerita** — l'operatore la può sovrascrivere con drag&drop.

### 8.4 Terminali kiosk senza autenticazione
I router `/api/reparto` e `/api/magazzino` non hanno JWT guard: sono usati da terminali fisici fissi in posizioni note dell'azienda (DL-ARCH-016).

### 8.5 Idempotenza dove necessario
- `POST /api/magazzino/ordini/{id}/pronto` — se l'evento ordine_pronto aperto esiste già, lo ritorna senza crearne uno nuovo
- `PUT /api/logistica/clienti/{id}/policy` — crea se non esiste, aggiorna se esiste

### 8.6 Quantità calcolate live, non persiste
`qty_da_produrre` e `qty_disponibile_futura` vengono calcolate al momento della richiesta HTTP, non persistite in DB. Questo evita disallineamenti con i dati sync.
