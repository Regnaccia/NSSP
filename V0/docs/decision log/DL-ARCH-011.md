# DL-ARCH-011 — Policy Governance & Conflict Resolution nel layer CORE

## Status
Accepted

## Context

Nei DL precedenti è stato definito che:

- il sistema è articolato in `sync`, `core`, `app` (DL-ARCH-001)
- il `core` è fact-centric e costruisce Source Facts, Computed Facts e Canonical Operational States (DL-ARCH-002, DL-ARCH-007)
- il `sync` non contiene logica operativa e il `core` è responsabile della semantica del sistema (DL-ARCH-004)
- il rebuild è governato da dependency chain esplicite ed è deterministico e rigenerabile (DL-ARCH-005, DL-ARCH-006)
- i Source Facts possono essere sia external-derived sia native (DL-ARCH-008)
- i Computed Facts possono essere meccanici o policy-driven (DL-ARCH-009)
- il rebuild avviene secondo confini di Aggregate Root e con dipendenze cross-aggregate esplicite (DL-ARCH-010)

Con l’introduzione dei **Policy-driven Computed Facts** emerge una nuova criticità architetturale:

> il sistema sa calcolare scenari diversi, ma non è ancora formalizzato **come governa le policy**, come risolve i conflitti e come garantisce coerenza, spiegabilità e auditabilità delle decisioni operative.

In un contesto reale possono infatti coesistere più policy concorrenti, ad esempio:

- allocazione stock FIFO
- priorità urgenze
- regole cliente/destinazione
- soglie di spedizione
- giorno fisso di approntamento
- conferma cliente
- override manuali
- vincoli qualità o disponibilità fisica

Senza una governance esplicita si rischia che:

- i Policy-driven Computed Facts diventino arbitrari
- i Canonical Operational States siano opachi
- lo stesso scenario produca esiti incoerenti
- i conflitti vengano risolti in modo implicito e non auditabile

È quindi necessario formalizzare un modello di **Policy Governance** nel `core`.

---

## Decision

Il layer `core` introduce un modello esplicito di:

> **Policy Governance & Conflict Resolution**

basato sui seguenti principi:

1. le policy sono oggetti logici espliciti del sistema
2. le policy non coincidono con i facts
3. i Policy-driven Computed Facts devono dichiarare da quali policy dipendono
4. i conflitti tra policy devono essere risolti da regole canoniche e tracciabili
5. gli override manuali sono policy esplicite, non eccezioni “fuori modello”
6. ogni Canonical Operational State rilevante deve essere spiegabile tramite:
   - facts di input
   - policy applicate
   - regola di precedenza usata

---

## Definitions

### Policy

Una **Policy** è una regola configurabile o istituzionale che guida l’interpretazione operativa dei facts.

Una policy:

- non è un Source Fact
- non è un evento grezzo
- non è di per sé uno stato operativo
- influenza il calcolo dei Policy-driven Computed Facts
- può concorrere alla determinazione degli Operational States

Esempi:

- strategia di allocazione stock = `FIFO`
- priorità urgenze = `urgency-first`
- spedizione anticipata se merce pronta oltre soglia
- richiedi conferma cliente prima della spedizione
- separa sempre le urgenze dal resto
- corriere preferenziale per fascia peso

---

### Policy Set

Un **Policy Set** è l’insieme coerente di policy attive in un dato contesto logico.

Un Policy Set può essere definito a livello di:

- sistema
- dominio
- aggregate
- cliente
- destinazione
- ordine
- urgenza specifica

---

### Policy-driven Computed Fact

Un Policy-driven Computed Fact è valido solo se dichiara esplicitamente:

- facts di input
- aggregate o contesto di calcolo
- policy richieste
- eventuali precedenze applicate

---

### Conflict

Esiste un **conflitto** quando due o più policy attive producono esiti incompatibili nello stesso contesto.

Esempi:

- `FIFO` vs `urgency-first`
- `spedisci tutto il venerdì` vs `spedisci subito l’urgenza`
- `attendi conferma cliente` vs `override spedizione immediata`

---

## Scope of Policies

Le policy appartengono al `core`, ma non tutte hanno lo stesso livello.

Si distinguono almeno quattro livelli:

### 1. System Policy
Regole generali valide salvo override espliciti.

Esempi:
- strategia di allocazione default
- definizione standard di “coverable now”
- comportamento standard in caso di conflitto

---

### 2. Domain / Aggregate Policy
Regole valide in un dominio o aggregate specifico.

Esempi:
- regole di shipping per Destination Aggregate
- regole di availability per Article Supply-Demand Aggregate

---

### 3. Context Policy
Regole applicate a un contesto locale.

Esempi:
- policy per un cliente
- policy per una destinazione
- policy per una categoria articolo

---

### 4. Exception / Override Policy
Regole eccezionali, esplicite e tracciate, che prevalgono su policy più generali.

Esempi:
- spedizione urgente manuale
- blocco qualità manuale
- forza approntamento fuori calendario

---

## Policy Hierarchy

Il sistema adotta una gerarchia canonica di precedenza.

Ordine di precedenza generale:

