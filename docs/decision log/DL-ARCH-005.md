# DL-ARCH-005 — Change propagation e dependency chain tra SYNC, Source Facts e Canonical States

## Status
Accepted

## Context

Nei DL architetturali precedenti è stato definito che:

- il layer `sync` è responsabile del riallineamento e della normalizzazione dei dati esterni
- il layer `core` costruisce i source facts canonici del sistema a partire dai dati sincronizzati
- gli stati canonici operativi sono derivati dai source facts
- il `sync` e il `core` devono essere modellati come layer rigenerabili tramite operazioni canoniche richiamabili
- il confine tra `sync` e `core` è esplicito e non coincide con la semplice pulizia tecnica del dato

Definito questo impianto, emerge la necessità di chiarire come propagare in modo governato i cambiamenti tra layer.

In particolare:

- quando il `sync` aggiorna dati esterni, il `core` deve poter sapere in modo chiaro cosa è cambiato
- quando cambiano source facts, deve essere possibile sapere quali stati canonici risultano impattati
- la propagazione dei cambiamenti non deve essere implicita, opaca o affidata a conoscenza dispersa nel codice

È quindi necessario definire un principio architetturale per la **change propagation** e per la **dependency chain** tra:

- dati sincronizzati
- source facts
- canonical operational states

## Decision

Il sistema adotta una propagazione dei cambiamenti basata su una **catena di dipendenze esplicita e monitorabile** tra layer.

### Principio generale

Il layer `sync` non comunica al `core` **cosa deve fare**, ma espone in modo strutturato **cosa è cambiato**.

Il layer `core` è responsabile di:

- interpretare i cambiamenti rilevati nel `sync`
- determinare quali source facts devono essere ricostruiti o aggiornati
- determinare quali canonical operational states dipendono dai facts modificati
- propagare il rebuild in modo totale o parziale

### Regola architetturale

La propagazione dei cambiamenti è articolata in tre livelli:

1. **SYNC → Source Facts**
   - il `sync` espone change sets strutturati
   - il `core` usa tali change sets per individuare i source facts impattati

2. **Source Facts → Canonical Operational States**
   - il `core` definisce in modo esplicito quali stati dipendono da quali facts

3. **Canonical States → Projections / App views**
   - i livelli applicativi leggono o rigenerano le proiezioni a partire dagli stati canonici aggiornati

## Architectural principle

Il sistema non deve basarsi su osservazione implicita del database o su coupling accidentale tra moduli.

Deve invece basarsi su:

- **change contracts espliciti**
- **dependency mapping espliciti**
- **rebuild governati**
- **possibilità di full rebuild come convergenza e recovery**

## SYNC responsibilities in change propagation

Il layer `sync` deve esporre un risultato strutturato delle proprie operazioni, ad esempio sotto forma di **change set**.

Il change set deve rappresentare almeno:

- identificativo del run o batch
- scope dell’operazione
- entità o domini toccati
- chiavi toccate
- tipo di variazione:
  - inserted
  - updated
  - deleted
- timestamp del cambiamento rilevato o del run

Il `sync` può quindi dichiarare:

- quali record sono stati modificati
- quali record sono nuovi
- quali record non risultano più presenti

Il `sync` non deve invece dichiarare:

- quali facts o stati interni devono essere ricalcolati
- quali logiche di business risultano impattate
- quali decisioni operative devono essere prese

## CORE responsibilities in change propagation

Il layer `core` deve possedere una dependency chain esplicita tra:

- entità del layer `sync`
- source facts
- canonical operational states

Il `core` è responsabile di:

- mappare i cambiamenti sync verso i facts dipendenti
- mappare i facts modificati verso gli stati dipendenti
- decidere il perimetro del rebuild:
  - totale
  - parziale
  - mirato per dominio
  - mirato per entità

## Dependency chain model

### Level 1 — Sync entity to Source Fact

Esempi:

- `sync_order_line` → `OrderLine`
- `sync_order_header` → `Order`
- `sync_customer` → `Customer`
- `sync_destination` → `Destination`

### Level 2 — Source Fact to Canonical State

Esempi:

- `OrderLine` → `FulfillmentLineState`
- `Order` → `OrderFulfillmentState`
- `Article` + `Stock` + `Commitments` → `ArticleAvailabilityState`

### Level 3 — Canonical State to Projection

Esempi:

- `OrderFulfillmentState` → vista logistica ordini aperti
- `ArticleAvailabilityState` → fabbisogno digitale
- `ShippingPreparationState` → dashboard magazzino

## Guiding rules

### Rule 1
Il `sync` espone cambiamenti fattuali della sorgente, non istruzioni di business.

### Rule 2
Il `core` possiede la conoscenza semantica delle dipendenze.

### Rule 3
Ogni rebuild parziale deve poter essere spiegato da una chain di dipendenze leggibile.

### Rule 4
Ogni livello deve poter essere ricostruito integralmente in caso di recovery, convergenza o modifica delle regole.

### Rule 5
La propagazione dei cambiamenti deve essere governata da mapping espliciti, non da side effects impliciti.

## Example

Caso: una riga ordine viene aggiornata nel sistema sorgente.

### Step 1 — Sync
Il layer `sync` aggiorna il record corrispondente e produce un change set del tipo:

- entity type: `sync_order_line`
- change kind: `updated`
- changed key: `[order_line_id]`

### Step 2 — Core facts
Il `core` legge la dependency chain e determina che devono essere ricostruiti:

- `OrderLine`
- eventualmente `Order`, se il modello lo richiede

### Step 3 — Core states
Il `core` legge la dependency chain facts → states e determina che devono essere aggiornati:

- `FulfillmentLineState`
- `OrderFulfillmentState`
- eventuali altri stati collegati

### Step 4 — Projections
Le viste applicative che dipendono da tali stati vengono aggiornate o rigenerate.

## Consequences

### Positive consequences

- propagazione dei cambiamenti comprensibile e auditabile
- minore accoppiamento tra `sync` e `core`
- maggiore controllabilità dei rebuild parziali
- minore rischio di inconsistenze logiche
- migliore base per logging, monitoring e debugging
- possibilità di ottimizzare i ricalcoli senza perdere rigore architetturale

### Trade-offs

- necessità di modellare e mantenere dependency maps esplicite
- maggiore disciplina architetturale richiesta
- possibile aumento iniziale della complessità progettuale
- necessità futura di definire bene granularità e priorità dei rebuild

## What is intentionally not decided yet

Questo DL non definisce ancora:

- formato tecnico definitivo dei change sets
- meccanismo concreto di orchestration
- tecnologia di messaging/eventing eventualmente usata
- struttura dati concreta del dependency graph
- strategia di execution scheduling dei rebuild
- livello di sincronicità o asincronicità della propagazione

Questi aspetti saranno definiti in documenti successivi.

## Notes

Questo DL fissa un principio architetturale fondamentale:

> il `sync` espone cambiamenti strutturati;  
> il `core` possiede la logica di dipendenza e ricostruzione.

La propagazione dei cambiamenti non è implicita, ma parte del modello architetturale del sistema.