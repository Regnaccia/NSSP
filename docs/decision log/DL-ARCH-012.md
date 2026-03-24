# DL-ARCH-012 — Canonical Decision Trace & Explainability Model

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il sistema è fact-centric e costruisce Source Facts, Computed Facts e Canonical Operational States (DL-ARCH-002, DL-ARCH-007)
- il rebuild del core è deterministico e rigenerabile (DL-ARCH-005, DL-ARCH-006)
- i Computed Facts possono essere policy-driven e dipendono da policy esplicite (DL-ARCH-009)
- le policy sono governate da un modello esplicito con precedence e conflict resolution (DL-ARCH-011)
- gli aggregate root definiscono i confini di coerenza e rebuild (DL-ARCH-010)

Con DL-ARCH-011 è stato introdotto il concetto di **Policy Governance**, ma emerge una necessità fondamentale:

> il sistema deve essere in grado non solo di calcolare uno stato, ma di **spiegare in modo deterministico e auditabile perché quello stato è stato prodotto**.

In un contesto operativo reale (produzione, logistica, urgenze):

- l’operatore deve capire rapidamente il motivo di una decisione
- il sistema deve essere debuggabile a posteriori
- le decisioni devono essere auditabili (chi, quando, con quali policy)
- il comportamento deve essere riproducibile

Senza un modello esplicito di **Decision Trace**, il sistema rischia di diventare:

- corretto ma opaco
- difficile da debuggare
- non auditabile
- poco affidabile per decisioni critiche

---

## Decision

Il layer `core` introduce un modello canonico di:

> **Decision Trace & Explainability**

basato sui seguenti principi:

1. ogni Canonical Operational State rilevante deve poter generare una **Decision Trace**
2. la Decision Trace è un oggetto strutturato, non una stringa descrittiva
3. la Decision Trace è deterministica e rigenerabile a partire da facts e policy
4. la Decision Trace espone:
   - input rilevanti
   - trasformazioni
   - policy applicate
   - conflitti risolti
   - risultato finale
5. la Decision Trace è separata dalla projection (UI), ma utilizzabile dalla stessa
6. la Decision Trace è parte integrante del modello del core (non logging accessorio)

---

## Definitions

### Decision Trace

Una **Decision Trace** è la rappresentazione strutturata del processo logico che porta da:

```text
facts + policy set → computed facts → conflict resolution → operational state