# DL-ARCH-015.md  
## Contracts: Projection Schema & Service I/O

### Status  
Accepted

---

### Context

Il sistema MRS introduce:

- Projection costruite dal core  
- Servizi che eseguono calcoli  
- Separazione tra semantica e calcolo  

Senza contratti formali si rischia:

- accoppiamento implicito  
- incoerenza tra moduli  
- difficoltà di evoluzione  
- impossibilità di sostituzione servizi  

---

### Decision

Il sistema introduce **Contracts espliciti** tra Core e Services.

---

## 1. Projection Schema Contract (Input)

Ogni projection deve avere:

- nome univoco  
- versione  
- schema campi  
- significato esplicito  

---

### Rules

- nessuna colonna implicita  
- schema stabile per versione  
- significato definito nel core  

---

## 2. Service Input Contract

Ogni servizio deve dichiarare:

- projection richiesta  
- versione supportata  
- parametri  

---

## 3. Service Output Contract

I servizi restituiscono solo strutture definite:

### Tipi

- candidate results  
- decision suggestions  
- delta  

---

## 4. Core Integration

Il core:

- valida output  
- applica policy  
- decide cosa persistere  

---

### Rule

> Nessun output diventa verità senza validazione del core.

---

## 5. Versioning

- breaking change → nuova versione  
- servizi possono supportare più versioni  
- il core seleziona la versione  

---

## 6. Technology Independence

I contract sono indipendenti da:

- SQL  
- Pandas  
- API  

Rappresentano solo struttura e semantica.

---

## 7. Validation

Il sistema valida:

- projection  
- input servizi  
- output servizi  

---

## 8. Anti-Patterns

❌ servizi che leggono dal DB  
❌ colonne implicite  
❌ output non strutturati  
❌ contract non versionati  

---

## Benefits

- disaccoppiamento forte  
- sostituibilità servizi  
- chiarezza semantica  
- testabilità  

---

## Trade-offs

- overhead iniziale  
- necessità di governance  

---

## Principle

> Il contratto definisce il linguaggio tra core e servizi.

---

### Related Decisions

- DL-ARCH-013 (Data Strategy)  
- DL-ARCH-014 (Core vs Services Separation)  
- DL-ARCH-009 (Aggregate Roots)  