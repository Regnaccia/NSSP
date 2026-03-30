# IMPLEMENTATION V0.1 — SYNC LAYER

## Obiettivo

La milestone **v0.1** ha lo scopo di implementare il primo layer reale del sistema: il **Sync Layer**.

Questa fase serve a costruire un componente in grado di:

- leggere dati dal sistema esterno di riferimento
- normalizzarli in uno storage locale controllato
- rendere osservabile ogni esecuzione di sincronizzazione
- produrre un output strutturato dei cambiamenti rilevati
- fungere da base affidabile per il successivo layer `core`

Questa milestone **non** deve ancora costruire `Source Facts`, `Computed Facts`, `States` o `Projection`.

Il focus esclusivo è:

> acquisire, versionare logicamente e rendere confrontabili i dati esterni in modo consistente e monitorabile.

---

## Ruolo del Sync Layer nell’architettura

Il Sync Layer è il punto di contatto tra:

- **sistema esterno / source system**
- **modello interno MRS**

Il suo compito **non** è interpretare il significato operativo del dato, ma:

- acquisirlo
- ripulirlo nei limiti necessari
- normalizzarlo
- confrontarlo con lo stato locale precedente
- dichiarare cosa è cambiato

In termini architetturali:

- il `sync` **conosce il sistema esterno**
- il `core` **non conosce il sistema esterno**
- il `sync` **non decide**
- il `sync` **non costruisce stati operativi**
- il `sync` **non applica policy aziendali**

Il Sync Layer produce un contratto tecnico verso il `core`:

- dataset locale coerente
- metadati di sincronizzazione
- change set osservabile

---

## Finalità della milestone v0.1

La milestone deve validare in particolare:

1. la possibilità di leggere dati reali dal sistema esterno
2. la qualità delle chiavi identificative disponibili
3. la sostenibilità del mapping verso tabelle `sync_*`
4. la possibilità di rilevare cambiamenti in modo consistente
5. la separazione netta tra acquisizione tecnica e interpretazione di dominio

---

## Perimetro della milestone

La milestone v0.1 deve restare **contenuta**.

L’obiettivo non è sincronizzare “tutto il gestionale”, ma costruire il primo slice reale e architetturalmente corretto.

### Dominio iniziale suggerito

Per questa prima implementazione il perimetro consigliato è:

- ordini
- righe ordine
- articoli
- disponibilità / stock / movimenti, a seconda della sorgente più praticabile

La selezione concreta delle entità può variare, ma la milestone deve includere almeno:

- una entità di livello documento
- una entità di dettaglio/riga
- una entità anagrafica/articolo
- una entità utile a testare disponibilità o copertura futura

---

## Responsabilità del Sync Layer

Il Sync Layer, in v0.1, deve avere le seguenti responsabilità.

### 1. Acquisizione
Recuperare dati dal sistema sorgente tramite un canale tecnico definito.

Esempi possibili:
- query DB diretta
- lettura da vista/materialized view
- estrazione batch
- API esterna, se presente

La scelta tecnica concreta non è oggetto di questo documento, purché il risultato sia equivalente:
un dataset leggibile e ripetibile.

### 2. Normalizzazione locale
Persistire i dati acquisiti in uno storage locale interno, con struttura controllata dal progetto.

Questa persistenza locale serve a:
- disaccoppiare il `core` dalla sorgente esterna
- permettere confronti tra snapshot o run successive
- consentire rebuild e analisi offline
- migliorare osservabilità e debugging

### 3. Tracciamento delle run
Ogni esecuzione di sync deve essere registrata come evento esplicito.

Il sistema deve poter rispondere a domande come:
- quando è partita una sync
- quando è terminata
- se è riuscita o fallita
- quali entità ha processato
- quanti record ha letto
- quanti record ha inserito/aggiornato/eliminato
- se ha prodotto anomalie

### 4. Rilevazione dei cambiamenti
La sync deve dichiarare in modo strutturato cosa è cambiato rispetto allo stato locale precedente.

Questa capacità è fondamentale perché il `core` dovrà poi decidere cosa rigenerare.

### 5. Osservabilità tecnica
Il layer deve generare output sufficienti per:
- audit tecnico
- debug
- futura propagazione verso il `core`

---

## Non responsabilità del Sync Layer

Per evitare contaminazioni architetturali, in v0.1 il Sync Layer **non deve**:

- ricostruire concetti canonici di dominio
- generare `Source Facts`
- unire entità in aggregate di business
- calcolare stati operativi
- applicare policy decisionali
- allocare stock
- determinare urgenze, coperture o priorità
- esporre logica orientata alla UI

Può fare solo la minima normalizzazione tecnica necessaria a rendere i dati coerenti e confrontabili.

---

## Principi architetturali della milestone

### 1. Source-aware, domain-agnostic
Il Sync Layer conosce la sorgente esterna ma deve restare il più possibile neutro rispetto alla logica di business interna.

