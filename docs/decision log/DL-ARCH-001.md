# DL-ARCH-001 — Impostazione architetturale iniziale di MRS OMR

## Stato
Approvato (provvisorio)

## Data
2026-03-23

---

## Contesto

Il progetto MRS OMR ha l’obiettivo di digitalizzare e orchestrare il flusso operativo aziendale che parte dall’ordine cliente e attraversa:

- commerciale
- produzione
- magazzino
- logistica

fino alla spedizione.

L’attuale processo è caratterizzato da:
- passaggi manuali
- gestione distribuita delle informazioni
- interscambio fisico (es. fabbisogno cartaceo)
- decisioni operative non formalizzate

È quindi necessario costruire una base architetturale che consenta di:
- integrare i dati provenienti dal gestionale esterno
- trasformarli in informazione operativa strutturata
- supportare i reparti con viste e strumenti dedicati
- preparare il sistema per evoluzioni future (automazioni avanzate e AI)

---

## Decisione

L’architettura iniziale del sistema viene organizzata in **tre layer principali**:

### 1. `sync`
Responsabile dell’acquisizione e normalizzazione dei dati da sistemi esterni (es. EasyJob).

### 2. `core`
Responsabile della trasformazione dei dati sincronizzati in entità operative e logica di business del sistema.

### 3. `app`
Responsabile dell’esposizione delle informazioni e delle azioni utente tramite interfacce per reparto o funzione.

---

## Decisione sul `core`

Il layer `core` **non viene strutturato per reparto aziendale**, ma secondo una logica **domain-driven**.

La suddivisione interna del `core`:
- **non è ancora fissata**
- verrà definita in base alle entità e ai domini operativi reali del sistema

---

## Motivazioni

### Separazione dei livelli
Separare `sync`, `core` e `app` consente di:
- isolare il gestionale esterno dalla logica interna
- evitare accoppiamento tra dati sorgente e comportamento del sistema
- mantenere il controllo sulla trasformazione dei dati

### Centralità del `core`
Il `core` rappresenta il cuore del sistema e deve:
- costruire il fabbisogno digitale
- determinare lo stato operativo degli ordini
- gestire produzione, disponibilità e spedizioni
- formalizzare le regole oggi implicite

### Approccio domain-driven
Molti oggetti del sistema sono trasversali ai reparti:
- fabbisogno
- stato ordine
- approntamento
- spedizione
- urgenze

Una divisione per reparto porterebbe a:
- duplicazione logica
- incoerenze tra moduli
- difficoltà di manutenzione

Un approccio per domini permette invece:
- una singola fonte di verità per ogni oggetto
- gestione coerente delle interazioni tra reparti
- maggiore scalabilità del sistema

---

## Conseguenze

### Positive
- architettura chiara e modulare
- separazione delle responsabilità
- maggiore manutenibilità
- base solida per MVP per reparto
- preparazione per future integrazioni AI

### Negative / Trade-off
- richiede analisi accurata delle entità prima di implementare
- la struttura interna del `core` resta temporaneamente aperta
- maggiore investimento iniziale nella modellazione

---

## Vincoli

1. `sync` non deve contenere logica di business operativa
2. `core` è l’unica fonte di verità per la logica MRS
3. `app` non deve contenere logica di processo
4. la struttura del `core` deve emergere dalle entità e non dall’organigramma
5. il fabbisogno digitale è considerato concetto centrale del sistema

---

## Decisioni rinviate

Da definire nelle fasi successive:

- elenco completo delle entità del sistema
- distinzione tra dati sincronizzati e dati derivati
- suddivisione definitiva del `core` in domini
- modalità di aggiornamento (event-driven, batch, manuale)
- struttura tecnica dei moduli backend

---

## Prossimi passi

Analisi delle entità del sistema:

- ordine
- riga ordine
- cliente
- destinazione
- articolo
- fabbisogno digitale
- commessa di produzione
- disponibilità magazzino
- approntamento
- piano spedizione
- urgenza
- DDT
- corriere

Per ciascuna entità:
- classificazione (`sync` vs `core`)
- responsabilità
- relazioni
- stato e ciclo di vita

---

## Note

Questo documento definisce la base architetturale del sistema e deve essere considerato riferimento per le decisioni successive fino a revisione formale.