# MRS OMR — Descrizione del progetto e razionale

## 1. Contesto reale

OMR è una realtà manifatturiera che opera su:

- produzione meccanica
- gestione commesse cliente
- articoli standard e articoli su disegno
- flussi che coinvolgono:
  - commerciale
  - produzione
  - magazzino
  - logistica

Il sistema informativo attuale è basato su un gestionale (EasyJob) che:

- contiene dati strutturati (ordini, articoli, movimenti, clienti)
- è affidabile come archivio
- ma è **statico e non operativo**

---

## 2. Problema fondamentale

Il problema NON è la mancanza di dati.

> Il problema è che i dati non diventano automaticamente decisioni operative.

---

### 2.1 Natura del problema

Nel flusso reale aziendale:

- i dati sono distribuiti
- le informazioni vengono ricostruite manualmente
- le decisioni sono:
  - implicite
  - non formalizzate
  - non tracciabili

Esempio tipico:
- esiste un ordine
- esiste stock
- esiste produzione in corso

👉 ma NON esiste una risposta chiara e sistemica a:
- cosa è davvero pronto?
- cosa posso spedire oggi?
- cosa è in ritardo?
- cosa devo produrre prima?

---

### 2.2 Il “fabbisogno cartaceo” (sintomo)

Il fabbisogno attuale rappresenta:

- una vista costruita manualmente
- un mix di:
  - dati reali
  - interpretazioni
  - priorità implicite

Problemi:
- statico
- non aggiornato in tempo reale
- non replicabile
- non auditabile

👉 è una **soluzione operativa emergente**, non un sistema

---

## 3. Limite strutturale dei gestionali

I gestionali tradizionali (come Easy):

### Funzionano bene per:
- registrare dati
- storicizzare
- garantire consistenza contabile

### NON funzionano per:
- orchestrare decisioni operative
- integrare più dimensioni (tempo, priorità, urgenza)
- reagire in tempo reale
- modellare scenari

👉 sono sistemi di **registrazione**, non di **decisione**

---

## 4. Natura delle decisioni operative

Le decisioni aziendali reali sono:

### 4.1 Multi-dimensione
Dipendono da:
- stato ordine
- disponibilità reale
- produzione
- urgenze
- logistica
- vincoli fisici

---

### 4.2 Dinamiche
- cambiano continuamente
- dipendono da eventi (produzione, arrivi, ritardi)

---

### 4.3 Contestuali
- diverse per cliente
- diverse per destinazione
- diverse per situazione

---

### 4.4 Non deterministiche nel sistema attuale
- due persone possono prendere decisioni diverse sugli stessi dati

👉 oggi il sistema non garantisce coerenza decisionale

---

## 5. Gap operativo

Esiste quindi un gap tra:

### Dato disponibile
✔ ordini  
✔ stock  
✔ produzione  
✔ spedizioni  

### Decisione operativa
❌ cosa fare ora  
❌ cosa ha priorità  
❌ cosa è realmente fattibile  

---

👉 Questo gap oggi è colmato da:
- esperienza
- intuizione
- comunicazione informale

Ma questo porta a:
- inefficienze
- errori
- difficoltà di scalare

---

## 6. Necessità del progetto

Il progetto nasce per risolvere questo gap.

### Obiettivo reale:

> trasformare dati dispersi in **sistema decisionale coerente, esplicito e replicabile**

---

## 7. Cambio di paradigma

Il passaggio chiave è:

### DA
- sistema che registra il passato

### A
- sistema che rappresenta il presente operativo
- sistema che supporta decisioni

---

## 8. Estensione del gestionale

Il progetto NON sostituisce Easy.

Lo estende.

### Easy rimane:
- fonte dati ufficiale
- base contabile

### MRS diventa:
- layer operativo
- layer decisionale
- layer di integrazione

---

## 9. Integrazione della realtà fisica

Uno dei limiti principali attuali:

👉 Easy non conosce la realtà fisica in tempo reale

Esempi:
- pezzo prodotto ma non consuntivato
- materiale pronto ma non registrato
- urgenza comunicata a voce

---

Il progetto introduce:

- dati di produzione real-time
- input operatori
- eventi macchina
- override operativi

👉 il sistema si avvicina alla realtà reale, non solo contabile

---

## 10. Formalizzazione della logica operativa

Oggi:
- le regole esistono ma sono nella testa delle persone

Domani:
- le regole diventano:
  - esplicite
  - configurabili
  - tracciabili

Esempi:
- priorità urgenze
- logiche di spedizione
- soglie economiche
- strategie di allocazione

---

## 11. Obiettivi concreti

Il sistema deve permettere di rispondere in modo chiaro a:

### Produzione
- cosa devo produrre adesso?
- cosa è urgente?

### Magazzino
- cosa è pronto davvero?
- cosa posso preparare?

### Logistica
- cosa spedisco oggi?
- cosa conviene accorpare?

### Direzione
- dove sono i colli di bottiglia?
- cosa rischia ritardi?

---

## 12. Benefici attesi

### Operativi
- riduzione errori
- meno comunicazioni informali
- maggiore velocità decisionale

### Organizzativi
- allineamento tra reparti
- visione condivisa
- meno dipendenza da singole persone

### Strategici
- base per automazioni
- base per AI
- scalabilità del sistema

---

## 13. Visione futura

Il progetto evolve verso:

- integrazione produzione real-time
- pianificazione avanzata
- simulazioni scenario
- suggerimenti automatici
- automazione decisionale (parziale o totale)

---

## 14. Sintesi finale

Il problema non è “gestire dati”.

> Il problema è **trasformare dati in decisioni operative affidabili**

Il progetto MRS è la risposta a questo problema.

---
