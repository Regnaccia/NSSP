# DL-ARCH-003 — Impostazione architetturale iniziale del layer SYNC

## Status
Accepted

## Context

L’architettura del sistema è stata suddivisa in layer distinti con responsabilità separate:

- `sync`: acquisizione e normalizzazione dei dati dai sistemi esterni
- `core`: elaborazione dei source facts e costruzione degli stati canonici operativi
- `app`: utilizzo applicativo dei dati elaborati

Con il consolidamento dei primi Decision Log architetturali e della prima visione dei source facts, emerge la necessità di fissare il ruolo del layer `sync` in modo più esplicito.

Il sistema dovrà riallinearsi ai dati provenienti da Easy in modo robusto, tracciabile e ricostruibile, evitando di introdurre nel layer `sync` logiche di business o interpretazioni operative che appartengono invece al `core`.

È inoltre emersa la possibilità di gestire la sincronizzazione secondo più modalità operative:

- sincronizzazione completa periodica
- sincronizzazione incrementale frequente
- sincronizzazioni richiamabili manualmente o da processi applicativi

## Decision

Il layer `sync` viene definito come un layer architetturale dedicato al **riallineamento dei dati esterni verso una base interna normalizzata**, tramite un insieme di **operazioni canoniche di sincronizzazione richiamabili**.

Il layer `sync` **non è definito dal suo trigger di attivazione**, ma dalla sua responsabilità architetturale: acquisire, normalizzare e riallineare dati provenienti da sistemi esterni senza applicare logica di business.

La strategia architetturale iniziale del layer `sync` prevede un modello ibrido basato su:

1. **full snapshot sync periodico**
   - usato come riallineamento globale del sistema
   - utile per garantire convergenza, sanare derive e recuperare eventuali mancate sincronizzazioni incrementali

2. **incremental sync frequente**
   - usato durante il giorno per ridurre la latenza operativa
   - destinato ad aggiornare solo i dati rilevati come variati

3. **sync richiamabile on demand**
   - utilizzabile da processi applicativi, operazioni manuali, bootstrap o recovery
   - concepito come parte nativa del layer, non come eccezione

## Architectural implications

Il layer `sync` deve essere progettato come insieme di primitive o operazioni canoniche, ad esempio:

- `full_sync`
- `incremental_sync`
- `sync_domain`
- `sync_entity`
- `reconcile_deleted_records`

I trigger di esecuzione (scheduler, chiamata manuale, eventuale watcher, trigger applicativo) sono considerati un livello separato rispetto alla definizione del layer.

Di conseguenza:

- il `sync` espone capacità di riallineamento
- i trigger decidono **quando** invocarle
- il `core` decide **come interpretare** i dati sincronizzati

## Responsibilities of the SYNC layer

Il layer `sync` è responsabile di:

- leggere dati dai sistemi esterni
- trasformarli in una forma interna coerente e normalizzata
- aggiornare la base dati del layer SYNC in modo tracciabile
- supportare riallineamenti completi e parziali
- predisporre dati affidabili per la costruzione dei source facts nel `core`

Il layer `sync` non è responsabile di:

- dedurre significati operativi
- costruire stati canonici di reparto
- prendere decisioni di business
- applicare logiche logistiche, produttive o di magazzino
- sostituirsi al `core` nell’interpretazione del dato

## Rationale

Questa scelta è adottata perché:

- separa chiaramente acquisizione dati e logica di business
- riduce il rischio di contaminare il layer `sync` con regole operative non stabili
- rende il sistema più ricostruibile, auditabile e testabile
- consente di partire con una soluzione semplice e robusta
- evita di vincolare l’architettura a un unico paradigma di attivazione
- permette evoluzioni future senza ridefinire il ruolo del layer

Il modello ibrido è preferito perché combina:

- **reattività operativa**, grazie all’incrementale frequente
- **robustezza sistemica**, grazie al full snapshot periodico
- **flessibilità applicativa**, grazie alle operazioni richiamabili on demand

## Consequences

### Positive consequences

- architettura più chiara e modulare
- migliore separazione delle responsabilità
- maggiore facilità di debug e recovery
- possibilità di aggiungere nuovi trigger senza modificare il significato del layer
- migliore supporto a source facts tracciabili e ricostruibili
- riduzione del rischio di dipendere da meccanismi di change detection ancora non confermati

### Trade-offs

- il modello richiede di progettare con cura il contratto delle operazioni di sync
- il full snapshot periodico introduce costo computazionale e di accesso dati
- l’incrementale richiederà una futura definizione tecnica precisa
- sarà necessario gestire in modo esplicito la riconciliazione delle cancellazioni o dei record non più presenti

## What is intentionally not decided yet

Questo DL non decide ancora:

- come l’incrementale rileva le variazioni reali
- se Easy supporta un vero modello event-driven o solo polling
- la granularità definitiva delle operazioni di sync per dominio o entità
- il dettaglio delle politiche di delete reconciliation
- la frequenza precisa degli scheduler
- il modello tecnico di orchestration dei job di sync
- i dettagli implementativi di logging, retry e fault handling

Questi aspetti saranno definiti in DL successivi o in documenti tecnici di implementazione.

## Notes

Questo DL fissa il ruolo architetturale del layer `sync`, non la sua implementazione definitiva.

La scelta chiave è che il `sync` venga trattato come **capability di riallineamento** e non come semplice watcher, scheduler o utility occasionale.