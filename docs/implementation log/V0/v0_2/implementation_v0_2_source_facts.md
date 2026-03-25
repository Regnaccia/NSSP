# IMPLEMENTATION V0.2 — SOURCE FACTS

## Obiettivo

La milestone **v0.2** ha lo scopo di costruire il primo layer `core` reale del sistema: i **Source Facts**.

I Source Facts sono la prima rappresentazione interna canonica del dominio MRS, indipendente dalla struttura di EasyJob.

Il layer `core` non conosce Easy. Conosce solo le tabelle `sync_*`.

---

## Posizione nella catena architetturale

```
SYNC → [Source Facts] → Computed Facts → Canonical States → Projections
```

I Source Facts sono il confine tra acquisizione tecnica e dominio interno.

- a sinistra: dati grezzi normalizzati da Easy (tabelle `sync_*`)
- a destra: fatti canonici del dominio, deterministici e ricostruibili

---

## Principi fondamentali (da DL-ARCH-006, DL-ARCH-007)

### 1. Rigenerabilità completa
I Source Facts devono poter essere completamente ricostruiti a partire dalle sole tabelle `sync_*`.
Un full rebuild deve produrre lo stesso risultato a parità di dati in sync.

### 2. Determinismo
A parità di dati sync, il risultato deve essere identico.
Nessuno stato implicito, nessuna dipendenza da esecuzioni precedenti.

### 3. Indipendenza da Easy
Il layer `core` non importa nulla da `sync.easy`, non tocca tabelle Easy,
non conosce nomi di colonne Easy.
Legge esclusivamente da tabelle `sync_*`.

### 4. No logica derivata
I Source Facts non contengono ancora computed facts né stati operativi.
Non calcolano `qty_remaining`, non assegnano stati come `OPEN` o `FULFILLED`.
Rappresentano solo ciò che il sistema **sa** dalla sorgente.

### 5. Normalizzazione canonica
I Source Facts applicano la normalizzazione semantica che il sync non può fare:
- codici uppercase
- trim esteso
- risoluzione di ambiguità tecniche note (es. destinazione effettiva)

---

## Entità da costruire in v0.2

### 1. `FactArticle`
**Sorgente:** `sync_articles`

Rappresenta un articolo del catalogo OMR nel dominio interno.

Campi canonici minimi:
- `fact_id` (PK interno, non legato a Easy)
- `source_id` (riferimento a `sync_articles.source_id`)
- `code` (normalizzato: uppercase, trim)
- `description`
- `unit_of_measure`
- metadati fact: `built_at`, `sync_run_id`

Normalizzazioni:
- `code` → uppercase, strip
- `description` → strip

---

### 2. `FactCustomer`
**Sorgente:** `sync_customers`

Rappresenta un cliente nel dominio interno.

Campi canonici minimi:
- `fact_id`
- `source_id`
- `code` (normalizzato)
- `name`
- `address` (indirizzo del cliente — usato come destinazione effettiva se non esiste una destinazione separata)
- `city`, `zip`, `country`

Normalizzazioni:
- `code` → uppercase, strip
- `name`, `address` → strip

---

### 3. `FactDestination`
**Sorgente:** `sync_destinations` + `sync_customers` (risoluzione destinazione effettiva)

Rappresenta una destinazione di consegna nel dominio interno.

**Regola di dominio (emersa da v0.1):**
Se un cliente non ha destinazioni in `sync_destinations`, la sua destinazione effettiva
è l'indirizzo presente in `sync_customers`.
Questa regola appartiene al core, non al sync.

Campi canonici minimi:
- `fact_id`
- `source_id` (può essere NULL se derivata dal cliente)
- `customer_source_id`
- `code` (normalizzato)
- `address`, `city`, `zip`, `country`
- `is_derived_from_customer` (bool — True se costruita da sync_customers)

Normalizzazioni:
- `code` → uppercase, strip
- campi indirizzo → strip

---

### 4. `FactOrder`
**Sorgente:** `sync_order_headers`

Rappresenta un ordine cliente nel dominio interno.

Campi canonici minimi:
- `fact_id`
- `source_id`
- `order_number` (normalizzato)
- `customer_source_id`
- `destination_source_id`
- `document_date`
- `delivery_date`
- metadati fact

Normalizzazioni:
- `order_number` → strip

---

### 5. `FactOrderLine`
**Sorgente:** `sync_order_lines`

Rappresenta una riga ordine nel dominio interno.

