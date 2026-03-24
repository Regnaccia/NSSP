# DL-ARCH-009 — Distinzione tra Computed Facts meccanici e policy-driven

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il layer `core` costruisce i **Source Facts** canonici del sistema (DL-ARCH-002)
- i Source Facts possono avere origine:
  - da sistemi esterni (external-derived)
  - da input nativi MRS (native facts) (DL-ARCH-008)
- il modello del core include un livello intermedio di **Computed Facts** (DL-ARCH-007)
- i Computed Facts sono:
  - derivati dai Source Facts
  - deterministici
  - riusabili
  - distinti dagli Operational States

Durante l’analisi di casi operativi complessi emerge che non tutti i Computed Facts sono omogenei.

In particolare, esistono due categorie distinte:

- Computed Facts derivati esclusivamente da relazioni matematiche o logiche dirette tra facts
- Computed Facts che richiedono l’applicazione di una **policy operativa** (es. priorità, allocazione, soglie)

Questa distinzione è fondamentale per:

- mantenere chiarezza semantica
- evitare ambiguità tra dato e decisione
- garantire rigenerabilità e controllabilità del sistema

---

## Decision

I Computed Facts vengono distinti in due categorie:

> **Mechanical Computed Facts**  
> **Policy-driven Computed Facts**

Entrambe le categorie:

- appartengono al layer `core`
- sono derivazioni dai Source Facts
- sono rigenerabili
- non rappresentano stati operativi

Tuttavia differiscono per:

- natura della derivazione
- dipendenza da logiche di business
- stabilità nel tempo

---

## Definitions

### Mechanical Computed Facts

Computed Facts derivati esclusivamente da relazioni deterministiche dirette tra Source Facts.

Caratteristiche:

- derivazione puramente matematica o logica
- indipendenti da decisioni operative
- invarianti rispetto al contesto di utilizzo
- completamente stabili nel tempo
- non dipendono da configurazioni o policy

Esempi:

- `qty_remaining = qty_ordered - qty_shipped`
- `qty_unpacked = qty_shipped - qty_packed`
- `total_open_demand = somma qty_remaining`
- `produced_not_posted_qty = somma eventi produzione completati`

---

### Policy-driven Computed Facts

Computed Facts derivati applicando una o più **policy operative** ai Source Facts (e/o ai Mechanical Computed Facts).

Caratteristiche:

- richiedono una regola o strategia definita dal sistema
- dipendono da configurazioni o scelte operative
- possono cambiare nel tempo al variare delle policy
- possono avere più versioni (diverse strategie)
- non rappresentano ancora uno stato operativo, ma preparano la decisione

Esempi:

- allocazione stock su righe ordine (FIFO, urgenza-first, priorità cliente)
- `qty_covered_now`
- `qty_coverable_soon`
- `operational_available_qty`
- quantità pesata da probabilità di completamento produzione
- simulazioni di copertura domanda-offerta

---

## Key Distinction

La differenza fondamentale è:

> Mechanical Computed Facts rispondono a “quanto è”,  
> Policy-driven Computed Facts rispondono a “quanto sarebbe disponibile secondo una regola”.

---

## Relationship with Operational States

Gli Operational States:

- NON devono contenere logiche numeriche complesse
- devono basarsi preferibilmente su:
  - Mechanical Computed Facts
  - Policy-driven Computed Facts

Esempio:

```text
AvailabilityState:
- usa qty_remaining (mechanical)
- usa qty_coverable_now (policy-driven)
→ determina AVAILABLE / PARTIAL / NOT_AVAILABLE