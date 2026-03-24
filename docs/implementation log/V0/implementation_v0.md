# IMPLEMENTATION V0 — MRS PRODUZIONE

## Obiettivo

Questa fase ha lo scopo di validare **l’architettura definita nei DL-ARCH-001 → 012** tramite una prima implementazione reale, progressiva e modulare.

L’obiettivo NON è costruire un MVP completo, ma verificare:

- solidità della separazione `sync / core / app`
- praticabilità di `Source Facts`, `Computed Facts`, `States`
- sostenibilità degli `Aggregate`
- gestione reale delle `Policy`
- costo e utilità della `Decision Trace`
- fattibilità del `rebuild mirato`

---

## Strategia

Le milestone non sono livelli di complessità, ma **layer architetturali reali** implementati progressivamente.

Ogni milestone deve:
- essere utilizzabile
- essere coerente con i DL
- non essere throwaway
- validare una parte critica del sistema

---

## Roadmap V0

### v0.1 — Sync reale da Easy

#### Obiettivo
Costruire un layer `sync` reale, minimale e architetturalmente corretto.

#### Scope
- Lettura dati da Easy
- Persistenza in tabelle `sync_*`
- Tracciamento `sync_run`
- Generazione `change_set`

#### Tabelle iniziali
- `sync_order_headers`
- `sync_order_lines`
- `sync_articles`
- `sync_stock` (o `movements` se necessario)

#### Deliverable
- Schema DB `sync`
- Mapper Easy → sync
- Script di sync manuale
- `sync_run` log
- `change_set` con:
  - inserted
  - updated
  - deleted

#### Validazione
- Stabilità chiavi
- Qualità mapping
- Gestione dati sporchi reali
- Chiarezza contratto `sync → core`

---

### v0.2 — Source Facts

#### Obiettivo
Costruire il primo layer `core` indipendente da Easy.

#### Source Facts iniziali
- `OrderFact`
- `OrderLineFact`
- `ArticleFact`
- `StockFact`

#### Regole
- Canonici
- Deterministici
- Ricostruibili da `sync`
- Indipendenti dalla struttura Easy

#### Deliverable
- Builder Source Facts
- Mapping `sync_id → fact_id`
- Full rebuild dei facts

#### Validazione
- Qualità modello canonico
- Separazione reale `sync / core`

---

### v0.3 — Computed Facts meccanici

#### Obiettivo
Introdurre calcoli deterministici non legati a policy.

#### Computed Facts iniziali

Per `OrderLine`:
- `qty_remaining`
- `value_remaining`
- `is_open_line`

Per `Article`:
- `current_stock`
- `total_open_demand`
- `net_available_raw`

#### Deliverable
- Modulo computed facts
- Dipendenze esplicite
- Rebuild source + computed

#### Validazione
- Utilità del layer computed
- Assenza di logica decisionale

---

### v0.4 — Aggregate & Rebuild

#### Obiettivo
Introdurre il concetto di **aggregate root** e rebuild governato.

#### Aggregate iniziali
- `OrderAggregate`
- `ArticleSupplyDemandAggregate`

#### Funzionalità
- Mappatura `change_set → facts impattati`
- Mappatura `facts → aggregate`
- Rebuild:
  - full
  - mirato (base)

#### Deliverable
- Registry dipendenze aggregate
- Primo rebuild mirato
- Logging del rebuild

#### Validazione
- Naturalità aggregate
- Gestione dipendenze cross-aggregate
- Complessità reale del rebuild

---

### v0.5 — Policy-driven Computed Facts

#### Obiettivo
Introdurre logica decisionale esplicita tramite policy.

#### Prima policy
- Allocazione stock FIFO

#### Computed Facts
- `qty_coverable_now`
- `coverable_now`

#### Deliverable
- `PolicySet` minimo
- Modulo policy
- Applicazione policy sugli aggregate

#### Validazione
- Separazione facts / policy
- Scalabilità futura
- Evitare leakage di logica nei computed meccanici

---

### v0.6 — States, Trace, Projection

#### Obiettivo
Produrre output operativo spiegabile.

#### States

Per `OrderLine`:
- `OPEN`
- `PARTIALLY_FULFILLED`
- `FULFILLED`
- `COVERABLE_NOW`
- `NOT_COVERABLE_NOW`

Per `Order`:
- `OPEN`
- `FULLY_COVERABLE`
- `PARTIALLY_COVERABLE`

#### Decision Trace

Per ogni decisione chiave:
- source facts
- computed facts
- policy applicata
- risultato
- motivazione

#### Projection
- Output debug (JSON / CLI / API)

#### Deliverable
- Canonical states
- Decision trace base
- Vista finale leggibile

#### Validazione
- Explainability reale
- Leggibilità output
- Nessuna logica nell’app layer

---

## Sequenza di sviluppo

1. Setup progetto
2. v0.1 Sync reale
3. v0.2 Source Facts
4. v0.3 Computed Facts
5. v0.4 Aggregate & Rebuild
6. v0.5 Policy
7. v0.6 States + Trace

---

## Scenario di test consigliato

Dataset minimo ma realistico:

- 1 cliente
- 1 destinazione
- 2 ordini aperti
- 4–6 righe ordine
- 2 articoli condivisi
- stock insufficiente su almeno 1 articolo
- una riga parzialmente evasa
- una modifica sync simulata

---

## Criteri di successo

### 1. Rebuild completo
Sistema ricostruisce tutto da sync senza interventi manuali.

### 2. Rebuild mirato
Dato un change, si identificano aggregate da aggiornare.

### 3. Explainability
Decisioni principali spiegabili via trace.

### 4. Separazione layer
Nessuna logica decisionale fuori dal core.

### 5. Sostenibilità
Il modello resta comprensibile e implementabile.

---

## Rischi attesi

- Confine computed vs state non sempre netto
- Dipendenze cross-aggregate complesse
- Verbosità del modello
- Complessità policy future
- Costo del rebuild mirato

---

## Nota finale

Questa implementazione v0 NON è un MVP prodotto.

È un **test architetturale guidato**.

L’obiettivo è capire:
> “Questo modello è sostenibile in codice reale?”

Se la risposta è sì → si scala.  
Se emergono criticità → si corregge il modello ora, non dopo.

---