# DL-ARCH-002 — Core Model: Fact-Centric & Multi-Axis Operational States

## Status

Proposed

## Context

Il sistema nasce per supportare il **customer demand fulfillment** a partire da dati provenienti dal gestionale EasyJob.

L’analisi del fabbisogno cartaceo ha evidenziato che:

* rappresenta una **vista decisionale statica**
* combina dati sorgente (ordini, articoli, giacenze) con interpretazioni implicite
* non è adatto come **fonte di verità primaria**

Durante il design del core è emersa la necessità di:

* separare chiaramente **dati sorgente** e **stati derivati**
* evitare modelli sbilanciati (solo order-centric o solo article-centric)
* supportare più reparti (logistica, magazzino, produzione) con esigenze diverse
* mantenere coerenza, auditabilità ed estendibilità del sistema

---

## Decision

Il core del sistema viene strutturato secondo un modello **fact-centric con stati operativi multi-asse**.

### 1. Source Facts (Base Canonica)

Il sistema definisce un insieme di **source facts normalizzati** come fondazione unica e condivisa.

Caratteristiche:

* derivati dal layer SYNC (EasyJob)
* tracciabili alla sorgente
* non interpretati o minimamente interpretati
* ricostruibili

Esempi:

* Cliente
* Destinazione
* Articolo
* Ordine
* Riga Ordine
* Quantità (ordinate, evase, residue)
* Stock / Giacenze
* Impegni
* Produzione (WIP)

I source facts costituiscono la **fonte di verità primaria interna**.

---

### 2. Canonical Operational States (Multi-Axis)

Il core costruisce uno o più **stati operativi canonici**, ciascuno relativo a un **asse operativo del sistema**.

Caratteristiche:

* derivati dai source facts
* semanticamente stabili
* condivisibili tra più use case
* persistibili (se necessario)
* rigenerabili

Ogni stato appartiene a un **asse canonico** (axis), ad esempio:

* fulfillment axis
* article axis
* (altri assi futuri)

Nota:
La definizione degli assi canonici **non è fissata in questo documento** e verrà trattata in DL successivi.

---

### 3. Department Projections

Le applicazioni e le interfacce di reparto (logistica, magazzino, produzione, ecc.) **non accedono direttamente ai source facts**, ma consumano:

* uno o più canonical operational states
* eventuali aggregazioni o viste specifiche

Caratteristiche:

* adattate allo scopo operativo del reparto
* non introducono nuova verità
* non duplicano logica già presente nei canonical states

---

### 4. Separation of Concerns

Il sistema è esplicitamente suddiviso in tre livelli:

* Source Facts → cosa il sistema sa
* Canonical Operational States → cosa il sistema conclude
* Projections → cosa il reparto deve vedere/fare

---

## Architectural Principles

1. **Fact-Centric Core**

   * Il sistema è centrato sui fatti, non sulle viste.

2. **No Single Dominant Axis**

   * Nessun asse (ordine, articolo, ecc.) domina l’intero modello.

3. **Multi-Axis Operational Modeling**

   * Gli stati operativi sono organizzati per assi indipendenti.

4. **Derived ≠ Source of Truth**

   * Gli stati derivati non sono fonte primaria di verità.

5. **Controlled Canonical Layer**

   * I canonical states devono essere pochi, governati e ben definiti.

6. **Projection Simplicity**

   * Le viste applicative non devono reimplementare logica di dominio.

---

## Consequences

### Positive

* Elevata coerenza semantica
* Separazione chiara tra dati e interpretazione
* Supporto naturale a più reparti
* Estendibilità futura (nuovi assi)
* Migliore auditabilità e debug

### Negative / Risks

* Necessità di governance forte sui canonical states
* Possibile complessità iniziale maggiore
* Rischio proliferazione di stati derivati se non controllato

---

## Open Points

* Definizione degli assi canonici iniziali (es. fulfillment, article)
* Identificazione dei primi canonical operational states
* Politica di persistenza vs calcolo runtime
* Strategia di aggiornamento (snapshot vs event-driven)

---

## Notes

Questo DL non sostituisce DL-ARCH-001 ma ne estende il modello logico interno al CORE.

Il fabbisogno digitale viene considerato una **projection del fulfillment axis**, non una fonte di verità primaria.
