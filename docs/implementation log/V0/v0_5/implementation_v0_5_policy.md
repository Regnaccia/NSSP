# SPEC V0.5 — POLICY-DRIVEN COMPUTED FACTS

**Data apertura:** 2026-03-25
**Stato:** IN PROGRESS

---

## Obiettivo

Introdurre la prima **Policy** del sistema: l'allocazione FIFO dello stock
sulle righe ordine aperte.

In v0.3–v0.4 i Computed Facts sono tutti meccanici (aritmetica pura, nessuna scelta).
In v0.5 il sistema impara a **prendere decisioni** basate sullo stock disponibile:
per ogni articolo, quali righe ordine aperte possono essere evase ora?

---

## Cosa cambia rispetto a v0.4

| Aspetto | v0.4 | v0.5 |
|---|---|---|
| Computed Facts | Meccanici (somme, sottrazioni) | + Policy-driven (allocazione) |
| Logica decisionale | Assente | `FifoAllocationPolicy` |
| Flusso rebuild | Aggregates | Aggregates → Policy |
| Nuovi campi | — | `qty_coverable_now`, `coverable_now` |

---

## Concetto di Policy in questo sistema

Una **Policy** è una funzione `f(session, aggregate_id) → scrivi computed facts`.

Si distingue da un Computed Fact meccanico perché:
- Applica **una scelta** (qui: chi prende lo stock prima)
- Il risultato dipende da **più aggregati insieme** (stock di un articolo + righe di più ordini)
- La scelta è **esplicita e sostituibile** (FIFO oggi, LIFO o priorità domani)

Le Policy vivono nel layer `core/policies/`, separato dagli aggregati.
Non modificano `fact_*`. Scrivono solo `computed_*` policy-driven.

---

## Prima Policy: `FifoAllocationPolicy`

### Logica

Dato un `article_id`:

1. Legge lo stock disponibile: `computed_article_demand.total_stock`
2. Legge tutte le righe ordine aperte per quell'articolo da `computed_order_lines`
   (righe con `qty_remaining > 0`), ordinate per `order_date ASC` (FIFO)
3. Distribuisce lo stock residuo riga per riga:
   ```
   stock_residuo = total_stock
   per ogni riga (ordine data crescente):
       qty_coverable_now = min(qty_remaining, max(stock_residuo, 0))
       coverable_now     = qty_coverable_now >= qty_remaining
       stock_residuo    -= qty_coverable_now
   ```
4. Aggiorna i campi `qty_coverable_now` e `coverable_now` su `computed_order_lines`

### Input necessari

| Fonte | Campi usati |
|---|---|
| `computed_article_demand` | `total_stock` |
| `computed_order_lines` | `order_source_id`, `line_number`, `article_source_id`, `qty_remaining` |
| `fact_orders` | `order_date` (per il sort FIFO) |

### Output

Aggiornamento UPDATE su `computed_order_lines`:

| Campo | Tipo | Nota |
|---|---|---|
| `qty_coverable_now` | Numeric | quanta domanda è coperta dallo stock attuale |
| `coverable_now` | Boolean | `qty_coverable_now >= qty_remaining` |

---

## Modifica tabella `computed_order_lines`

Aggiunta di due colonne nullable via migration:

```sql
ALTER TABLE computed_order_lines
  ADD COLUMN qty_coverable_now NUMERIC(13,5),
  ADD COLUMN coverable_now     BOOLEAN;
```

I campi sono `NULL` finché la policy non gira.
`OrderAggregate.rebuild()` non li calcola — rimangono a cura esclusiva della policy.

**Problema:** `OrderAggregate.rebuild()` fa DELETE + INSERT su `computed_order_lines`,
cancellando i valori policy. **La policy deve girare dopo ogni rebuild di aggregate che la tocca.**

---

## Struttura directory

```
core/
  policies/
    __init__.py
    base.py                      # BasePolicy
    fifo_allocation.py           # FifoAllocationPolicy
```

### `BasePolicy`

```python
class BasePolicy:
    policy_type: str

    def apply(self, session, aggregate_id: str) -> PolicyResult:
        raise NotImplementedError
```

