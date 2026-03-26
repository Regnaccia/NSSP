# SPEC V0.4 — AGGREGATE & REBUILD MIRATO

**Data apertura:** 2026-03-25
**Stato:** COMPLETED ✅

---

## Obiettivo

Introdurre il concetto di **Aggregate** come unità di rebuild del sistema,
e implementare un rebuild mirato guidato dal `change_set` prodotto dal layer sync.

In v0.1–v0.3 il core esegue sempre un full rebuild di tutti i `fact_*` e `computed_*`.
In v0.4 il core impara a ricalcolare **solo le entità impattate da una sync run**.

---

## Concetto di Aggregate in questo sistema

Un Aggregate NON è una tabella materializzata.
È un'**unità di orchestrazione del rebuild**: un insieme di `fact_*` e `computed_*`
che appartengono logicamente allo stesso dominio e vengono ricostruiti insieme.

Ogni Aggregate ha:
- un **identity** (es. `order_source_id`, `article_source_id`)
- un **metodo `rebuild(session, aggregate_id)`** che ricalcola solo le righe relative a quell'identità

Il full rebuild esistente rimane invariato — è la somma di tutti i rebuild mirati.

---

## Aggregate iniziali

### `OrderAggregate`

**Identity:** `order_source_id`

**Componenti ricostruiti:**
| Tabella | Operazione |
|---|---|
| `fact_orders` | DELETE WHERE source_id=X + reinsert |
| `fact_order_lines` | DELETE WHERE order_source_id=X + reinsert |
| `computed_order_lines` | DELETE WHERE order_source_id=X + ricalcolo |

**Trigger da change_set:**
- `sync_order_headers` cambiato → `OrderAggregate(source_id)`
- `sync_order_lines` cambiato → `OrderAggregate(order_source_id)` (parsed da `source_id = "order_id|line_number"`)

### `ArticleSupplyDemandAggregate`

**Identity:** `article_source_id`

**Componenti ricostruiti:**
| Tabella | Operazione |
|---|---|
| `fact_articles` | DELETE WHERE source_id=X + reinsert |
| `computed_stock_balances` | DELETE WHERE article_source_id=X + riaggregazione |
| `computed_production_status` | DELETE WHERE article_source_id=X + riaggregazione |
| `computed_article_demand` | DELETE WHERE article_source_id=X + riaggregazione |

**Trigger da change_set:**
- `sync_articles` cambiato → `ArticleSupplyDemandAggregate(source_id)`
- `sync_stock_movements` inserito → lookup `article_source_id` dal record → `ArticleSupplyDemandAggregate(article_source_id)`
- `sync_productions` cambiato → lookup `article_source_id` dal record → `ArticleSupplyDemandAggregate(article_source_id)`
- `sync_order_lines` cambiato → lookup `article_source_id` dal record → `ArticleSupplyDemandAggregate(article_source_id)`

---

## Struttura directory

```
core/
  aggregates/
    __init__.py
    base.py                          # BaseAggregate
    order_aggregate.py               # OrderAggregate
    article_supply_demand_aggregate.py # ArticleSupplyDemandAggregate
  orchestrators/
    __init__.py
    dependency_registry.py           # change_set → {AggregateType: {ids}}
    targeted_rebuild.py              # esegue il rebuild mirato
  models/
    __init__.py
    core_run.py                      # log di ogni esecuzione core
  runner.py                          # aggiornato: full rebuild + targeted rebuild
```

---

## Modello `core_run`

Traccia ogni esecuzione del core (full o targeted).

| Campo | Tipo | Note |
|---|---|---|
| id | BigInteger PK | autoincrement |
| started_at | DateTime(tz) | |
| finished_at | DateTime(tz) | nullable |
| status | String(30) | STARTED / COMPLETED / FAILED / COMPLETED_WITH_WARNINGS |
| rebuild_type | String(20) | FULL / TARGETED |
| sync_run_id_from | BigInteger | nullable — prima sync run processata |
| sync_run_id_to | BigInteger | nullable — ultima sync run processata |
| aggregates_rebuilt | Integer | numero di aggregate ricostruiti |
| records_rebuilt | Integer | totale record ricostruiti |
| notes | Text | nullable |

---

## `BaseAggregate`