### 2. Idempotenza pratica
Ripetere una sync senza modifiche nella sorgente non deve produrre cambiamenti logici non necessari nel layer locale.

### 3. Determinismo
A parità di dati sorgente, il risultato della sync deve essere coerente e ripetibile.

### 4. Tracciabilità
Ogni record sincronizzato deve poter essere ricondotto alla sua origine tecnica.

### 5. Minimizzazione dell’interpretazione
Il Sync Layer può normalizzare, ma non deve “inventare” semantica di dominio.

### 6. Contract-first verso il core
Il vero output della sync non è solo la tabella locale, ma il contratto implicito:
- quali record esistono
- quali record sono cambiati
- con quali identificativi
- in quale run

---

## Componenti concettuali di v0.1

La milestone può essere pensata come composta da questi blocchi logici.

### 1. Source Connector
Componente incaricato di leggere i dati dal sistema esterno.

Responsabilità:
- apertura connessione
- esecuzione query / fetch
- gestione errori tecnici
- restituzione dataset grezzo leggibile dal sync processor

### 2. Sync Extractor / Loader
Componente incaricato di trasferire il dataset sorgente nel layer locale.

Responsabilità:
- adattare i campi minimi necessari
- allineare il formato
- caricare nello storage locale

### 3. Sync Storage
Storage locale controllato dal progetto.

Contiene:
- tabelle o collezioni `sync_*`
- log delle esecuzioni
- eventuale change set persistito
- metadati utili al debugging

### 4. Change Detector
Componente incaricato di confrontare:
- stato locale precedente
- stato importato corrente

e produrre un risultato strutturato del differenziale.

### 5. Sync Run Tracker
Componente incaricato di registrare:
- inizio run
- fine run
- outcome
- metriche
- errori / warning
- riferimenti ai blocchi processati

---

## Struttura concettuale dello storage sync

Il dettaglio fisico verrà deciso in implementazione, ma concettualmente il layer locale deve includere almeno tre famiglie di dati.

### A. Dati sincronizzati
Entità locali `sync_*` che rappresentano copie controllate e normalizzate del dato esterno.

Esempi astratti:
- `sync_document`
- `sync_document_line`
- `sync_article`
- `sync_inventory`

### B. Metadati di esecuzione
Entità che descrivono ogni run di sincronizzazione.

Esempi astratti:
- `sync_run`
- `sync_run_entity`
- `sync_run_issue`

### C. Risultati di confronto
Entità o strutture che rappresentano i cambiamenti rilevati.

Esempi astratti:
- `sync_change_set`
- `sync_change_item`

Non è obbligatorio che siano tabelle separate fin da subito, ma il concetto deve esistere.

---

## Modello concettuale di `sync_run`

Ogni esecuzione deve essere trattata come una unità osservabile autonoma.

### Una `sync_run` dovrebbe poter descrivere almeno:
- identificativo univoco run
- timestamp avvio
- timestamp fine
- stato finale
- sorgente elaborata
- perimetro elaborato
- quantità record letti
- quantità record inseriti
- quantità record aggiornati
- quantità record eliminati
- warning
- errori
- note diagnostiche opzionali

### Stati minimi suggeriti della run
- `STARTED`
- `COMPLETED`
- `FAILED`
- `COMPLETED_WITH_WARNINGS`

---

## Modello concettuale di Change Set

Il Change Set è uno degli output più importanti di v0.1.

Non è ancora una richiesta di rebuild verso il core, ma una dichiarazione tecnica dei cambiamenti rilevati.

### Il Change Set deve poter esprimere almeno:
- entità coinvolta
- identificativo record locale
- identificativo record sorgente
- tipo di cambiamento
- run che ha prodotto il cambiamento

### Tipologie minime di cambiamento
- `INSERTED`
- `UPDATED`
- `DELETED`

### Tipologie opzionali utili
- `UNCHANGED`
- `RESTORED`
- `SOFT_DELETED`
- `TECHNICALLY_CHANGED_BUT_BUSINESS_EQUIVALENT`

Le tipologie opzionali non sono necessarie in v0.1, ma è utile tenere aperta la struttura.

---

## Logica di rilevazione cambiamenti

Il documento non impone una tecnica unica, ma la rilevazione deve essere coerente.

Approcci possibili:
- confronto campo per campo
- hash tecnico della riga normalizzata
- confronto snapshot precedente vs corrente
- timestamp sorgente, se affidabile
- combinazione dei precedenti

### Requisito architetturale
La tecnica scelta deve rendere possibile distinguere almeno:
- nuovo record
- record modificato
- record non più presente

### Nota importante
La nozione di “modificato” in v0.1 è ancora tecnica, non semantica di business.

Esempio:
- cambia un campo descrittivo secondario → per il sync è un `UPDATED`
- sarà il core, in futuro, a decidere se quel change impatta o meno i facts

---

## Chiavi e identità

Uno dei punti principali da validare in v0.1 è la qualità delle chiavi.

Per ogni entità sincronizzata bisogna distinguere concettualmente:

