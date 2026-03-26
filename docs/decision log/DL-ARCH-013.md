# DL-ARCH-013.md  
## Data Persistence & Materialization Strategy

### Status  
Accepted

---

### Context

Il sistema MRS deve gestire:

- dati persistenti (Source Facts)
- derivazioni (Computed Facts)
- dataset operativi per algoritmi e servizi

Senza una strategia chiara si rischia:

- database sovraccarico
- duplicazione della logica
- incoerenza tra moduli
- perdita di semantica

È necessario distinguere tra:

- verità persistente
- derivazioni canoniche
- workspace temporaneo di calcolo

---

### Decision

Il sistema distingue tre livelli di materializzazione dei dati.

---

## 1. Persistent Canonical Data

Persistiti nel core:

- Source Facts  
- Computed Facts canonici  
- Canonical Operational States  
- Policy e override  
- Decision trace rilevante  

Questi rappresentano la **verità operativa del sistema**.

---

## 2. Computed Facts

I Computed Facts sono:

- derivati da Source Facts  
- deterministici  
- rigenerabili  

### Non sono persistiti per default

Diventano persistiti quando:

- sono condivisi tra moduli  
- guidano decisioni operative  
- sono esposti in UI/API  
- devono essere coerenti rispetto a uno snapshot  
- devono essere tracciabili  
- sono costosi da ricalcolare  

---

### Classificazione

#### Ephemeral
- solo in-memory  
- non persistiti  

#### Materialized (cache)
- persistiti opzionalmente  
- rigenerabili  

#### Canonical
- persistiti  
- parte del modello  

---

## 3. Projection / Working Sets

Le Projection sono:

> dataset temporanei costruiti dal core a partire dai dati persistiti, utilizzati per calcolo e servizi.

Caratteristiche:

- non persistite  
- costruite on-demand  
- deterministiche  
- prive di autonomia semantica  
- indipendenti dalla tecnologia  

---

### Architectural Rules

- I servizi NON accedono direttamente al database  
- Le Projection NON vengono mai persistite  
- Solo l’output può essere promosso a:
  - computed facts  
  - stati canonici  
  - decision trace  

---

### Principle

> Persisti il significato, non il workspace di calcolo.

---

### Consequences

#### Positive
- DB più leggero  
- semantica centralizzata  
- maggiore coerenza  
- supporto a rebuild  

#### Trade-offs
- necessità di classificazione  
- maggiore disciplina progettuale  

---

### Related Decisions

- DL-ARCH-007 (Computed Facts)  
- DL-ARCH-009 (Aggregate Roots)  
- DL-ARCH-011 (Policy System)  
