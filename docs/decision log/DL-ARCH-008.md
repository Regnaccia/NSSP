# DL-ARCH-008 — Origine dei Source Facts: external-derived vs native MRS

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il layer `sync` è responsabile del riallineamento dei dati provenienti da sistemi esterni (es. Easy)
- il layer `core` costruisce i **source facts canonici** del sistema a partire dai dati sincronizzati
- i source facts rappresentano la base di verità interna del sistema (DL-ARCH-002)
- il `core` è un layer rigenerabile e deterministico (DL-ARCH-006)

Nella fase iniziale del progetto, la maggior parte dei dati utilizzati dal sistema deriva dal gestionale Easy.

Tuttavia, l’obiettivo del sistema MRS è:

- **estendere le capacità operative del gestionale**
- introdurre nuove fonti di dati non presenti in Easy
- raccogliere dati direttamente dai reparti (produzione, magazzino, logistica)
- supportare decisioni operative basate su informazioni più aggiornate e granulari

Esempi di dati non presenti in Easy:

- avanzamento produzione in tempo reale
- dichiarazioni operatore
- eventi macchina / linea
- produzione completata ma non ancora consuntivata
- segnalazioni di urgenza inserite manualmente
- override operativi (priorità, rischedulazioni)

Questi dati devono essere integrati nel modello senza compromettere:

- la coerenza del `core`
- la rigenerabilità
- la separazione dei layer

---

## Decision

I **Source Facts** non sono limitati ai dati derivati da sistemi esterni.

Il sistema distingue due categorie di Source Facts:

> **External-derived Source Facts**  
> **Native MRS Source Facts**

Entrambe le categorie:

- appartengono al layer `core`
- rappresentano fatti canonici del dominio
- sono utilizzate come base per computed facts e operational states
- devono essere tracciabili e rigenerabili

---

## Definition

### External-derived Source Facts

Source facts costruiti a partire da dati provenienti da sistemi esterni (es. Easy), tramite il layer `sync`.

Caratteristiche:

- derivati dal layer `sync`
- tracciabili alla sorgente esterna
- riflettono lo stato del sistema esterno
- soggetti a riallineamento tramite sync

Esempi:

- Order
- OrderLine
- Customer
- Destination
- Article
- Stock (contabile)
- quantità evase, imballate, ordinate

---

### Native MRS Source Facts

Source facts generati e mantenuti direttamente dal sistema MRS.

Caratteristiche:

- non derivano da sistemi esterni
- originano da input applicativi o da acquisizione dati interna
- rappresentano eventi o stati operativi reali del sistema
- persistiti e tracciati dal sistema MRS
- devono essere rigenerabili a partire dai dati di origine (eventi, log, input strutturati)

Esempi:

- ProductionExecutionFact
- ProductionProgressFact
- OperatorReport
- LineEvent
- UrgencyFact
- ManualOverride
- ShippingDecision
- dati raccolti da terminali di reparto o PLC

---

## Input Layers

Il sistema distingue concettualmente due modalità di ingresso dei dati:

### 1. External Sync Layer

- responsabile del riallineamento dati da sistemi esterni
- produce dati normalizzati nel layer `sync`
- alimenta gli External-derived Source Facts

### 2. Native Capture / Ingestion Layer

- responsabile dell’acquisizione di dati interni al sistema
- include:
  - input utente (UI)
  - eventi macchina / linea
  - input operatori
  - sistemi IoT / PLC
- alimenta i Native MRS Source Facts

Nota:
Questo layer non è necessariamente denominato `sync` e non deve essere forzato semanticamente nel modello di sincronizzazione esterna.

---

## Unified Core Model

Indipendentemente dalla loro origine, tutti i Source Facts:

- convergono nel layer `core`
- sono trattati in modo uniforme dal sistema
- partecipano alla costruzione di:
  - computed facts
  - canonical operational states

Il modello aggiornato diventa:

**(External Sync + Native Capture) → Source Facts → Computed Facts → Operational States → Projections**

---

## Relationship with Computed Facts

I Computed Facts (DL-ARCH-007):

- possono derivare da:
  - soli external-derived facts
  - soli native facts
  - combinazione di entrambi

Esempi:

### Solo external-derived
- qty_remaining = ordered - shipped

### Solo native
- qty_produced_not_posted = somma eventi produzione non consuntivati

### Combinati
- qty_total_operational_supply =
  stock_easy + produced_not_posted_qty + near_completion_qty

---

## Architectural Implications

### 1. Il CORE è la vera fonte di verità

Il sistema non è “Easy-centric”, ma **core-centric**.

Easy è:

- una sorgente importante
- ma non l’unica

Il `core` rappresenta:

> la realtà operativa del sistema, costruita da più fonti.

---

### 2. Separazione tra origine e significato

- l’origine del dato (external vs native) è distinta dal suo significato
- due facts con origine diversa possono contribuire allo stesso computed fact o stato

---

### 3. Rigenerabilità estesa

Il principio di rigenerabilità (DL-ARCH-006) si estende a tutti i Source Facts:

- external-derived → rigenerabili via sync
- native → rigenerabili da eventi, log o input persistiti

---

### 4. Necessità di tracciabilità dell’origine

Ogni Source Fact deve essere concettualmente tracciabile rispetto alla sua origine:

- external system
- modulo MRS
- linea/macchina
- operatore

Questa tracciabilità può essere:

- esplicita (campo `source`)
- implicita (tipologia entità)

---

### 5. Coerenza nella dependency chain

La dependency chain (DL-ARCH-005) deve supportare:

- dipendenze tra facts di origine diversa
- computed facts che combinano più fonti
- stati derivati da facts eterogenei

---

## Consequences

### Positive

- il sistema diventa realmente estensibile oltre Easy
- possibilità di integrare dati real-time e operativi
- maggiore precisione nelle decisioni operative
- supporto naturale a IoT, produzione e input manuali
- maggiore valore rispetto al solo gestionale
- coerenza architetturale mantenuta

---

### Trade-offs

- maggiore complessità nella gestione delle fonti dati
- necessità di progettare pipeline di acquisizione native
- maggiore attenzione alla qualità e affidabilità dei dati interni
- necessità di definire politiche di riconciliazione tra dati esterni e interni

---

## Relationship with previous DLs

Questo DL:

- **estende DL-ARCH-002**, ampliando il concetto di Source Facts
- è coerente con DL-ARCH-003 e DL-ARCH-004**, mantenendo il ruolo del sync
- si integra con DL-ARCH-005**, estendendo la dependency chain a più origini
- rafforza DL-ARCH-006**, estendendo la rigenerabilità anche ai dati nativi
- completa DL-ARCH-007**, permettendo ai computed facts di combinare più fonti

---

## Notes

Questo DL sancisce un principio fondamentale:

> il sistema MRS non è una copia intelligente del gestionale,  
> ma una piattaforma operativa che costruisce la propria realtà a partire da più fonti.

I Source Facts rappresentano la base comune, indipendentemente dalla loro origine.

Questo consente al sistema di evolvere verso:

- integrazione real-time con la produzione
- supporto decisionale avanzato
- automazioni intelligenti
- applicazioni AI future