Campi canonici minimi:
- `fact_id`
- `order_source_id`
- `line_number`
- `article_source_id`
- `article_description` (già preprocessata da sync — COLL_RIGA_PREC già assorbito)
- `qty_ordered`
- `qty_shipped`
- `qty_packed`
- `customer_line_ref`
- metadati fact

Nota: `qty_remaining`, `is_open`, ecc. non appartengono ai Source Facts — sono Computed Facts (v0.3).

---

### 6. `FactStockMovement`
**Sorgente:** `sync_stock_movements`

Rappresenta un singolo movimento di magazzino nel dominio interno.

Campi canonici minimi:
- `fact_id`
- `source_id`
- `article_source_id`
- `depot_code`
- `qty_in`
- `qty_out`
- `movement_type`
- `document_type`
- `document_number`
- `registered_at`
- metadati fact

Nota: lo stock aggregato per articolo/deposito è un Computed Fact (v0.3),
non un Source Fact.

---

### 7. `FactProduction`
**Sorgente:** `sync_productions`

Rappresenta un ordine di produzione nel dominio interno.

Campi canonici minimi:
- `fact_id`
- `source_id`
- `production_order` (normalizzato)
- `article_source_id`
- `customer_source_id`
- `qty_total`
- `qty_to_produce`
- `qty_produced`
- `qty_in_progress`
- `is_closed`
- `order_number`
- `order_line`
- `planned_date`
- metadati fact

---

## Struttura del layer core

```
V0/
  core/
    models/
      fact_article.py
      fact_customer.py
      fact_destination.py
      fact_order.py
      fact_order_line.py
      fact_stock_movement.py
      fact_production.py
      __init__.py
      mixins.py
    builders/
      article_builder.py
      customer_builder.py
      destination_builder.py
      order_builder.py
      order_line_builder.py
      stock_movement_builder.py
      production_builder.py
      __init__.py
      base.py
    runner.py
```

I **builder** sono i componenti che leggono da `sync_*` e scrivono nei `fact_*`.
Ogni builder è responsabile di una sola entità.

---

## Pattern del builder

Ogni builder espone almeno:

```python
class ArticleBuilder(BaseBuilder):
    def build(self, session) -> BuildResult:
        ...
```

### Strategie di rebuild

In v0.2 esistono due strategie, scelte in base alla natura della sorgente:

#### FULL_REBUILD (default)
Per entità la cui sorgente è mutabile (record possono cambiare o essere eliminati).

Comportamento:
1. Elimina tutti i `fact_*` esistenti per l'entità
2. Legge tutti i record dalla tabella `sync_*`
3. Applica normalizzazione e mapping
4. Inserisce i nuovi fact

Entità: Article, Customer, Destination, Order, OrderLine, Production.

#### APPEND_ONLY
Per entità la cui sorgente è append-only (i record non vengono mai modificati o eliminati).

Comportamento:
1. Legge `max(source_id)` già presente in `fact_*`
2. Legge solo i record `sync_*` con `source_id > max`
3. Applica normalizzazione e mapping
4. Inserisce i nuovi fact (nessun delete)

Entità: **StockMovement** — MAG_REALE è append-only per design, i movimenti non vengono mai modificati.

Questa strategia è deterministica e ricostruibile: un full rebuild da zero (delete-all + riprocessa tutto) produce lo stesso risultato, ma nella pratica quotidiana processa solo i nuovi record.

Il rebuild incrementale guidato dal change set (per le entità FULL_REBUILD) appartiene a v0.4.

---

## Metadati dei fact

Ogni tabella `fact_*` deve contenere:

```python
class FactMetaMixin:
    built_at: datetime       # quando il fact è stato costruito
    sync_run_id: int | None  # run sync da cui è stato derivato (opzionale in v0.2)
```

Non serve `row_hash` nei fact — il change detection appartiene al sync layer.

---

## Runner core v0.2

Analogamente al sync runner, il core avrà un runner:

```python
# python -m core.runner
def run_full_rebuild():
    """Esegue full rebuild di tutti i Source Facts."""
    ...
```

Il runner deve:
- eseguire i builder nell'ordine corretto (rispettare dipendenze)
- tracciare l'esito (record costruiti per entità)
- essere invocabile manualmente

Ordine consigliato (rispetta dipendenze di chiave):
1. ArticleBuilder
2. CustomerBuilder
3. DestinationBuilder (dipende da CustomerBuilder)
4. OrderBuilder
5. OrderLineBuilder
6. StockMovementBuilder
7. ProductionBuilder

