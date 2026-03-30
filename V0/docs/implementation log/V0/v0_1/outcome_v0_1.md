# OUTCOME V0.1 — SYNC LAYER

**Data chiusura:** 2026-03-25
**Stato:** COMPLETED ✅

---

## Risultati della prima sync reale

Prima esecuzione su dati reali Easy (OMR):

| Entità             | Letti   | Inseriti | Aggiornati | Eliminati | Note |
|--------------------|---------|----------|------------|-----------|------|
| sync_customers     | 566     | 566      | 0          | 0         |      |
| sync_destinations  | 566     | 566      | 0          | 0         | stesso numero di customers — coincide con dati reali |
| sync_articles      | 2.491   | 2.491    | 0          | 0         |      |
| sync_order_headers | 155     | 155      | 0          | 0         |      |
| sync_order_lines   | 666     | 452      | 0          | 0         | 214 righe di continuazione COLL_RIGA_PREC assorbite correttamente |
| sync_stock_movements | 337.038 | 337.038 | 0         | 0         | prima sync full — le successive saranno incrementali per ID |
| sync_productions   | 136     | 136      | 0          | 0         |      |

---

## Validazione test architetturali

### Test 1 — Connettività reale ✅
Connessione a Easy (SQL Server via pyodbc ODBC driver) e a Postgres stabile.
Nessun errore di connessione durante l'esecuzione.

### Test 2 — Stabilità chiavi ✅
Le chiavi sorgenti risultano stabili e sufficienti per tutti i mapping:
- `CLI_COD` per clienti
- `PDES_COD` per destinazioni
- `ART_COD` per articoli
- `ID_TESTATA` per order headers
- `(ID_TESTATA, NUM_PROGR)` per order lines (composite key)
- `ID_MAGREALE` per movimenti di magazzino
- `ID_DETTAGLIO` per produzioni

### Test 3 — Coerenza differenziale ✅
Il change detector MD5 è in posizione e funzionante.
Non ancora testato su run successive con dati modificati — da validare nella prossima run.

### Test 4 — Separazione dei layer ✅
Nessuna logica di dominio introdotta nel sync.
L'unica normalizzazione tecnica presente è COLL_RIGA_PREC (DL-ARCH-004) — giustificata come pre-processing necessario a formare un record coerente.

### Test 5 — Qualità osservabilità ✅
`sync_run` e `sync_change_item` popolati correttamente.
Runner stampa un summary leggibile al termine.

---

## Bug risolti in fase di sviluppo

| Bug | Causa | Fix |
|-----|-------|-----|
| `HY104` ODBC error su `inspect()` | Legacy SQL Server ODBC driver incompatibile con `NUMERIC(38,0)` | Sostituzione con query dirette su `INFORMATION_SCHEMA.COLUMNS` |
| `DetachedInstanceError` su `run.status` | Accesso attributi `SyncRun` dopo chiusura sessione SQLAlchemy | Aggiunto `session.refresh(sync_run)` prima che la sessione si chiuda |
| Pylance `reportAttributeAccessIssue` in `stock_movements.py` | Uso di classe anonima `type("R", (), {...})()` non tipizzabile | Sostituita con `ExtractorResult` dataclass |

---

## Decisioni tecniche confermate

- **Sync incrementale MAG_REALE**: append-only per design → sync per `ID_MAGREALE > max(source_id)`. Prima sync full (337k record), successive parziali.
- **COLL_RIGA_PREC**: righe di continuazione assorbite nel `preprocess_rows()` di `OrderLineExtractor` — 214 righe su 666 eliminate come entità separate, descrizione concatenata alla riga reale precedente.
- **Env separati**: `env/postgres.env` e `env/easy.env` — non committati, presenti `.example` tracciati.
- **Un file per extractor**: struttura mantenuta pulita e estendibile.

---

## Considerazioni emerse per v0.2

### 1. Destinazione effettiva del cliente
Alcuni clienti non hanno una destinazione esplicita in `POT_DESTDIV`.
In questi casi la destinazione di consegna è l'indirizzo presente nella tabella `ANACLI` (cliente).

**Implicazione per v0.2**: il core dovrà costruire un fatto canonico `effective_delivery_address` o simile, che combini `sync_destinations` e `sync_customers` secondo questa regola.
Il sync non deve risolvere questa ambiguità — è logica di business.

### 2. Primo test change detection
La prima sync ha inserito tutto da zero (nessun UPDATED/DELETED possibile).
In v0.2 sarà utile eseguire una seconda sync per validare che:
- record non modificati → nessun change
- record modificati → UPDATED corretto
- record rimossi → DELETED corretto

### 3. Scope Source Facts suggerito per v0.2
Basandosi sui dati sincronizzati, i Source Facts prioritari sono:
- `OrderFact` — da `sync_order_headers`
- `OrderLineFact` — da `sync_order_lines`
- `ArticleFact` — da `sync_articles`
- `CustomerFact` — da `sync_customers` (con risoluzione destinazione)

`StockMovementFact` e `ProductionFact` possono essere aggiunti in v0.2 o rinviati a v0.3 a seconda della complessità.

---

## Criteri di successo v0.1 — verifica

| Criterio | Esito |
|----------|-------|
| Legge dati reali dal source system | ✅ |
| Dati persistiti localmente in modo coerente | ✅ |
| Ogni run è tracciata | ✅ |
| Cambiamenti identificati in modo consistente | ✅ (struttura pronta, da validare su run successive) |
| Output sufficiente per alimentare il core | ✅ |
| Nessuna logica di dominio impropria nel sync | ✅ |

---

## Prossimo step

**v0.2 — Source Facts**

Costruire il primo layer `core` indipendente da Easy, a partire dai dati in `sync_*`.
