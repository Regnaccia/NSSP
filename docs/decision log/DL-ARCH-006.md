# DL-ARCH-006 — Rigenerabilità del layer CORE

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il layer `sync` è responsabile del riallineamento dei dati esterni
- il layer `core` costruisce i source facts e gli stati operativi canonici
- i source facts sono tracciabili e ricostruibili
- gli stati canonici sono derivati dai source facts e organizzati per assi
- la propagazione dei cambiamenti è governata tramite dependency chain esplicite

Questo implica che il `core` non deve essere trattato come un sistema che accumula stato in modo opaco, ma come un sistema in grado di **ricostruire il proprio stato interno a partire da input deterministici**.

È quindi necessario formalizzare il principio di **rigenerabilità del layer CORE**.

## Decision

Il layer `core` viene definito come un layer **rigenerabile**, basato su operazioni canoniche richiamabili che permettono di ricostruire:

- i source facts
- i canonical operational states

a partire dai dati del layer `sync`.

Il `core` non è progettato come accumulatore incrementale non deterministico, ma come sistema in grado di:

- ricostruire completamente il proprio stato
- ricostruire porzioni del proprio stato
- rigenerare stati a partire da dati sincronizzati persistiti

## Core capabilities

Il layer `core` deve esporre operazioni canoniche di rebuild, ad esempio:

### Source facts

- `build_source_facts()`
- `rebuild_source_facts()`
- `rebuild_domain_facts(domain)`
- `rebuild_entity(entity_type, key)`

### Canonical states

- `build_canonical_states()`
- `rebuild_axis(axis_name)`
- `rebuild_states_from_facts(fact_ids)`

Queste operazioni sono indipendenti dai trigger di esecuzione.

## Separation of triggers

Come per il layer `sync`, anche nel `core`:

- le operazioni definiscono **cosa può essere fatto**
- i trigger definiscono **quando viene fatto**

Possibili trigger:

- dopo una sync completa
- dopo una sync incrementale
- manuale (debug, recovery)
- cambiamento di regole o logica
- bootstrap sistema

## Full rebuild capability

Il sistema deve sempre supportare:

> ricostruzione completa del layer `core` a partire dal solo layer `sync`

Questa capacità è fondamentale per:

- recovery da errori
- migrazioni
- modifiche di logica
- audit e validazione
- testing

## Partial rebuild capability

Il sistema deve supportare anche rebuild parziali:

- per dominio (es. ordini, articoli)
- per entità specifica
- per insieme di facts
- per asse operativo

Il rebuild parziale deve essere coerente con la dependency chain definita in DL-ARCH-005.

## Determinism principle

La ricostruzione del `core` deve essere:

- deterministica
- ripetibile
- indipendente dallo stato storico implicito

Formalmente:

> A parità di dati nel layer `sync`, il risultato del `core` deve essere identico.

## No hidden state

Il layer `core` non deve contenere:

- stato implicito non derivabile
- cache non ricostruibili
- logiche dipendenti da esecuzioni precedenti non tracciate

Ogni informazione nel `core` deve essere:

- derivabile dai source facts
- o derivabile dal layer `sync`

## Dependency-driven rebuild

Il rebuild del `core` deve essere guidato da:

- dependency mapping tra sync → facts
- dependency mapping tra facts → states

Questo consente:

- rebuild mirati
- ottimizzazione delle performance
- coerenza logica

## Relationship with SYNC

Il `core`:

- consuma dati dal layer `sync`
- non dipende dal momento della sync
- può essere ricostruito senza eseguire una nuova sync

Questo implica che:

> il layer `sync` rappresenta la base persistente su cui il `core` può essere rigenerato in qualsiasi momento.

## Consequences

### Positive consequences

- sistema completamente auditabile
- facilità di debug
- resilienza a errori
- facilità di evoluzione delle regole
- supporto naturale a test e simulazioni
- eliminazione di stati incoerenti

### Trade-offs

- necessità di progettare bene le operazioni di rebuild
- possibile aumento del costo computazionale
- necessità di gestire correttamente la granularità dei rebuild
- maggiore disciplina nella gestione dello stato

## What is intentionally not decided yet

- modalità di persistenza dei source facts (materializzati vs runtime)
- strategia di caching
- orchestrazione dei rebuild
- gestione della concorrenza
- eventuale uso di code/eventi

## Notes

Questo DL introduce un principio chiave:

> il `core` è un sistema rigenerabile, non uno stato accumulato.

Questo principio è fondamentale per garantire coerenza, robustezza e evolvibilità del sistema nel tempo.

Il `sync` rappresenta la memoria del mondo esterno.  
Il `core` rappresenta la verità interna, sempre ricostruibile.
