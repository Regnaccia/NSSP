# DL-ARCH-014.md  
## Core vs Services Separation

### Status  
Accepted

---

### Context

Il sistema MRS introduce:

- un core semantico centralizzato  
- algoritmi complessi (scheduler, planner, simulazioni)  
- futura evoluzione verso servizi indipendenti  

Senza separazione chiara si rischia:

- core ingestibile  
- logica distribuita  
- forte coupling  
- difficoltà di evoluzione  

---

### Decision

Il sistema adotta una separazione tra:

> Core Semantico  
> Servizi / Funzioni di Calcolo  

---

## Core Responsibilities

Il core è responsabile di:

### Semantica
- Source Facts  
- Computed Facts canonici  
- Stati operativi  

### Integrità
- rebuild completo  
- rebuild mirato  
- gestione dipendenze  

### Governance
- policy base  
- override  
- validazione risultati  

### Orchestrazione
- costruzione projection  
- invocazione servizi  
- integrazione output  

---

## Core NON Responsibilities

Il core NON deve contenere:

- algoritmi complessi  
- scheduler avanzati  
- simulazioni multi-scenario  
- modelli AI  
- logiche iterative pesanti  

---

## Services / Functions

I servizi sono:

> componenti di calcolo specializzati che operano su projection fornite dal core.

---

### Interaction Model

1. Core costruisce projection  
2. Servizio elabora  
3. Servizio restituisce risultato  
4. Core decide cosa persistere  

---

### Rule

> I servizi non scrivono direttamente nel database.

---

## Modularity Principle

> Il core definisce il significato, i servizi eseguono il calcolo.

---

## Determinism

- Core → deterministico e rigenerabile  
- Servizi → possono essere non deterministici  

---

## Replaceability

I servizi devono essere:

- sostituibili  
- indipendenti dal database  
- basati su contratti  

---

## Deployment

I servizi possono evolvere da:

- moduli interni  
→ servizi separati  

senza modificare il core.

---

## Anti-Patterns

❌ Core con logica di scheduling  
❌ Servizi che accedono al DB  
❌ Servizi che scrivono dati  
❌ Logica duplicata  

---

## Benefits

- modularità  
- testabilità  
- evoluzione controllata  

---

## Trade-offs

- maggiore orchestrazione  
- necessità di contratti chiari  

---

### Related Decisions

- DL-ARCH-003 (Core vs Sync)  
- DL-ARCH-006 (Rebuildability)  
- DL-ARCH-013 (Data Strategy)  