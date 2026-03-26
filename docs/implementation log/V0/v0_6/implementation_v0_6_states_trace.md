# SPEC V0.6 — STATES, TRACE, PROJECTION

**Data apertura:** 2026-03-26
**Stato:** COMPLETED ✅

---

## Obiettivo

Produrre **output operativo spiegabile**: ogni riga ordine e ogni ordine
ricevono uno stato esplicito derivato dai computed facts e dalle policy,
con una traccia minimale di come si è arrivati a quella conclusione.

In v0.5 il sistema sa già se una riga è coperta dallo stock (FIFO).
In v0.6 formalizza questo in **Canonical States** persistenti e produce
una **Projection** leggibile per uso operativo.

---

## Riferimenti ai DL

| DL | Principio rilevante |
|---|---|
| DL-ARCH-007 | SYNC → Source Facts → Computed Facts → **Operational States** → Projections |
| DL-ARCH-012 | Decision Trace: ogni stato deve avere una spiegazione deterministica e auditabile |
| DL-ARCH-013 | States = Persistent Canonical. Projections = in-memory, non persistite |
| DL-ARCH-005 | States sono l'ultimo step della catena di rebuild, dopo i Computed Facts |

---

## Canonical States

Gli stati sono **persistenti** (tabelle DB) e **ricostruibili** (rebuild da computed facts).
Appartengono al layer `core/states/`.

### `OrderLineState`

Stato di una singola riga ordine. Cinque valori possibili:

| Stato | Condizione |
|---|---|
| `FULFILLED` | `is_fully_shipped = True` |
| `PARTIALLY_FULFILLED` | `qty_shipped > 0` AND `qty_remaining > 0` |
| `COVERABLE_NOW` | `is_open_line = True` AND `coverable_now = True` |
| `NOT_COVERABLE_NOW` | `is_open_line = True` AND `coverable_now = False` (o NULL) |
| `OPEN` | nessuna delle precedenti (qty_ordered NULL, nessun dato spedizione) |

Priorità: FULFILLED > PARTIALLY_FULFILLED > COVERABLE_NOW / NOT_COVERABLE_NOW > OPEN

**Tabella `order_line_states`:**

| Campo | Tipo | Note |
|---|---|---|
| state_id | BigInteger PK | autoincrement |
| order_source_id | BigInteger | FK logica a fact_orders |
| line_number | BigInteger | |
| article_source_id | String(25) | nullable |
| state | String(25) | valore enum |
| trace | Text | JSON — spiegazione minimale della decisione |
| built_at | DateTime(tz) | |

### `OrderState`

Stato aggregato per ordine. Derivato dagli stati delle sue righe.

| Stato | Condizione |
|---|---|
| `FULFILLED` | tutte le righe sono FULFILLED |
| `FULLY_COVERABLE` | tutte le righe aperte sono COVERABLE_NOW |
| `PARTIALLY_COVERABLE` | almeno una riga aperta è COVERABLE_NOW, almeno una NOT_COVERABLE_NOW |
| `OPEN` | nessuna riga aperta coperta (tutte NOT_COVERABLE_NOW o OPEN) |

**Tabella `order_states`:**

| Campo | Tipo | Note |
|---|---|---|
| state_id | BigInteger PK | autoincrement |
| order_source_id | BigInteger | unico per ordine |
| state | String(25) | valore enum |
| total_lines | Integer | totale righe dell'ordine |
| open_lines | Integer | righe con qty_remaining > 0 |
| coverable_lines | Integer | righe COVERABLE_NOW |
| fulfilled_lines | Integer | righe FULFILLED |
| trace | Text | JSON — riepilogo della composizione |
| built_at | DateTime(tz) | |

---

## Decision Trace (minimale)

Per v0.6 il trace è un **JSON inline** nel campo `trace` di ogni state row.
Non è una tabella separata — è sufficiente per l'auditability di questa fase.

**Formato `order_line_states.trace`:**
```json
{
  "qty_ordered": 10,
  "qty_shipped": 3,
  "qty_remaining": 7,
  "coverable_now": true,
  "qty_coverable_now": 7,
  "policy": "fifo_allocation",
  "decision": "COVERABLE_NOW"
}
```

**Formato `order_states.trace`:**
```json
{
  "total_lines": 4,
  "open_lines": 3,
  "coverable_lines": 2,
  "fulfilled_lines": 1,
  "decision": "PARTIALLY_COVERABLE"
}
```