### 1. Source Identity
Identificativo con cui il sistema esterno individua il record.

### 2. Local Sync Identity
Identificativo con cui il layer locale traccia il record sincronizzato.

### 3. Stable Business Reference
Riferimento che potrebbe essere usato in futuro dal core per costruire facts canonici.

Queste tre nozioni possono coincidere oppure no.  
La milestone serve anche a capire se coincidono davvero o se vanno separate.

---

## Grado di normalizzazione consentito nel Sync Layer

Il Sync Layer può introdurre alcune normalizzazioni tecniche, ma con prudenza.

### Consentito
- uniformare tipi
- rinominare campi tecnici nel layer locale
- separare metadati di run dai dati di business raw
- pulire valori nulli / formati incoerenti se necessario a fini tecnici
- preservare riferimenti tra header e linee

### Da trattare con cautela
- ricostruzioni complesse multi-record
- deduzioni non esplicite nella sorgente
- fusioni semantiche di più record
- classificazioni di business

### Non consentito in v0.1
- trasformare già il dato in `Source Facts`
- attribuire stati canonici
- applicare regole decisionali

---

## Modalità di esecuzione della sync

In v0.1 è sufficiente una esecuzione manuale o on-demand.

### Modalità minima richiesta
- comando esplicito lanciabile da sviluppo / test

### Modalità future possibili
- schedulazione periodica
- trigger applicativi
- sync perimetralizzata per entità o subset
- refresh forzato

Queste modalità future non devono essere implementate ora, ma la struttura v0.1 non deve precluderle.

---

## Scope operativo della prima sync

Per evitare dispersione, la prima sync deve rispettare alcuni limiti.

### La v0.1 deve essere:
- reale
- utile
- osservabile
- piccola

### La v0.1 non deve essere:
- completa su tutto il gestionale
- ottimizzata al massimo
- già pronta per produzione
- accoppiata al core

---

## Output attesi di v0.1

A fine milestone, il sistema deve essere in grado di produrre in modo affidabile almeno i seguenti output.

### 1. Dataset locale sync consistente
Una copia locale leggibile e interrogabile del subset sorgente scelto.

### 2. Storico delle run
Una vista affidabile delle sincronizzazioni eseguite.

### 3. Change Set strutturato
Un risultato chiaro dei cambiamenti rilevati.

### 4. Diagnostica minima
Capacità di capire:
- cosa è stato sincronizzato
- cosa è fallito
- cosa è cambiato
- con quale run

---

## Test architetturali attesi

La milestone deve essere valutata anche come test del modello.

### Test 1 — Connettività reale
Verificare che l’accesso al sistema sorgente sia robusto abbastanza da supportare la roadmap.

### Test 2 — Stabilità chiavi
Verificare se gli identificativi disponibili sono davvero stabili e sufficienti.

### Test 3 — Coerenza differenziale
Verificare che il change detector non produca rumore eccessivo.

### Test 4 — Separazione dei layer
Verificare che nessuna logica da `core` stia entrando impropriamente nel `sync`.

### Test 5 — Qualità osservabilità
Verificare se una run problematica può essere compresa e diagnosticata facilmente.

---

## Criteri di successo della milestone

La milestone v0.1 è da considerarsi riuscita se:

1. il sistema legge dati reali dal source system
2. i dati vengono persistiti localmente in modo coerente
3. ogni run è tracciata
4. i cambiamenti vengono identificati in modo consistente
5. il risultato è sufficiente per alimentare in futuro il layer `core`
6. non è stata introdotta logica di dominio impropria nel sync

---

## Rischi principali da osservare

### 1. Chiavi instabili o ambigue
Potrebbero emergere record non identificabili in modo pulito.

### 2. Rumore nel change detection
Piccole variazioni tecniche potrebbero generare troppi `UPDATED`.

### 3. Eccessiva interpretazione nel sync
Si potrebbe essere tentati di risolvere già qui problemi che appartengono al `core`.

### 4. Accoppiamento eccessivo alla sorgente
Una modellazione troppo aderente al sistema esterno potrebbe rendere fragile il passaggio successivo.

### 5. Osservabilità insufficiente
Senza run log chiari, debugging e trust nel sistema diventano subito difficili.

---

## Decisioni rinviate alle milestone successive

Le seguenti decisioni non fanno parte di v0.1:

- definizione concreta dei `Source Facts`
- regole di ricostruzione canonica
- computed facts
- aggregate
- rebuild policy-driven
- canonical states
- explainability di business
- projection applicative

---

## Esito atteso della milestone

Al termine di v0.1 il progetto deve aver ottenuto:

> un layer `sync` reale, piccolo ma affidabile, capace di costituire la base tecnica per il primo `core` canonico.

Se questa milestone fallisce o mostra ambiguità forti, il problema va risolto qui, prima di procedere con `Source Facts`.

Se invece regge bene, allora il passo successivo naturale sarà:

- **v0.2 — Source Facts**

---