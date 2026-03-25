# SPEC V0.3 — COMPUTED FACTS MECCANICI

**Data apertura:** 2026-03-25
**Stato:** COMPLETED ✅

---

## Obiettivo

Calcolare valori derivati **meccanicamente** a partire dai `fact_*` tables.

Nessuna logica decisionale, nessuna policy aziendale.
Un Computed Fact è puro algebra sui Source Facts: somme, sottrazioni, aggregazioni.

**Regola fondamentale:** i Computed Facts leggono **solo da `fact_*`** — mai da `sync_*`.

---

## Scope v0.3

### Computed Facts implementati — copertura completa DL

**`computed_order_lines`** (per riga ordine):

| Campo | Calcolo |
|---|---|
| `qty_remaining` | `qty_ordered - qty_shipped` |
| `is_fully_shipped` | `qty_remaining <= 0` |
| `is_open_line` | `qty_remaining > 0` |
| `unit_price` | da `fact_order_lines` (campo Easy: `DOC_PZ_NETTO`) |
| `value_remaining` | `qty_remaining × unit_price` |

**`computed_stock_balances`** (per articolo + deposito):

| Campo | Calcolo |
|---|---|
| `stock_balance` | `SUM(qty_in) - SUM(qty_out)` |
| `qty_in_total` / `qty_out_total` | componenti separati |
| `movement_count` | numero movimenti aggregati |

**`computed_production_status`** (per articolo, ordini aperti):

| Campo | Calcolo |
|---|---|
| `qty_in_production` | `SUM(qty_to_produce - qty_produced)` su `is_closed=False` |
| `open_order_count` | numero ordini aperti |

**`computed_article_demand`** (per articolo, visione integrata):

| Campo | Calcolo |
|---|---|
| `total_stock` | `SUM(qty_in - qty_out)` su tutti i depositi |
| `total_open_demand` | `SUM(qty_ordered - qty_shipped)` su righe aperte |
| `net_available_raw` | `total_stock - total_open_demand` |

---

## Struttura directory

```
core/
  computed_facts/
    __init__.py
    models/
      __init__.py
      mixins.py                      # ComputedMetaMixin (built_at, no sync_run_id)
      computed_order_line.py         # ComputedOrderLine
      computed_stock_balance.py      # ComputedStockBalance
      computed_production_status.py  # ComputedProductionStatus
      computed_article_demand.py     # ComputedArticleDemand
    builders/
      __init__.py
      order_line_builder.py
      stock_balance_builder.py
      production_status_builder.py
      article_demand_builder.py
  runner.py                          # Fase 1 (source) + flush + Fase 2 (computed)
```

I nomi delle tabelle DB saranno `computed_order_lines`, `computed_stock_balances`, `computed_production_status`.

---

## Modelli

### `computed_order_lines`

Granularità: una riga per riga ordine.

| Campo               | Tipo           | Note |
|---------------------|----------------|------|
| computed_id         | BigInteger PK  | surrogate key |
| order_source_id     | BigInteger     | FK logica → fact_orders |
| line_number         | BigInteger     | |
| article_source_id   | String(25)     | indexed |
| qty_ordered         | Numeric(13,5)  | copiato da fact_order_lines |
| qty_shipped         | Numeric(13,5)  | copiato da fact_order_lines |
| qty_remaining       | Numeric(13,5)  | `qty_ordered - qty_shipped` |
| is_fully_shipped    | Boolean        | `qty_remaining <= 0` |
| built_at            | DateTime(tz)   | |

**Strategia:** FULL_REBUILD (righe ordine sono mutabili — qty_shipped cambia ad ogni spedizione).

### `computed_stock_balances`

Granularità: una riga per coppia `(article_source_id, depot_code)`.