---

## Gestione delle chiavi

### source_id vs fact_id

Ogni `fact_*` ha due identificativi:
- `source_id`: chiave proveniente da Easy, presente anche in `sync_*`
- `fact_id`: PK interna del dominio MRS (surrogate key)

Il `fact_id` è utile per:
- disaccoppiare il dominio da Easy anche nelle relazioni
- permettere future fusioni o riassegnazioni senza rompere le FK interne

In v0.2 il `fact_id` può essere implementato come semplice `BIGSERIAL`.

### Riferimenti tra fact

I `fact_*` si referenziano tramite `source_id` (non `fact_id`) in v0.2,
per semplicità e coerenza con il rebuild full.
Il passaggio a FK su `fact_id` può avvenire in versioni successive.

---

## Separazione layer — vincoli espliciti

| Regola | Descrizione |
|--------|-------------|
| Il core non importa da `sync.easy` | Nessun import da `sync.easy.*` nel layer `core` |
| Il core non tocca tabelle Easy | Nessuna query su SQL Server dal core |
| Il core legge solo da `sync_*` | Solo lettura da tabelle `sync_*` del DB interno |
| I Computed Facts non leggono da `sync_*` | Questa regola vale già in v0.3 — va rispettata da subito |
| I builder non applicano logica operativa | Nessuna policy, nessuno stato derivato |

---

## Normalizzazione canonica — linee guida

Le seguenti normalizzazioni sono applicate nei builder, non nel sync:

| Campo | Regola |
|-------|--------|
| Codici articolo | uppercase + strip |
| Codici cliente | uppercase + strip |
| Codici destinazione | uppercase + strip |
| Numeri ordine | strip |
| Campi stringa generici | strip se non già fatto in sync |
| Destinazione effettiva | se assente in `sync_destinations`, derivata da `sync_customers` |

---

## Output attesi di v0.2

1. **Tabelle `fact_*`** popolate e interrogabili
2. **Full rebuild funzionante** — a partire da sync, ricostruisce tutto il core
3. **Separazione netta** — nessun accesso a Easy o a tabelle Easy dal core
4. **Normalizzazione canonica applicata** — codici puliti e uniformi
5. **Runner core** con summary (entità costruite, record per entità)

---

## Test architetturali attesi

### Test 1 — Rigenerabilità
Svuotare le tabelle `fact_*` e rieseguire il runner: il risultato deve essere identico.

### Test 2 — Indipendenza da sync
Dopo un full rebuild, le tabelle `fact_*` devono essere usabili anche senza rieseguire il sync.

### Test 3 — Normalizzazione
Verificare che codici articolo e cliente siano uniformi (case, trim) nei `fact_*`.

### Test 4 — Destinazione effettiva
Verificare che i clienti senza destinazione in `sync_destinations` abbiano
un `FactDestination` derivato da `sync_customers`.

### Test 5 — Separazione layer
Verificare che nessun builder importi da `sync.easy.*` o acceda a tabelle Easy.

---

## Criteri di successo della milestone

La milestone v0.2 è da considerarsi riuscita se:

1. tutti i Source Facts sono costruiti correttamente da `sync_*`
2. il full rebuild è funzionante e deterministico
3. il core è indipendente da Easy
4. la normalizzazione canonica è applicata
5. la regola di destinazione effettiva è implementata nel core
6. nessuna logica di Computed Fact è entrata nei Source Facts

---

## Rischi principali

| Rischio | Mitigazione |
|---------|-------------|
| Tentazione di calcolare `qty_remaining` già nel Source Fact | Vietato — appartiene a v0.3 |
| Importare da `sync.easy` per "comodità" | Vietato — il core non conosce Easy |
| Mancata risoluzione destinazione effettiva | Test dedicato (Test 4) |
| Codici non uniformi tra fact_articles e fact_order_lines | Normalizzazione su `article_source_id` in tutti i builder |

---

## Decisioni rinviate

- rebuild incrementale guidato da change set → v0.4
- Computed Facts (qty_remaining, stock aggregato, ecc.) → v0.3
- Canonical Operational States → v0.5/v0.6
- Dipendenze esplicite tra fact → v0.4

---

## Prossimo step dopo v0.2

**v0.3 — Computed Facts meccanici**

A partire dai Source Facts, calcolo deterministico di:
- `qty_remaining` per riga ordine
- `stock_available` per articolo/deposito
- `qty_in_production` per articolo
