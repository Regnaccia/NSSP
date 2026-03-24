# DL-ARCH-010 — Aggregate Roots & Rebuild Boundaries nel layer CORE

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il `core` è fact-centric e costruisce Source Facts e Canonical Operational States (DL-ARCH-002)
- esiste una separazione chiara tra `sync` e `core` (DL-ARCH-004)
- la propagazione dei cambiamenti è governata da dependency chain esplicite (DL-ARCH-005)
- il `core` è rigenerabile e deterministico (DL-ARCH-006)
- esiste un layer intermedio di Computed Facts (DL-ARCH-007)
- i Source Facts possono avere origine sia esterna che nativa (DL-ARCH-008)
- i Computed Facts possono essere meccanici o policy-driven (DL-ARCH-009)

Durante l’analisi di casi operativi complessi emerge un problema strutturale:

> non è ancora definita in modo esplicito l’unità naturale di coerenza e ricalcolo del sistema.

In particolare:

- quando cambia un dato (es. produzione, stock, ordine), non è sempre chiaro **quanto deve essere ricalcolato**
- alcune logiche coinvolgono più entità (ordine, articolo, produzione, urgenze)
- alcuni Computed Facts sono cross-entity e cross-domain
- la dependency chain da sola non è sufficiente a definire i confini del rebuild

È quindi necessario introdurre il concetto di **Aggregate Root** come unità di coerenza del `core`.

---

## Decision

Il layer `core` introduce il concetto di:

> **Aggregate Root (AR)** come unità canonica di:
- coerenza
- rebuild
- valutazione logica

Un Aggregate Root rappresenta:

- un contesto coerente di fatti correlati
- un perimetro naturale di ricalcolo
- un punto di aggregazione per Computed Facts e Operational States

---

## Definition

### Aggregate Root

Un Aggregate Root è:

> un’entità o contesto che definisce un **confine consistente** entro cui i dati devono essere valutati e ricalcolati insieme.

Caratteristiche:

- rappresenta un dominio logico coerente
- include più Source Facts correlati
- può includere Computed Facts locali e cross-entity
- è unità primaria per rebuild parziale
- è indipendente dai layer applicativi

---

## Examples of Aggregate Roots

### 1. Order Aggregate

Contiene:

- Order
- OrderLine(s)
- eventuali UrgencyFact
- Computed Facts locali (qty_remaining, stato ordine)

Uso:

- fulfillment axis
- stato ordine complessivo
- gestione urgenze a livello ordine

---

### 2. Article Supply-Demand Aggregate

Contiene:

- Article
- StockFact
- ProductionFact
- tutte le OrderLine aperte per quell’articolo
- eventuali UrgencyFact sulle righe
- Computed Facts di copertura e disponibilità

Uso:

- availability axis
- copertura domanda-offerta
- simulazioni allocazione

---

### 3. Destination / Shipping Aggregate (futuro)

Contiene:

- Destination
- OrderLine pronte per spedizione
- regole di spedizione
- corrieri
- stati di approntamento

Uso:

- shipping axis
- pianificazione spedizioni

---

## Aggregate vs Entity

Non tutte le entità sono Aggregate Root.

Esempio:

- `OrderLine` è una entità
- `Order` può essere aggregate root
- `ArticleSupplyContext` è aggregate root

Regola:

> un Aggregate Root non è definito dalla struttura dati, ma dal **perimetro di coerenza logica**

---

## Role in Dependency Chain

La dependency chain (DL-ARCH-005) resta valida, ma viene arricchita:

Nuovo modello:

1. Sync → Source Facts
2. Source Facts → Aggregate Root(s)
3. Aggregate Root → Computed Facts
4. Aggregate Root → Operational States
5. States → Projections

L’Aggregate Root diventa il punto centrale di orchestrazione del rebuild.

---

## Rebuild Model

### Rule 1 — Rebuild per Aggregate

Quando cambia un Source Fact:

- si identificano gli Aggregate Root impattati
- si esegue il rebuild dell’aggregate (non solo della singola entità)

---

### Rule 2 — No partial inconsistency

Non è ammesso:

- aggiornare solo una parte dell’aggregate lasciando il resto inconsistente

---

### Rule 3 — Determinism per aggregate

Un Aggregate Root deve essere:

- completamente deterministico
- ricostruibile in modo isolato

---

## Cross-Aggregate Interaction

Alcuni scenari coinvolgono più aggregate.

Esempio:

- produzione cambia → impatta Article aggregate
- Article aggregate impatta Order aggregate (via availability)

Regola:

> le dipendenze tra aggregate devono essere esplicite e tracciabili

---

## Relationship with Computed Facts

### Mechanical Computed Facts

- spesso locali all’aggregate
- calcolati direttamente durante il rebuild dell’aggregate

---

### Policy-driven Computed Facts

- spesso vivono all’interno dell’aggregate
- possono combinare più facts e più entità
- possono dipendere da policy configurabili

---

## Architectural Implications

### 1. Il rebuild diventa aggregate-driven

Non più:

- rebuild per tabella
- rebuild per singola entità

Ma:

- rebuild per contesto logico

---

### 2. Migliore controllo della complessità

- i computed cross-entity vengono confinati nell’aggregate
- gli stati operativi leggono risultati già coerenti

---

### 3. Scalabilità del sistema

- ogni aggregate può evolvere indipendentemente
- nuovi domini possono essere aggiunti senza rompere i precedenti

---

### 4. Preparazione a event-driven architecture

Gli aggregate:

- sono candidati naturali per gestione eventi
- definiscono i confini di consistenza

---

## Design Guidelines

### Rule 1 — Define aggregates early

Gli aggregate principali devono essere identificati il prima possibile.

---

### Rule 2 — Avoid over-fragmentation

Non creare troppi aggregate piccoli:

- aumenta complessità
- rompe la coerenza

---

### Rule 3 — Avoid mega-aggregates

Non creare aggregate troppo grandi:

- impattano performance
- rendono difficile il rebuild

---

### Rule 4 — Align with business reality

Gli aggregate devono riflettere:

- flussi reali
- decisioni operative
- responsabilità logiche

---

## Consequences

### Positive

- maggiore chiarezza del modello
- rebuild più controllato
- gestione naturale dei computed cross-entity
- migliore separazione dei domini
- base solida per scaling e ottimizzazione

---

### Trade-offs

- necessità di identificare correttamente i confini
- possibile revisione futura degli aggregate
- aumento iniziale della complessità concettuale

---

## Relationship with previous DLs

Questo DL:

- completa DL-ARCH-005**, definendo il perimetro reale del rebuild
- rafforza DL-ARCH-006**, rendendo la rigenerabilità più concreta
- si integra con DL-ARCH-007 e DL-ARCH-009**, fornendo il contenitore naturale dei computed
- si basa su DL-ARCH-002**, rispettando il modello multi-axis
- è coerente con DL-ARCH-008**, permettendo aggregate che combinano più origini dati

---

## Notes

Questo DL introduce il concetto che rende il sistema realmente implementabile:

> non basta sapere cosa dipende da cosa,  
> bisogna sapere **dove si chiude il mondo quando ricalcoli**.

Gli Aggregate Roots rappresentano quel confine.