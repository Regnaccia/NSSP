# OUTCOME V0.2 — SOURCE FACTS

**Data chiusura:** 2026-03-25
**Stato:** COMPLETED_WITH_WARNINGS ✅

---

## Risultati del primo full rebuild

Prima esecuzione su dati reali derivati da `sync_*`:

| Entità              | Costruiti | Eliminati | Warnings | Note |
|---------------------|-----------|-----------|----------|------|
| fact_articles       | 2.491     | 0         | 0        | prima run — nessun dato precedente |
| fact_customers      | 566       | 0         | 0        |      |
| fact_destinations   | 867       | 0         | 53       | 53 destinazioni orfane saltate (vedi sotto) |
| fact_orders         | 145       | 0         | 0        |      |
| fact_order_lines    | 431       | 0         | 0        |      |
| fact_stock_movements| 337.063   | 0         | 0        | APPEND_ONLY — 337k record da sync |
| fact_productions    | 134       | 0         | 0        |      |

**Durata:** 40.5s (dominata da fact_stock_movements — 337k record)

---

## Validazione test architetturali

### Test 1 — Rigenerabilità ✅
Full rebuild eseguibile da zero a partire dalle sole tabelle `sync_*`.
Risultato deterministico e ripetibile.

### Test 2 — Indipendenza da Easy ✅
Nessun builder importa da `sync.easy.*` o accede a tabelle Easy.
Il layer `core` conosce solo `sync_*`.

### Test 3 — Normalizzazione canonica ✅
Codici articolo, cliente e destinazione normalizzati (uppercase + strip) nei builder.
I dati `sync_*` restano fedeli a Easy; i `fact_*` contengono valori canonici.

### Test 4 — Destinazione effettiva ✅
La regola di dominio è implementata in `DestinationBuilder`:
- 566 clienti → alcuni coperti da destinazioni esplicite in `sync_destinations`
- i clienti restanti → destinazione derivata da `sync_customers` (`is_derived_from_customer=True`)
- totale fact_destinations (867) > sync_destinations (566) — il delta sono le destinazioni derivate

### Test 5 — Separazione layer ✅
Nessuna violazione di confine rilevata.

---

## Anomalie rilevate e risolte

### 1. Destinazioni orfane in Easy (53 record)
`sync_destinations` contiene 53 destinazioni con `customer_source_id = NULL`.
Probabilmente record storici mai puliti in EasyJob.

**Comportamento adottato:** skip con warning — il builder non inserisce la destinazione
e registra il codice nel log di run. Il sistema continua senza errori.

**Decisione:** il dato sporco resta in `sync_*` (fedeltà a Easy) e viene filtrato
nel layer core. Non richiede intervento immediato.

### 2. `StringDataRightTruncation` su `fact_destinations.name`
Il campo `name` in `fact_destinations` era `String(55)` (copiato da `sync_destinations`).
Le destinazioni derivate da clienti usano `sync_customers.name` che è `String(110)`.

**Fix:** `fact_destinations.name` allargato a `String(110)` + migrazione Alembic applicata.

**Lezione:** quando dati da sorgenti di dimensioni diverse confluiscono nella stessa tabella,
il campo deve essere dimensionato sul più grande tra le sorgenti.

### 3. `NotNullViolation` su `fact_destinations.customer_source_id`
Prima run fallita perché le 53 destinazioni orfane venivano inserite con `customer_source_id=NULL`.
**Fix:** guard esplicito nel builder + warning loggato.

---

## Decisioni tecniche confermate

- **Struttura `core/facts/`**: modelli in `models/`, builder in `builders/` — leggibile e estendibile
- **`fact_id` surrogate key**: ogni tabella `fact_*` ha PK interna separata da `source_id`
- **FULL_REBUILD vs APPEND_ONLY**: strategia corretta — APPEND_ONLY per stock_movements evita di riprocessare 337k record ad ogni run
- **`records_deleted` tracciato**: il rowcount del delete è ora incluso nell'output del runner

---

## Criteri di successo v0.2 — verifica

| Criterio | Esito |
|----------|-------|
| Tutti i Source Facts costruiti da `sync_*` | ✅ |
| Full rebuild funzionante e deterministico | ✅ |
| Core indipendente da Easy | ✅ |
| Normalizzazione canonica applicata | ✅ |
| Regola destinazione effettiva implementata | ✅ |
| Nessuna logica di Computed Fact nei Source Facts | ✅ |

---

## Considerazioni emerse per v0.3+

### 1. Durata rebuild dominata da StockMovements
40.5s quasi interamente dovuti ai 337k record di `fact_stock_movements`.
La strategia APPEND_ONLY mitiga il problema nelle run successive.
Per il full rebuild notturno è accettabile.

### 2. Rebuild parziale — upsert vs delete+insert (→ v0.4)
Attualmente tutti i builder FULL_REBUILD fanno delete-all + reinsert.
In v0.4 con rebuild incrementale (guidato dal change set) sarà necessario
scegliere per ogni entità tra:
- **upsert su `source_id`**: naturale per la maggior parte delle entità
- **delete + reinsert selettivo**: per entità con logiche di costruzione complesse (es. `fact_destinations` con derived rows)

### 3. Destinazioni orfane — coordinamento con OMR (→ futuro)
53 destinazioni in Easy non hanno cliente associato.
Probabile dato legacy non pulito. Da segnalare a chi gestisce EasyJob
se le destinazioni sono ancora operative.

### 4. Scope Computed Facts per v0.3
A partire dai Source Facts ora disponibili, i Computed Facts prioritari sono:
- `qty_remaining` per riga ordine (`qty_ordered - qty_shipped`)
- `stock_balance` per articolo/deposito (somma movimenti `qty_in - qty_out`)
- `qty_in_production` per articolo (da `fact_productions` aperte)

---

## Prossimo step

**v0.3 — Computed Facts meccanici**

A partire dai `fact_*`, calcolo deterministico di valori derivati
senza logica decisionale né policy aziendali.