`PolicyResult`: dataclass con `policy_type`, `aggregate_id`, `records_updated`, `errors`.

---

## Integrazione nel flusso di rebuild

### Flusso targeted rebuild aggiornato

```
1. DependencyRegistry → affected_orders, affected_articles
2. OrderAggregate.rebuild() per ogni ordine impattato
3. ArticleSupplyDemandAggregate.rebuild() per ogni articolo impattato
4. FifoAllocationPolicy.apply() per ogni articolo impattato
   (include articoli derivati dagli ordini ricostruiti al passo 2)
```

**Step 4 — articoli da cui derivare la policy:**

Gli ordini ricostruiti al passo 2 possono toccare `computed_order_lines`
su articoli che non erano in `affected_articles`. Bisogna raccogliere
gli `article_source_id` distinti dalle righe ricostruite dagli ordini
e aggiungerli agli `affected_articles` per la policy.

Il `targeted_rebuild.py` (o un nuovo `PolicyOrchestrator`) si occupa di:
- Collezionare gli `article_source_id` dopo i rebuild degli ordini
- Fare `union` con gli `affected_articles`
- Chiamare `FifoAllocationPolicy.apply()` per tutti

### Flusso full rebuild aggiornato

```
--- Fase 1: Source Facts ---      (invariato)
--- Fase 2: Computed Facts ---    (invariato)
--- Fase 3: Policy ---
    FifoAllocationPolicy.apply() per ogni articolo in computed_article_demand
```

`runner.py` aggiunge la Fase 3 dopo il flush di Fase 2.

---

## `core_run` — estensione logging

Aggiunta di un campo opzionale per le policy applicate:

| Campo | Tipo | Note |
|---|---|---|
| `policies_applied` | Integer | nullable — numero di articoli processati dalla policy |

Alternativa più leggera: incluso in `records_rebuilt` con nota in `notes`.
→ **Scelta v0.5:** incluso in `records_rebuilt`, nota in `notes` (no migration aggiuntiva).

---

## Criteri di successo v0.5

| Criterio | Verifica |
|---|---|
| `qty_coverable_now` calcolato correttamente su campione reale | confronto manuale stock vs righe |
| `coverable_now = True` solo se stock sufficiente per quella riga | ispezione spot |
| Ordine FIFO rispettato (data ordine crescente) | verifica su articolo con più ordini |
| Full rebuild: policy gira dopo Fase 2 | `computed_order_lines` con campi non NULL |
| Targeted rebuild: policy gira per articoli da ordini ricostruiti | test con sync che tocca solo ordini |
| `OrderAggregate.rebuild()` non sovrascrive i campi policy | ispezione — i campi tornano NULL solo se la policy rigira dopo |

---

## Considerazioni architetturali

### Perché UPDATE e non DELETE + INSERT?

La policy **non possiede** `computed_order_lines` — la tabella è dell'OrderAggregate.
La policy aggiorna solo i suoi campi. Questo rende chiaro il confine di responsabilità.

### Perché non una tabella separata `computed_order_line_coverage`?

Una tabella separata sarebbe più pura ma richiederebbe JOIN per ogni query downstream.
Con due colonne nullable su `computed_order_lines` il consumer vede tutto in una riga.
Se il confine diventerà un problema reale → migrare in v0.6.

### FIFO su `order_date` — ambiguità

Se due ordini hanno la stessa `order_date`, il FIFO è deterministico solo se si aggiunge
un secondo criterio di ordinamento (`order_source_id ASC`). Lo includiamo dal principio.

### Stock negativo

`total_stock` può essere negativo (movimenti in uscita > entrate).
In quel caso `max(stock_residuo, 0) = 0` → tutte le righe ottengono `qty_coverable_now = 0`.

---

## Prossimo step

**v0.6 — States, Trace, Projection**

- `OrderLineState`: OPEN / PARTIALLY_FULFILLED / FULFILLED / COVERABLE_NOW / NOT_COVERABLE_NOW
- `OrderState`: OPEN / FULLY_COVERABLE / PARTIALLY_COVERABLE
- `DecisionTrace`: log strutturato delle decisioni per ogni aggregate
- `Projection`: output leggibile (CLI / JSON)
