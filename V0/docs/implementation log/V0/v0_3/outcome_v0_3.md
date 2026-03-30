# OUTCOME V0.3 — COMPUTED FACTS MECCANICI

**Data chiusura:** 2026-03-25
**Stato:** COMPLETED_WITH_WARNINGS ✅

---

## Risultati del full rebuild finale

| Entità                     | Costruiti | Eliminati | Note |
|----------------------------|-----------|-----------|------|
| computed_order_lines       | 435       | 435       | 1:1 con fact_order_lines |
| computed_stock_balances    | 2.301     | 2.301     | aggregazione su 337k movimenti |
| computed_production_status | 89        | 89        | articoli con almeno un ordine aperto |
| computed_article_demand    | 2.298     | 2.298     | articoli con stock o domanda aperta |

**Durata rebuild completo (Fase 1 + Fase 2):** 1.4s

---

## Copertura DL v0.3 — verifica completa

| Campo DL | Tabella | Campo implementato |
|---|---|---|
| `qty_remaining` | computed_order_lines | `qty_remaining` |
| `value_remaining` | computed_order_lines | `value_remaining` |
| `is_open_line` | computed_order_lines | `is_open_line` |
| `current_stock` | computed_article_demand | `total_stock` (somma su tutti i depositi) |
| `total_open_demand` | computed_article_demand | `total_open_demand` |
| `net_available_raw` | computed_article_demand | `net_available_raw` |

`value_remaining` ha richiesto l'aggiunta di `DOC_PZ_NETTO` (prezzo netto unitario)
attraverso tutti e 3 i layer: `sync_order_lines` → `fact_order_lines` → `computed_order_lines`.

---

## Validazione test architetturali

### Test 1 — Separazione layer ✅
Nessun file in `core/computed_facts/` importa da `sync.*`.
I builder leggono esclusivamente da `fact_*`.

### Test 2 — SQL aggregation ✅
`ComputedStockBalanceBuilder`, `ComputedProductionStatusBuilder` e
`ComputedArticleDemandBuilder` usano `SELECT ... GROUP BY` direttamente in SQL.
Nessun loop Python su dataset grandi.

### Test 3 — Sequenza Fase 1 → Fase 2 ✅
`runner.py` esegue `session.flush()` tra le due fasi.
I Computed Facts leggono i Source Facts appena inseriti nella stessa transazione.

### Test 4 — Determinismo ✅
`del = built` per tutte le entità FULL_REBUILD.
Le variazioni tra run riflettono aggiornamenti reali dei sync_* — non instabilità del rebuild.

### Test 5 — Assenza logica decisionale ✅
Tutti i builder sono pura aritmetica: sottrazioni, somme, comparazioni `> 0`.

---

## Anomalie rilevate e risolte

### 1. `computed_order_lines: built=0` alla prima run
**Causa:** `autoflush=False` sulla session — le righe aggiunte dai Source Facts builder
non erano visibili ai Computed Facts builder nella stessa transazione.

**Fix:** aggiunto `session.flush()` in `runner.py` tra Fase 1 e Fase 2.

**Lezione:** con `autoflush=False`, la visibilità intra-sessione richiede flush esplicito
prima di ogni SELECT che dipende da INSERT pendenti nella stessa sessione.

### 2. `is_fully_shipped=True` su righe con `qty_ordered=NULL`
**Causa:** `qty_ordered or 0` trattava NULL come 0 → `qty_remaining = 0 - 0 = 0`
→ `is_fully_shipped = True` anche senza dati di quantità.

**Fix:** guard esplicito in `ComputedOrderLineBuilder` — tutti i campi calcolati
(`qty_remaining`, `is_fully_shipped`, `is_open_line`, `value_remaining`) sono `NULL`
quando `qty_ordered` è `NULL`.

**Lezione:** `x or 0` non distingue tra `NULL` e `0`. Per campi numerici nullable
con semantica distinta tra assente e zero, usare guard esplicito su `is not None`.

### 3. Encoding `→` nel sync runner
**Causa:** terminale Windows (cp1252) non supporta il carattere `→`.
**Fix:** sostituito con `->` in `sync/runner.py` (già fatto in `core/runner.py`).

---

## Decisioni tecniche confermate

- **`ComputedMetaMixin`**: senza `sync_run_id` — i Computed Facts non hanno dipendenza diretta da un sync run
- **`computed_id` surrogate PK**: coerente con `fact_id` nei Source Facts
- **`session.flush()` esplicito**: necessario tra Fase 1 e Fase 2 con `autoflush=False`
- **SQL aggregation**: pattern validato su più builder — evita loop Python su dataset grandi
- **`unit_price` denormalizzato in `computed_order_lines`**: copia esplicita da `fact_order_lines` — evita join downstream e rende il layer computed autosufficiente per query sulle righe ordine

---

## Criteri di successo v0.3 — verifica

| Criterio | Esito |
|----------|-------|
| Tutti i Computed Facts del DL v0.3 costruiti | ✅ |
| Nessun builder computed legge da `sync_*` | ✅ |
| Aggregazioni via SQL GROUP BY (no loop grandi dataset) | ✅ |
| Runner Fase 1 → flush → Fase 2 in sequenza | ✅ |
| Full rebuild deterministico e ripetibile | ✅ |
| Assenza logica decisionale nei builder | ✅ |

---

## Considerazioni emerse per v0.4+

### 1. Aggregate & Rebuild mirato (→ v0.4 per DL)
Il prossimo step da DL è introdurre `OrderAggregate` e `ArticleSupplyDemandAggregate`
con mappatura `change_set → facts impattati → aggregate da ricalcolare`.

### 2. Computed Facts incrementali
Attualmente tutti i Computed Facts sono FULL_REBUILD.
In v0.4 con rebuild mirato, i computed potranno ricalcolare solo le entità impattate.

### 3. `qty_available` — aggregato di aggregati
`qty_available = total_stock - qty_in_production - total_open_demand`
Tutti e tre i componenti sono ora disponibili in `computed_article_demand`
(total_stock, total_open_demand) e `computed_production_status` (qty_in_production).
Candidato meccanico per completamento in v0.4 prima degli Aggregate,
oppure calcolato direttamente dentro `ArticleSupplyDemandAggregate`.

---

## Prossimo step

**v0.4 — Aggregate & Rebuild mirato** (per DL)

- `OrderAggregate`
- `ArticleSupplyDemandAggregate`
- Registry dipendenze: `change_set → facts → aggregate`
- Primo rebuild mirato
