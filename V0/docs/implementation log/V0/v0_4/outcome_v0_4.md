# OUTCOME V0.4 — AGGREGATE & REBUILD MIRATO

**Data chiusura:** 2026-03-25
**Stato:** COMPLETED ✅

---

## Risultati del targeted rebuild finale

Test eseguito su sync run reale con modifiche effettive:

| Step | Risultato |
|---|---|
| Full rebuild (baseline) | 9.766 record, 1.3s, COMPLETED_WITH_WARNINGS |
| Sync run successiva | 46 ins, 7 upd, 8 del su più entity_type |
| Targeted rebuild | 28 aggregate, 177 record, 0.4s, COMPLETED |

### Dettaglio aggregate ricostruiti

**OrderAggregate** — 9 ordini (trigger: sync_order_headers + sync_order_lines):
`107541`, `107679`, `107703`, `107775`, `107776`, `107777`, `107778`, `107779`, `107780`

**ArticleSupplyDemandAggregate** — 19 articoli (trigger: sync_order_lines → lookup article_source_id + sync_stock_movements):
`12X8X80`, `24X14X100R`, `25X14TRC`, `25X14X200`, `25X14X250`, `28X16TRC`, `28X16X180`,
`4X4X25`, `5X5X22`, `8X7TRC`, `8X7X40`, `DESCRIZIONE LIBERA`, `S`, `SAB`, `SAF`,
`SB`, `SB1`, `SPEZZONI`, `TORNITURA`

---

## Struttura implementata

```
core/
  aggregates/
    base.py                            # BaseAggregate + RebuildResult
    order_aggregate.py                 # OrderAggregate
    article_supply_demand_aggregate.py # ArticleSupplyDemandAggregate
  orchestrators/
    dependency_registry.py             # change_set → {AggregateClass: {ids}}
    targeted_rebuild.py                # run_targeted_rebuild()
  models/
    core_run.py                        # log di ogni esecuzione core
  runner.py                            # aggiornato: full rebuild + targeted rebuild
```

---

## Modello `core_run`

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

Migration: `20260325_cc3d86f0809b_core_run_v04.py`

---

## Validazione test architetturali

### Test 1 — Full rebuild invariato ✅
Il full rebuild produce risultati identici a v0.3.
Le classi Aggregate non interferiscono con i builder esistenti.

### Test 2 — DependencyRegistry copre tutti gli entity_type ✅
| entity_type | Aggregate impattato | Strategia |
|---|---|---|
| `sync_order_headers` | OrderAggregate | source_id diretto |
| `sync_order_lines` | OrderAggregate | split `"order_id\|line_number"` → parts[0] |
| `sync_order_lines` | ArticleSupplyDemandAggregate | batch lookup IN su SyncOrderLine |
| `sync_articles` | ArticleSupplyDemandAggregate | source_id diretto |
| `sync_stock_movements` | ArticleSupplyDemandAggregate | batch lookup IN su SyncStockMovement |
| `sync_productions` | ArticleSupplyDemandAggregate | batch lookup IN su SyncProduction |

Tutti i lookup sono query batch (`IN`) — una query per entity_type, indipendente dal numero di righe cambiate.

### Test 3 — Ordine di esecuzione corretto ✅
`OrderAggregate` eseguito prima di `ArticleSupplyDemandAggregate`.
`computed_article_demand` legge `fact_order_lines` già ricalcolato nello stesso rebuild.

### Test 4 — Idempotenza ✅
Ogni rebuild cancella (DELETE WHERE aggregate_id) e reinserisce.
Doppio targeted rebuild sullo stesso change_set produce risultati identici.

### Test 5 — Isolamento layer sync ✅
`DependencyRegistry` esegue lookup su `sync_*` read-only.
`sync_change_item` non viene modificato dal layer core.

---

## Anomalie rilevate e risolte

### 1. `_get_latest_sync_run_id` — NameError in targeted_rebuild.py
**Causa:** la funzione `get_latest_sync_run_id` era stata rinominata durante lo sviluppo,
ma rimasto un riferimento interno con il prefisso privato `_get_latest_sync_run_id` alla riga 56.

**Fix:** sostituito con il nome corretto `get_latest_sync_run_id`.

**Lezione:** prefissi `_` inconsistenti tra definizione e chiamata non sono catturati
da import check — solo dall'esecuzione del ramo corrispondente.

---

## Decisioni tecniche confermate

- **`BaseAggregate` + `RebuildResult`**: interfaccia minimale — ogni aggregate è autonomo nel proprio rebuild
- **Batch lookup IN**: il DependencyRegistry non fa N query per N change items — una query per entity_type
- **Ordine fisso `OrderAggregate → ArticleSupplyDemandAggregate`**: risolve la dipendenza `computed_article_demand → fact_order_lines` senza coordinazione dinamica
- **`core_run` come baseline**: il full rebuild scrive `sync_run_id_to` — il targeted rebuild parte da lì, senza bisogno di stato esterno
- **Transazione unica per targeted rebuild**: tutti gli aggregate ricostruiti in un unico `get_session()` — commit atomico o rollback completo

---

## Criteri di successo v0.4 — verifica

| Criterio | Esito |
|---|---|
| Full rebuild esistente non rotto | ✅ output identico a v0.3 |
| Targeted rebuild corretto su campione reale | ✅ 28 aggregate su sync run reale |
| `core_run` loggato correttamente | ✅ record presente dopo ogni run |
| DependencyRegistry copre tutti gli entity_type | ✅ 6 entity_type mappati |
| Rebuild mirato più veloce del full rebuild | ✅ 0.4s vs 1.3s su run con poche modifiche |

---

## Prossimo step

**v0.5 — Policy & Orchestration**

Il rebuild mirato è ora il punto di partenza per applicare logica decisionale
sugli aggregate già ricalcolati:

- `PolicyEngine`: valuta le condizioni post-rebuild su `computed_article_demand`
- `Orchestrator`: coordina Policy → Action su ogni aggregate impattato
- `DecisionTrace`: log strutturato delle decisioni per audit e debug
- La `core_run` diventa il punto di ancoraggio per la traccia decisionale di v0.6
