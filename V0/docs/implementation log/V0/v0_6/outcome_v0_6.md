# OUTCOME V0.6 — STATES, TRACE, PROJECTION

**Data chiusura:** 2026-03-26
**Stato:** COMPLETED ✅

---

## Risultati del test finale

Test eseguito su full rebuild con Fase 4 + QC automatico:

| Step | Risultato |
|---|---|
| Full rebuild con Fase 4 (States) | 10.699 record, 6.8s, COMPLETED_WITH_WARNINGS |
| QC automatico | 8/8 test superati |
| Projection CLI (`app.projection order 107703`) | Output corretto, PARTIALLY_COVERABLE |
| Targeted rebuild dopo full rebuild | COMPLETED, 0 aggregates (nessuna sync nuova) |

### Dettaglio full rebuild

- **446 order_line_states** costruiti
- **150 order_states** costruiti
- Fase 4 eseguita dopo Fase 3 (policy)

---

## Struttura implementata

```
core/
  states/
    __init__.py
    models/
      __init__.py
      order_line_state.py    # ORM order_line_states
      order_state.py         # ORM order_states
    builders/
      __init__.py
      order_state_builder.py # Ricostruisce entrambe le tabelle per un order_source_id

app/
  projection.py              # CLI: python -m app.projection order <id>
```

**Migration:** `20260326_b2c3d4e5f6a7_states_tables_v06.py`

---

## QC — 8 test superati

| Test | Verifica | Esito |
|---|---|---|
| 1 | Nessuno stato riga non valido | ✅ |
| 2 | Nessuno stato ordine non valido | ✅ |
| 3 | `total_lines` coerente con `count(order_line_states)` | ✅ |
| 4 | `fulfilled_lines` coerente con `count(FULFILLED)` | ✅ |
| 5 | `coverable_lines` coerente con `count(COVERABLE_NOW)` | ✅ |
| 6 | Trace JSON valido e completo per tutte le righe | ✅ |
| 7 | Trace JSON valido e completo per tutti gli ordini | ✅ |
| 8 | Ordine FULFILLED solo se tutte le righe sono FULFILLED | ✅ |

---

## Flusso rebuild aggiornato

### Full rebuild (4 fasi)

```
Fase 1: Source Facts     (invariato)
Fase 2: Computed Facts   (invariato)
Fase 3: Policy           (invariato)
Fase 4: States
    OrderStateBuilder.build() per ogni order_source_id in fact_orders
```

### Targeted rebuild (7 step)

```
1. DependencyRegistry → affected_orders, affected_articles
2. OrderAggregate.rebuild()         per ogni ordine impattato
3. ArticleSupplyDemandAggregate.rebuild() per ogni articolo impattato
4. session.flush()
5. FifoAllocationPolicy.apply()     per tutti gli articoli impattati
6. session.flush() (implicito nella sessione)
7. OrderStateBuilder.build()        per tutti gli ordini impattati
```

---

## Decisioni tecniche confermate

- **DELETE + INSERT (non UPDATE)**: `OrderStateBuilder` possiede interamente `order_line_states` e `order_states`. Fa DELETE + INSERT ad ogni rebuild — le tabelle non contengono stato nascosto.
- **`OrderStateBuilder` separato dall'aggregate**: gli stati dipendono da `coverable_now` scritto dalla policy, che gira *dopo* i rebuild. Impossibile calcolare stati dentro `OrderAggregate`.
- **Trace JSON inline**: serializzato nel campo `trace` come stringa JSON. Sufficiente per auditability in v0.6. Promozione a tabella separata prevista in v0.7+.
- **Projection CLI ASCII-safe**: i caratteri speciali Unicode (box drawing) sostituiti con `-` e `OK`/`NO` per compatibilità terminale Windows cp1252.

---

## Criteri di successo v0.6 — verifica

| Criterio | Esito |
|---|---|
| Stati calcolati correttamente su campione reale | ✅ Ispezione projection ordine 107703 |
| Priorità stati rispettata | ✅ QC Test 8 |
| `order_states` coerente con somma `order_line_states` | ✅ QC Test 3, 4, 5 |
| Trace JSON valido e completo | ✅ QC Test 6, 7 |
| Full rebuild: stati calcolati in Fase 4 | ✅ 446 + 150 record |
| Targeted rebuild: stati aggiornati per ordini impattati | ✅ Step 7 in orchestratore |
| Projection CLI leggibile e corretta | ✅ Output manuale verificato |

---

## Prossimo step

**v0.7 — App layer & API**

Con states + projection disponibili:
- REST API minimale per lettura stati ordini
- Autenticazione base
- Dashboard operativa per reparto commerciale