1. **Physical / Constraint Policies**
2. **Manual Override Policies**
3. **Urgency / Exception Policies**
4. **Context Policies**
5. **Domain / Aggregate Policies**
6. **System Default Policies**

---

### 1. Physical / Constraint Policies

Sono vincoli che derivano da impossibilità fisica, blocco qualità, assenza materiale, vincoli non derogabili.

Caratteristiche:

- non rappresentano una preferenza
- bloccano l’esito operativo anche in presenza di altre policy
- hanno precedenza massima

Esempi:
- materiale non fisicamente disponibile
- articolo bloccato per non conformità
- articolo non ancora validato come pronto

---

### 2. Manual Override Policies

Sono decisioni operative esplicite inserite dal sistema o da operatore autorizzato.

Caratteristiche:

- devono essere intenzionali e tracciate
- prevalgono sulle policy ordinarie
- non possono violare vincoli fisici non derogabili

Esempi:
- forza spedizione oggi
- separa questa urgenza dal lotto standard
- ignora il giorno fisso per questa destinazione

---

### 3. Urgency / Exception Policies

Gestiscono casistiche urgenti o straordinarie.

Caratteristiche:

- prevalgono sulle policy ordinarie
- restano subordinate a vincoli fisici e override superiori

Esempi:
- `urgency-first`
- priorità assoluta a ordine urgente
- approntamento anticipato di materiale pronto urgente

---

### 4. Context Policies

Regole locali di cliente, destinazione o caso specifico.

Esempi:
- richiedi conferma cliente
- spedisci solo sopra soglia economica
- usa corriere X fino a 100 kg

---

### 5. Domain / Aggregate Policies

Regole standard di dominio.

Esempi:
- policy di allocazione stock standard nel dominio availability
- regole di pianificazione base nel dominio shipping

---

### 6. System Default Policies

Fallback globali del sistema.

Esempi:
- FIFO come default
- nessuna separazione spedizioni salvo indicazione contraria

---

## Conflict Resolution Rules

### Rule 1 — No implicit conflict resolution

Non è ammesso risolvere conflitti in modo implicito nel codice applicativo o nelle projection.

Ogni conflitto deve essere risolvibile tramite:

- gerarchia di policy
- regola canonica di precedence
- eventuale override esplicito

---

### Rule 2 — Higher-level precedence wins

In caso di conflitto, prevale la policy con livello di precedenza superiore.

Esempio:

- `FIFO` (domain policy)
- `urgency-first` su ordine urgente (urgency policy)

Risultato:
- prevale `urgency-first`

---

### Rule 3 — Physical constraints are non-bypassable by normal policy

Una policy ordinaria non può dichiarare disponibile ciò che il sistema considera fisicamente non disponibile.

Esempio:

- override di spedizione immediata
- articolo ancora bloccato da qualità

Risultato:
- l’override non rende l’articolo fisicamente spedibile
- può al massimo cambiare priorità o pianificazione, non la realtà fisica

---

### Rule 4 — Manual override must be explicit and auditable

Un override manuale deve essere registrato come oggetto canonico del sistema.

Non è ammesso:

- alterare direttamente uno state finale
- cambiare projection senza traccia nel core

L’override entra nel sistema come fact/policy nativa esplicita e partecipa al rebuild.

---

### Rule 5 — Same-level conflicts require canonical tie-breaker

Se due policy dello stesso livello confliggono, deve esistere un tie-breaker canonico.

Possibili tie-breaker:

- priorità numerica esplicita
- data di attivazione più recente
- specificità maggiore del contesto
- ranking dichiarato nel dominio

Il tie-breaker deve essere definito per dominio, non lasciato implicito.

---

## Relationship with Aggregate Roots

Le policy si applicano sempre entro un contesto preciso di Aggregate Root.

Regola:

> non esistono policy “flottanti” senza aggregate o contesto dichiarato.

Esempi:

- `FIFO` su `Article Supply-Demand Aggregate`
- `giorno_fisso_venerdì` su `Destination / Shipping Aggregate`
- `urgenza_ordine` su `Order Aggregate`

In caso di effetti cross-aggregate:

- la policy nasce in un aggregate
- gli effetti sugli altri aggregate devono passare tramite dependency esplicite

---

## Relationship with Computed Facts

### Mechanical Computed Facts
Non dipendono da policy.

Devono restare:

- stabili
- puramente deterministici
- riusabili come base comune

---

### Policy-driven Computed Facts
Dipendono da policy esplicite e dal relativo contesto.

Ogni Policy-driven Computed Fact dovrebbe essere concettualmente leggibile come:

> risultato di una funzione deterministica di  
> `(facts + policy set + precedence rules)`

---

## Relationship with Operational States

I Canonical Operational States non devono incorporare logiche arbitrarie.

Devono invece essere il risultato finale di:

1. facts canonici
2. computed facts meccanici
3. computed facts policy-driven
4. conflict resolution esplicita

Esempio:

```text
ShippingReadinessState:
- uses qty_remaining
- uses qty_coverable_now
- uses destination shipping policies
- uses urgency override
- resolves conflicts through precedence model
→ returns READY_STANDARD / READY_URGENT / WAIT_CONFIRMATION / NOT_READY