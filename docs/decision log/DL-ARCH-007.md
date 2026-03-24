# DL-ARCH-007 — Introduzione dei Computed Facts nel layer CORE

## Status
Accepted

## Context

Nei DL architetturali precedenti è stato definito che:

- il layer `sync` è responsabile dell’acquisizione e normalizzazione dei dati esterni
- il layer `core` costruisce i **source facts** canonici del sistema
- i **canonical operational states** sono derivati dai source facts e rappresentano stati operativi per i vari assi
- la propagazione dei cambiamenti è governata tramite dependency chain esplicite (DL-ARCH-005)
- il `core` è un layer rigenerabile e deterministico (DL-ARCH-006)

Durante l’analisi di casi operativi reali emerge una categoria di dati che:

- non appartiene al layer `sync`
- non è un source fact puro
- non rappresenta ancora uno stato operativo

Esempi tipici:

- quantità residua di una riga ordine (`qty_remaining`)
- quantità ancora da imballare
- quantità impegnata calcolata
- valore residuo di una riga ordine

Questi dati sono:

- derivati meccanicamente dai source facts
- semanticamente stabili
- riusabili da più contesti e assi operativi

È quindi necessario introdurre esplicitamente un livello intermedio nel modello del `core`.

---

## Decision

Il modello del layer `core` viene esteso introducendo un nuovo livello:

> **Computed Facts**

I Computed Facts sono definiti come:

- valori derivati in modo deterministico dai source facts
- semanticamente stabili e riusabili
- indipendenti da specifiche interpretazioni operative
- rigenerabili a partire dai source facts
- distinti dai canonical operational states

---

## Updated Core Model

Il modello logico del sistema diventa:

**SYNC → Source Facts → Computed Facts → Canonical Operational States → Projections**

Dove:

- `sync` → rappresentazione normalizzata dei dati esterni
- `source facts` → fatti canonici del dominio
- `computed facts` → valori canonici derivati dai facts
- `canonical operational states` → interpretazione operativa per asse
- `projections` → viste applicative

---

## Semantic Distinction

### Source Facts

Rappresentano fatti canonici del dominio interno.

Caratteristiche:

- derivati dal layer `sync`
- tracciabili alla sorgente
- semanticamente stabili
- indipendenti da logiche operative

Esempi:

- Order
- OrderLine
- Article
- Customer
- Destination
- quantità ordinate, evase, imballate

---

### Computed Facts

Rappresentano valori canonici derivati meccanicamente dai source facts.

Caratteristiche:

- derivazione deterministica
- nessuna interpretazione operativa
- riusabili da più assi
- rigenerabili
- non dipendono da decisioni di processo

Esempi:

- `qty_remaining = qty_ordered - qty_shipped`
- `qty_unpacked = qty_shipped - qty_packed`
- valore residuo riga ordine

---

### Canonical Operational States

Rappresentano interpretazioni operative del sistema.

Caratteristiche:

- dipendono da source facts e/o computed facts
- legati a uno specifico asse operativo
- esprimono uno stato decisionale

Esempi:

- `partially_fulfilled`
- `fulfilled`
- `ready_to_ship`
- `in_delay`

---

## Dependency Chain Update

La dependency chain viene estesa come segue:

1. **SYNC → Source Facts**
2. **Source Facts → Computed Facts**
3. **Source Facts + Computed Facts → Canonical Operational States**
4. **Canonical States → Projections**

Il layer `core` deve mantenere mapping espliciti tra questi livelli.

---

## Rebuild Implications

Il modello di rigenerazione del `core` viene aggiornato:

- una modifica nei source facts richiede:
  - rebuild dei computed facts dipendenti
  - rebuild degli operational states dipendenti

- i computed facts:
  - non devono contenere stato implicito
  - devono essere completamente rigenerabili

- gli operational states:
  - devono dipendere da computed facts ove possibile, evitando duplicazioni logiche

---

## Physical Modeling Guidelines

I Computed Facts sono entità **logiche distinte** dai Source Facts.

A livello fisico possono essere implementati come:

- tabelle dedicate
- viste (views)
- viste materializzate
- strutture calcolate runtime
- espansioni controllate delle tabelle source (solo in casi semplici e ben definiti)

Principio:

> la distinzione logica deve essere sempre mantenuta, indipendentemente dalla scelta fisica.

---

## Design Guidelines

### Rule 1 — No contamination

I source facts non devono essere contaminati da:

- valori derivati complessi
- logiche di stato operativo

---

### Rule 2 — Reusability first

I computed facts devono essere progettati per essere:

- riusabili tra più assi
- indipendenti da specifiche applicazioni

---

### Rule 3 — State minimalism

Gli operational states devono:

- evitare duplicazione di logiche numeriche
- utilizzare computed facts come input

---

### Rule 4 — Determinism

I computed facts devono essere:

- completamente deterministici
- indipendenti da esecuzioni precedenti

---

## Consequences

### Positive

- maggiore chiarezza del modello del `core`
- separazione netta tra dato, derivazione e interpretazione
- riduzione della complessità degli operational states
- maggiore riusabilità cross-axis
- migliore allineamento con la dependency chain
- miglior supporto alla rigenerabilità

---

### Trade-offs

- introduzione di un livello architetturale aggiuntivo
- aumento del numero di entità logiche
- necessità di governance per evitare proliferazione incontrollata
- maggiore disciplina progettuale richiesta

---

## Relationship with previous DLs

Questo DL:

- **estende DL-ARCH-002**, introducendo un livello intermedio tra source facts e operational states
- è **coerente con DL-ARCH-004**, mantenendo il confine tra sync e core
- rafforza DL-ARCH-005**, espandendo la dependency chain
- è **allineato con DL-ARCH-006**, mantenendo la rigenerabilità del core

---

## Notes

I Computed Facts rappresentano un concetto chiave per rendere il sistema:

- più implementabile
- più leggibile
- più stabile nel tempo

Il loro ruolo è separare in modo netto:

- ciò che il sistema **sa** (facts)
- ciò che il sistema **calcola** (computed facts)
- ciò che il sistema **decide/interpreta** (states)