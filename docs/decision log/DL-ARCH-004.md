# DL-ARCH-004 — Confine tra SYNC storage e CORE source facts

## Status
Accepted

## Context

L’architettura del sistema è suddivisa in layer distinti:

- `sync`: acquisizione e normalizzazione dei dati dai sistemi esterni
- `core`: costruzione dei source facts e degli stati canonici operativi
- `app`: utilizzo applicativo

Nei DL precedenti è stato definito che:

- il layer `sync` è responsabile del riallineamento e della normalizzazione dei dati, senza logica di business (DL-ARCH-003)
- i source facts del `core` sono derivati dal layer `sync`, tracciabili e ricostruibili (DL-ARCH-002)

Rimane da definire in modo esplicito il **confine semantico e funzionale** tra:

- dati persistiti nel layer `sync`
- dati considerati source facts nel layer `core`

Questo confine è critico per evitare:
- contaminazione del `sync` con logica di business
- dipendenza eccessiva del `core` dalla struttura del sistema sorgente
- ambiguità nella definizione dei source facts

## Decision

Il confine tra `SYNC storage` e `CORE source facts` è definito come segue:

> Il layer `sync` conserva dati esterni riallineati e normalizzati, ancora orientati alla sorgente.  
> Il layer `core` costruisce da essi i source facts canonici del sistema, orientati al dominio interno.

Il passaggio da `sync` a `core` **non coincide con la semplice pulizia tecnica del dato**, ma con la sua **canonizzazione semantica nel modello interno**.

### SYNC storage

Il layer `sync` contiene:

- dati provenienti da sistemi esterni (es. Easy)
- strutture dati ancora legate alla semantica della sorgente
- normalizzazioni tecniche necessarie a rendere il dato coerente e utilizzabile
- metadata di sincronizzazione e provenienza

Nel layer `sync` è ammessa:

- pulizia e tipizzazione dei dati
- rinomina campi
- join tecnici necessari a ricostruire record leggibili
- ricostruzione di record frammentati dovuti a limiti tecnici della sorgente

Esempio:
- ricomposizione della descrizione di una riga ordine a partire da più righe generate da limiti di lunghezza

Nel layer `sync` **non è ammessa**:

- logica di business
- interpretazione operativa del dato
- costruzione di stati (es. pronto, urgente, spedibile)
- deduzione di significati di dominio non espliciti nella sorgente

### CORE source facts

Il layer `core` contiene:

- entità canoniche del dominio interno (cliente, ordine, riga ordine, articolo, ecc.)
- fatti considerati base condivisa del sistema
- strutture indipendenti (per quanto possibile) dalla forma del sistema sorgente

Nel layer `core` è ammessa:

- canonizzazione del dato
- definizione di identità interne stabili
- costruzione di relazioni tra entità
- interpretazione minima necessaria a definire un fatto coerente

Esempio:
- trasformare una riga ordine sincronizzata in una entità `OrderLine` canonica
- associare in modo stabile cliente, destinazione e articolo

Il layer `core` non deve contenere:

- dettagli tecnici della rappresentazione della sorgente (es. righe di continuazione)
- artefatti di memorizzazione del sistema esterno

## Guiding principles

### 1. Source-oriented vs Domain-oriented

- `sync` → orientato alla sorgente
- `core` → orientato al dominio

### 2. Normalization vs Canonization

- `sync` → normalizzazione tecnica
- `core` → canonizzazione semantica

### 3. Representation vs Meaning

- `sync` → rappresentazione fedele e pulita del dato esterno
- `core` → significato del dato per il sistema

### 4. External dependency vs Internal stability

- `sync` → dipendente dalla struttura di Easy
- `core` → stabile rispetto a cambiamenti della sorgente (per quanto possibile)

## Practical classification rules

Per decidere dove collocare una trasformazione o un dato:

### Rule 1
Se la trasformazione serve a ricostruire un record coerente a partire da limiti tecnici della sorgente → `sync`

### Rule 2
Se il dato cambierebbe direttamente al cambiare della struttura del sistema esterno → `sync`

### Rule 3
Se il dato rappresenta un concetto stabile necessario al sistema per operare → `core`

### Rule 4
Se si sta assegnando un significato canonico al dato → `core`

### Rule 5
Se si stanno introducendo stati operativi o decisionali → non è né `sync` né source fact, ma livello successivo del `core`

## Example — Order line description reconstruction

Nel sistema sorgente, una descrizione lunga può essere suddivisa su più righe per limiti tecnici.

Decisione:

- la ricostruzione della descrizione completa è responsabilità del layer `sync`
- il `core` utilizza la descrizione già ricomposta come attributo del source fact `OrderLine`

Motivazione:

- la suddivisione in più righe è un artefatto tecnico della sorgente
- la ricostruzione è una normalizzazione, non una interpretazione di business

## Architectural implications

- il `core` non deve dipendere direttamente dalla struttura fisica delle tabelle del `sync`
- deve esistere un passaggio esplicito di trasformazione da dati sincronizzati a source facts
- il `sync` deve assorbire le anomalie e i limiti di rappresentazione della sorgente
- il `core` deve lavorare su entità pulite, coerenti e semanticamente stabili

## Consequences

### Positive consequences

- separazione netta delle responsabilità
- maggiore robustezza rispetto a cambiamenti del sistema sorgente
- migliore leggibilità e mantenibilità del modello dati
- riduzione del rischio di inserire business logic nel layer sbagliato
- base più solida per i canonical operational states

### Trade-offs

- necessità di introdurre un passaggio esplicito tra sync e core
- possibile duplicazione controllata dei dati tra layer
- maggiore disciplina progettuale richiesta

## What is intentionally not decided yet

- modello tecnico di persistenza (tabelle, viste, materializzazioni)
- modalità di implementazione del passaggio sync → core
- strumenti utilizzati (ORM, ETL, pipeline)
- granularità definitiva delle entità canoniche

## Notes

Questo DL stabilisce un principio architetturale fondamentale:  
il sistema deve distinguere tra “dato proveniente dalla sorgente” e “fatto canonico interno”.

Il layer `sync` assorbe la complessità della sorgente.  
Il layer `core` definisce la realtà del sistema.