| Campo               | Tipo           | Note |
|---------------------|----------------|------|
| computed_id         | BigInteger PK  | surrogate key |
| article_source_id   | String(25)     | indexed |
| depot_code          | String(6)      | indexed |
| qty_in_total        | Numeric(18,6)  | `SUM(qty_in)` |
| qty_out_total       | Numeric(18,6)  | `SUM(qty_out)` |
| stock_balance       | Numeric(18,6)  | `qty_in_total - qty_out_total` |
| movement_count      | BigInteger     | numero movimenti aggregati |
| built_at            | DateTime(tz)   | |

**Strategia:** FULL_REBUILD.
Nota: dato che `fact_stock_movements` è APPEND_ONLY, un rebuild di `computed_stock_balances`
è rapido (query di aggregazione SQL, non loop Python record-by-record).

### `computed_production_status`

Granularità: una riga per articolo.

| Campo                | Tipo           | Note |
|----------------------|----------------|------|
| computed_id          | BigInteger PK  | surrogate key |
| article_source_id    | String(25)     | indexed, unique |
| qty_in_production    | Numeric(18,5)  | `SUM(qty_to_produce - qty_produced)` su ordini aperti |
| open_order_count     | BigInteger     | numero ordini di produzione aperti |
| built_at             | DateTime(tz)   | |

**Strategia:** FULL_REBUILD (ordini di produzione si aprono e chiudono).

---

## Builders

### Pattern comune

I builder Computed Facts seguono lo stesso pattern dei Source Facts ma con una differenza:

- Input: query su `fact_*` — possibilmente aggregazioni SQL (no loop per record se non necessario)
- Output: `BuildResult` identico a v0.2

### `StockBalanceBuilder` — aggregazione SQL

Caso speciale: 337k movimenti → **non fare loop Python**.
Usare `GROUP BY` direttamente in SQL e inserire i risultati aggregati.

```python
rows = session.execute(
    select(
        FactStockMovement.article_source_id,
        FactStockMovement.depot_code,
        func.sum(FactStockMovement.qty_in).label("qty_in_total"),
        func.sum(FactStockMovement.qty_out).label("qty_out_total"),
        func.count().label("movement_count"),
    )
    .group_by(FactStockMovement.article_source_id, FactStockMovement.depot_code)
).all()
```

Questo produce un numero di righe pari ai depositi distinti per articolo — gestibile con loop.

---

## Regole di separazione layer

| Layer          | Può leggere da         | Non può leggere da |
|----------------|------------------------|--------------------|
| `sync.*`       | Easy (ODBC)            | —                  |
| `core/facts`   | `sync_*` tables        | `sync.easy.*`, `computed_*` |
| `core/computed_facts` | `fact_*` tables | `sync_*`, `sync.easy.*` |

---

## Runner aggiornato

`core/runner.py` dovrà eseguire i builder in due fasi:

```
Fase 1 — Source Facts   (già esistente)
Fase 2 — Computed Facts (nuovo in v0.3)
```

Fase 2 si avvia solo dopo che Fase 1 è completata senza errori critici.

---

## Mixin riutilizzato

`ComputedMetaMixin` (analogo a `FactMetaMixin`):
- `built_at`: DateTime(timezone=True)
- Nessun `sync_run_id` — i Computed Facts non hanno dipendenza diretta da un sync run

---

## Criteri di successo v0.3

| Criterio | Verifica |
|----------|----------|
| I 3 computed facts calcolati correttamente | numeri verificati su campione dati reali |
| Nessun builder computed legge da `sync_*` | ispezione import |
| `stock_balance` calcolato via SQL aggregation (non loop) | ispezione codice |
| Runner esegue Fase 1 poi Fase 2 in sequenza | test run completo |
| Full rebuild ripetibile e deterministico | eseguire 2 volte, risultato identico |

---

## Considerazioni per v0.4+

- **Computed Facts incrementali**: se le source facts cambiano poco, ricalcolare solo le righe impattate
- **`qty_available`** = `stock_balance - qty_in_production - qty_remaining` — questo è già un aggregato
  di 3 computed facts, probabilmente appartiene a v0.4 o alle Projections
- **Indici** su `computed_stock_balances(article_source_id)` fondamentale per query successive