```python
class BaseAggregate:
    aggregate_type: str  # "order" | "article_supply_demand"

    def rebuild(self, session, aggregate_id: str) -> RebuildResult:
        raise NotImplementedError
```

`RebuildResult`: dataclass con `aggregate_type`, `aggregate_id`, `records_rebuilt`, `errors`.

---

## `DependencyRegistry`

Risolve un `change_set` (lista di `SyncChangeItem`) in un dizionario:

```python
{
    OrderAggregate: {"107511", "107512"},
    ArticleSupplyDemandAggregate: {"ART001", "ART002", "ART003"},
}
```

**Regole di risoluzione per entity_type:**

| entity_type | Aggregate impattato | Come si ricava l'ID |
|---|---|---|
| `sync_order_headers` | OrderAggregate | `source_id` diretto |
| `sync_order_lines` | OrderAggregate | `source_id.split("\|")[0]` (order_source_id) |
| `sync_order_lines` | ArticleSupplyDemandAggregate | lookup `article_source_id` su `fact_order_lines` o `sync_order_lines` |
| `sync_articles` | ArticleSupplyDemandAggregate | `source_id` diretto |
| `sync_stock_movements` | ArticleSupplyDemandAggregate | lookup `article_source_id` su `fact_stock_movements` |
| `sync_productions` | ArticleSupplyDemandAggregate | lookup `article_source_id` su `fact_productions` |

I lookup sono query batch (`IN`) su tabelle già disponibili — una query per entity_type,
indipendentemente da quante righe sono cambiate. Il layer sync rimane isolato: non conosce
concetti del core e `sync_change_item` non viene modificato.

---

## `TargetedRebuildRunner`

```
1. Legge sync_run_id dell'ultimo core_run COMPLETED
2. Legge sync_change_item WHERE sync_run_id > last_core_run
3. Passa il change_set al DependencyRegistry → ottiene aggregates da ricostruire
4. Per ogni aggregate_type, per ogni aggregate_id: chiama aggregate.rebuild()
5. Scrive core_run con risultati
```

**Ordine di esecuzione dei rebuild:**

I due Aggregate sono indipendenti e possono girare in qualsiasi ordine.
Tuttavia `ArticleSupplyDemandAggregate` ricostruisce `computed_article_demand`
che dipende da `fact_order_lines` → se quell'ordine è anche in `OrderAggregate`,
`OrderAggregate` deve girare prima.

Ordine sicuro: `OrderAggregate` → `ArticleSupplyDemandAggregate`.

---

## Regole di rebuild parziale per entità

### Entità con PK semplice (fact_orders, fact_articles)
```python
session.execute(delete(FactOrder).where(FactOrder.source_id == aggregate_id))
# reinsert singolo record da sync_order_headers
```

### Entità con PK relazionale (fact_order_lines, computed_order_lines)
```python
session.execute(delete(FactOrderLine).where(FactOrderLine.order_source_id == aggregate_id))
# reinsert tutte le righe per quell'ordine da sync_order_lines
```

### Entità aggregate (computed_stock_balances, computed_production_status, computed_article_demand)
```python
session.execute(delete(ComputedStockBalance).where(ComputedStockBalance.article_source_id == aggregate_id))
# riaggregazione via GROUP BY filtrata su article_source_id=X
```

---

## Criteri di successo v0.4

| Criterio | Verifica |
|---|---|
| Full rebuild esistente non rotto | output identico a v0.3 |
| Targeted rebuild corretto su campione reale | numeri verificati su articolo/ordine specifico |
| `core_run` loggato correttamente | record presente dopo ogni run |
| DependencyRegistry copre tutti gli entity_type del change_set | ispezione |
| Rebuild mirato più veloce del full rebuild | misura su run con poche modifiche |

---

## Considerazioni per v0.5+

- Con il rebuild mirato in produzione, i Computed Facts incrementali diventano naturali
- `qty_available` (aggregato di aggregati) si calcola agevolmente dentro `ArticleSupplyDemandAggregate`
- Le `Policy` di v0.5 si applicano sugli Aggregate già ricostruiti — il rebuild mirato è prerequisito
- Il `core_run` diventa il punto di partenza per la `Decision Trace` di v0.6
