# OUTCOME V0.5 — POLICY-DRIVEN COMPUTED FACTS

**Data chiusura:** 2026-03-26
**Stato:** COMPLETED ✅

---

## Risultati del test finale

Test eseguito su sync run reale con modifiche effettive:

| Step | Risultato |
|---|---|
| Full rebuild (baseline con policy) | 10.144 record, 6.5s, COMPLETED_WITH_WARNINGS |
| Sync run successiva | 22 ins, 20 del su più entity_type |
| Targeted rebuild con policy | 23 aggregate + 18 articoli policy, 50 record, 0.4s, COMPLETED |

### Dettaglio targeted rebuild

**Aggregates ricostruiti:** 5 ordini + 18 articoli
**Policy applicata:** 18 articoli, 24 righe aggiornate con `qty_coverable_now` / `coverable_now`

---

## Struttura implementata

```
core/
  policies/
    __init__.py
    base.py              # BasePolicy + PolicyResult
    fifo_allocation.py   # FifoAllocationPolicy
```

**Modifica tabella:**
```sql
ALTER TABLE computed_order_lines
  ADD COLUMN qty_coverable_now NUMERIC(13,5),
  ADD COLUMN coverable_now     BOOLEAN;
```

Migration: `20260326_a1b2c3d4e5f6_policy_fields_v05.py`

---

## QC — 7 test superati

| Test | Verifica | Esito |
|---|---|---|
| 1 | `core/policies/` non importa da `sync.*` | ✅ |
| 2 | `coverable_now` = `qty_coverable_now >= qty_remaining` su tutte le righe | ✅ |
| 3 | `qty_coverable_now <= qty_remaining` su tutte le righe | ✅ |
| 4 | Articoli con `total_stock <= 0` → `qty_coverable_now = 0` | ✅ |
| 5 | FIFO rispettato: riga parzialmente coperta non seguita da riga con copertura > 0 | ✅ |
| 6 | `SUM(qty_coverable_now) <= total_stock` per ogni articolo | ✅ |
| 7 | Righe chiuse (`qty_remaining <= 0`) non toccate dalla policy | ✅ |

---

## Flusso rebuild aggiornato

### Full rebuild (3 fasi)
```
Fase 1: Source Facts    (invariato)
Fase 2: Computed Facts  (invariato)
Fase 3: Policy
    FifoAllocationPolicy.apply() per ogni articolo in computed_article_demand
```

### Targeted rebuild (con policy)
```
1. DependencyRegistry → affected_orders, affected_articles
2. OrderAggregate.rebuild() per ogni ordine impattato
3. ArticleSupplyDemandAggregate.rebuild() per ogni articolo impattato
4. session.flush()
5. FifoAllocationPolicy.apply() per:
   - articoli da ArticleSupplyDemandAggregate (direct)
   - articoli derivati dagli ordini ricostruiti (via computed_order_lines)
```

---

## Decisioni tecniche confermate

- **UPDATE, non DELETE+INSERT**: la policy aggiorna solo i propri campi su `computed_order_lines`. La tabella appartiene a `OrderAggregate` — il confine di responsabilità è esplicito.
- **FIFO deterministico**: sort su `(order_date ASC, order_source_id ASC)`. Secondo criterio evita ambiguità tra ordini con stessa data.
- **Stock negativo gestito**: `max(total_stock, 0)` — lo stock residuo non scende sotto zero, nessuna riga riceve allocazione negativa.
- **Articoli da ordini ricostruiti**: il targeted rebuild raccoglie `article_source_id` dalle righe degli ordini appena ricostruiti e li aggiunge agli articoli della policy, garantendo che l'allocazione sia sempre aggiornata anche quando cambia solo un ordine.
- **`session.flush()` prima della policy**: rende visibili i `computed_order_lines` appena ricostruiti dagli aggregate prima che la policy li legga.

---

## Criteri di successo v0.5 — verifica

| Criterio | Esito |
|---|---|
| `qty_coverable_now` calcolato correttamente | ✅ QC Test 2, 3, 6 |
| `coverable_now = True` solo se stock sufficiente | ✅ QC Test 2 |
| Ordine FIFO rispettato | ✅ QC Test 5 |
| Full rebuild: policy gira dopo Fase 2 | ✅ Fase 3 in runner.py |
| Targeted rebuild: policy gira per articoli da ordini ricostruiti | ✅ `_get_article_ids_from_orders` |
| `OrderAggregate.rebuild()` non sovrascrive i campi policy | ✅ QC Test 7 — i campi tornano NULL solo sulle righe ricostruite, la policy li ricalcola subito dopo |
| Separazione layer: policies non legge da sync.* | ✅ QC Test 1 |

---

## Prossimo step

**v0.6 — States, Trace, Projection**

Con policy operative, il sistema può ora produrre **stati espliciti** per ogni riga e ordine:

- `OrderLineState`: OPEN / PARTIALLY_FULFILLED / FULFILLED / COVERABLE_NOW / NOT_COVERABLE_NOW
- `OrderState`: OPEN / FULLY_COVERABLE / PARTIALLY_COVERABLE
- `DecisionTrace`: log strutturato policy → risultato per ogni aggregate
- `Projection`: output leggibile (CLI / JSON) per uso operativo