---

## Struttura directory

```
core/
  states/
    __init__.py
    models/
      __init__.py
      order_line_state.py    # modello ORM order_line_states
      order_state.py         # modello ORM order_states
    builders/
      __init__.py
      order_state_builder.py # ricostruisce entrambe le tabelle per un order_source_id
```

---

## `OrderStateBuilder`

Ricostruisce gli stati per un singolo ordine.

```
input:  session, order_source_id
output: BuildResult

1. DELETE order_line_states WHERE order_source_id = X
2. Legge computed_order_lines WHERE order_source_id = X
3. Per ogni riga: determina lo stato + produce il trace JSON
4. INSERT order_line_states
5. DELETE order_states WHERE order_source_id = X
6. Aggrega gli stati delle righe → determina order state + produce trace JSON
7. INSERT order_states
```

---

## Integrazione nel flusso di rebuild

### Targeted rebuild (step aggiornati)

```
1. DependencyRegistry → affected_orders, affected_articles
2. OrderAggregate.rebuild()         per ogni ordine impattato
3. ArticleSupplyDemandAggregate.rebuild() per ogni articolo impattato
4. session.flush()
5. FifoAllocationPolicy.apply()     per tutti gli articoli impattati
6. session.flush()
7. OrderStateBuilder.build()        per tutti gli ordini impattati
```

Gli ordini da processare nello step 7 sono gli stessi di `affected[OrderAggregate]`.

### Full rebuild (4 fasi)

```
Fase 1: Source Facts   (invariato)
Fase 2: Computed Facts (invariato)
Fase 3: Policy         (invariato)
Fase 4: States
    OrderStateBuilder.build() per ogni order_source_id in fact_orders
```

---

## Projection (CLI)

Una proiezione CLI leggibile per un singolo ordine. Non persistita.

```
python -m app.projection order <order_source_id>
```

**Output esempio:**
```
Ordine 107703 — PARTIALLY_COVERABLE
Cliente: C001  Data: 2026-01-15  Consegna attesa: 2026-01-30

  Riga  Articolo       Ord    Ship   Rem    Coperta    Stato
  ────────────────────────────────────────────────────────────
  1     SAF             50     10     40     40 ✓     COVERABLE_NOW
  2     SB               8      0      8      0 ✗     NOT_COVERABLE_NOW
  3     12X8X80         20     20      0      -       FULFILLED
```

Il modulo `app/projection.py` legge da `order_states`, `order_line_states`,
`fact_orders`, `fact_order_lines`. Nessuna logica — solo lettura e formattazione.

---

## Criteri di successo v0.6

| Criterio | Verifica |
|---|---|
| Stati calcolati correttamente su campione reale | ispezione spot su DB |
| Priorità stati rispettata (FULFILLED > PARTIALLY_FULFILLED > ...) | QC automatico |
| `order_states` coerente con somma `order_line_states` | QC automatico |
| Trace JSON valido e completo per ogni riga | QC automatico |
| Full rebuild: stati calcolati in Fase 4 | verifica count tabelle |
| Targeted rebuild: stati aggiornati per ordini impattati | test su sync run reale |
| Projection CLI leggibile e corretta | verifica output manuale |

---

## Considerazioni architetturali

### Perché gli stati non vivono dentro `OrderAggregate.rebuild()`?

Gli stati dipendono da `coverable_now`, che è scritto dalla policy
**dopo** il rebuild degli aggregate. `OrderAggregate` non può calcolare
stati completi — li calcola incompleti o deve invocare la policy internamente.

Soluzione: `OrderStateBuilder` è un passaggio separato nell'orchestratore,
eseguito dopo tutti gli aggregate e tutte le policy.

### Perché il trace è JSON inline e non una tabella?

Per v0.6 il trace è un'informazione di supporto, non un'entità autonoma.
Una tabella separata sarebbe over-engineering per questa fase.
La promozione a tabella dedicata (con query e audit strutturati) è prevista in v0.7+.

### Gli stati sono regenerabili

`order_line_states` e `order_states` sono interamente derivabili
da `computed_order_lines` + `fact_orders`. Ogni rebuild completo li ricalcola.
Non contengono stato nascosto.

---

## Prossimo step

**v0.7 — App layer & API**

Con states + projection disponibili:
- REST API minimale per lettura stati ordini
- Autenticazione base
- Dashboard operativa per reparto commerciale
