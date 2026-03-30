# IMPLEMENTATION V1 — Fase 2: Schedulazione Coda + Reparto Terminale

*Data: 2026-03-27*

---

## Obiettivo

Introdurre il layer di gestione produzione attiva:

- **F2 Schedulazione** — Ufficio produzione vede e gestisce la coda di lavorazione
- **Reparto Terminale** — L'operatore al terminale in reparto avanza le commesse nel loro ciclo di vita
- **State machine commesse** — Transizioni di stato tracciate e validate

Prerequisito: Fase 1 completata, le commesse vengono già create da F1a/genera-commesse.

---

## File creati

### `app/schemas/commessa.py`

Schemi Pydantic v2 per commesse e macchine.

| Schema | Uso |
|---|---|
| `MacchinaResponse` | Dati macchina (codice, nome, stato, operazioni_eseguibili) |
| `CommessaResponse` | Commessa completa con join articolo, macchina, ordine. Include `qty_totale` e `qty_residua` calcolati |
| `AssegnaMacchinaRequest` | Body POST assegna macchina |
| `RiordinaVoce` | Singola voce `{commessa_id, posizione}` nel riordino |
| `RiordinaCodaRequest` | Body POST riordina coda |
| `RiordinaCodaResponse` | Response `{aggiornate: int}` |
| `SospendiRequest` | Body POST sospendi (con nota opzionale) |
| `AggiornaQtyRequest` | Body POST aggiorna-qty (qty_prodotta_cliente, qty_prodotta_scorta) |

**Campi calcolati in `CommessaResponse`:**

```
qty_totale  = qty_cliente + qty_scorta
qty_residua = max(0, qty_totale - qty_prodotta_cliente - qty_prodotta_scorta)
```

### `app/services/commesse.py`

State machine e query per le commesse. Tutta la logica di stato vive qui — i router non toccano il DB direttamente.

**State machine — transizioni valide:**

```
in_coda  ──avvia──►  in_produzione  ──completa──►  completata
                          │
                       sospendi
                          │
                          ▼
                        sospesa  ──riprendi──►  in_produzione
```

| Azione | Da | A | Effetti collaterali |
|---|---|---|---|
| `avvia` | `in_coda` | `in_produzione` | — |
| `sospendi` | `in_produzione` | `sospesa` | Scrive `sospesa_at`, `sospesa_nota` |
| `riprendi` | `sospesa` | `in_produzione` | Azzera `sospesa_at`, `sospesa_nota` |
| `completa` | `in_produzione` | `completata` | Scrive `completata_at` |

Transizioni non valide → `CommessaError` (409 Conflict nel router).

**Funzioni esposte:**

| Funzione | Descrizione |
|---|---|
| `transizione(session, id, azione, **kwargs)` | Esegue una transizione di stato |
| `assegna_macchina(session, id, macchina_id)` | Assegna macchina (solo se `in_coda` o `sospesa`) |
| `aggiorna_qty(session, id, qty_cliente, qty_scorta)` | Aggiorna qty prodotte (solo se `in_produzione` o `sospesa`) |
| `get_commesse_attive(session)` | Lista `in_coda + in_produzione + sospesa`, ordinata per `posizione_coda` |
| `get_commesse_macchina(session, macchina_id)` | Commesse di una macchina specifica, non completate |
| `get_commessa_detail(session, id)` | Dettaglio singola commessa con tutti i join |

Tutte le query usano un join comune (`_BASE_SQL`) con articolo, macchina, riga_ordine, ordine per avere sempre i dati completi in un solo round-trip.

### `app/services/priorita.py`

Calcolo `posizione_coda` e `priorita_suggerita` per le commesse `in_coda`.

**`ricalcola_coda(session) → int`**

Algoritmo di ordinamento in tre livelli:

1. **Urgenza formale** — commesse con un evento `urgenza_formale` aperto sull'ordine associato → `priorita_suggerita=1`, posizionate per prime
2. **Data consegna** — `data_consegna ASC NULLS LAST` (le scadenze più vicine prima)
3. **FIFO** — `created_at ASC` come spareggio finale

Solo le commesse `in_coda` vengono riposizionate. Le commesse `in_produzione` e `sospesa` mantengono la loro `posizione_coda` esistente (sono già su una macchina).

Ritorna il numero di commesse aggiornate.

**Quando chiamarlo:**

- Manualmente via `POST /api/produzione/coda/ricalcola-priorita`
- In futuro: automaticamente quando viene creato un evento urgenza o quando arriva una nuova commessa (Fase 4)

---

### `app/routers/produzione.py` — aggiunte F2

Endpoint aggiunti al router produzione esistente (tag: `produzione`).

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/produzione/coda` | Lista commesse attive (in_coda, in_produzione, sospesa) |
| `POST` | `/api/produzione/coda/riordina` | Riordino manuale drag&drop: `[{commessa_id, posizione}]` |
| `POST` | `/api/produzione/coda/ricalcola-priorita` | Applica algoritmo urgenza→data→FIFO |
| `POST` | `/api/produzione/commesse/{id}/assegna` | Assegna macchina a una commessa |
| `GET` | `/api/produzione/macchine` | Lista macchine (query param: `solo_attive=true`) |

**Riordino manuale vs automatico:**

Il sistema supporta entrambi i flussi:
- L'ufficio produzione può trascinare le commesse nella UI → `POST /coda/riordina` con le posizioni finali
- Oppure può chiedere al sistema di ricalcolare in base ai criteri → `POST /coda/ricalcola-priorita`

Le due operazioni si sovrascrivono a vicenda — è l'operatore a decidere quale usare.

---

### `app/routers/reparto.py`

Router `/api/reparto` per il terminale fisso in reparto (modalità kiosk, DL-ARCH-016).

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/reparto/macchine` | Lista macchine attive (selezione all'avvio terminale) |
| `GET` | `/api/reparto/macchine/{id}/coda` | Commesse assegnate a questa macchina |
| `GET` | `/api/reparto/commesse/{id}` | Dettaglio singola commessa |
| `POST` | `/api/reparto/commesse/{id}/avvia` | `in_coda → in_produzione` |
| `POST` | `/api/reparto/commesse/{id}/sospendi` | `in_produzione → sospesa` (body: `{nota?}`) |
| `POST` | `/api/reparto/commesse/{id}/riprendi` | `sospesa → in_produzione` |
| `POST` | `/api/reparto/commesse/{id}/aggiorna-qty` | Aggiorna qty prodotte durante lavorazione |
| `POST` | `/api/reparto/commesse/{id}/completa` | `in_produzione → completata` |

**Flusso tipico operatore:**

```
1. Apre il terminale → vede le sue macchine
2. Seleziona la macchina → vede la coda di quella macchina
3. Prende la prima commessa in coda → "Avvia"
4. Aggiorna le qty prodotte man mano → "Aggiorna qty"
5. Se interrotto → "Sospendi" con nota
6. Alla fine → "Completa"
```

---

## File modificati

### `app/main.py`

```python
from app.routers import reparto as reparto_router
# ...
app.include_router(reparto_router.router)
```

---

## API completa Fase 2

| Method | Endpoint | Tag | Descrizione |
|---|---|---|---|
| `GET` | `/api/produzione/coda` | produzione | Vista coda lavorazione |
| `POST` | `/api/produzione/coda/riordina` | produzione | Riordino manuale posizioni |
| `POST` | `/api/produzione/coda/ricalcola-priorita` | produzione | Ricalcola con algoritmo |
| `POST` | `/api/produzione/commesse/{id}/assegna` | produzione | Assegna macchina |
| `GET` | `/api/produzione/macchine` | produzione | Lista macchine |
| `GET` | `/api/reparto/macchine` | reparto | Macchine per kiosk |
| `GET` | `/api/reparto/macchine/{id}/coda` | reparto | Coda macchina |
| `GET` | `/api/reparto/commesse/{id}` | reparto | Dettaglio commessa |
| `POST` | `/api/reparto/commesse/{id}/avvia` | reparto | Avvia lavorazione |
| `POST` | `/api/reparto/commesse/{id}/sospendi` | reparto | Sospendi con nota |
| `POST` | `/api/reparto/commesse/{id}/riprendi` | reparto | Riprendi |
| `POST` | `/api/reparto/commesse/{id}/aggiorna-qty` | reparto | Aggiorna qty prodotte |
| `POST` | `/api/reparto/commesse/{id}/completa` | reparto | Completa commessa |

---

## Decisioni architetturali applicate

| Decisione | DL | Come implementato |
|---|---|---|
| State machine centralizzata | DL-019 | Tutta la logica di transizione in `services/commesse.py` — i router chiamano solo `transizione()` |
| Terminale kiosk senza auth | DL-016 | `/api/reparto` non ha guard JWT in Fase 2 — auth kiosk da implementare in Fase auth |
| Qty calcolate, non denormalizzate | DL-007 | `qty_totale` e `qty_residua` calcolati in `_row_to_dict()`, mai colonne DB |
| Errori dominio → HTTP 409 | — | `CommessaError` catturata nel router → `HTTPException(status_code=409)` |

---

## Errori gestiti

| Condizione | HTTP | Messaggio |
|---|---|---|
| Commessa non trovata | 404 | `Commessa {id} non trovata` |
| Transizione non valida (stato sbagliato) | 409 | `Transizione 'X' non valida: stato corrente='Y', atteso='Z'` |
| Macchina non trovata nell'assegna | 404 | `Macchina non trovata` |
| Assegna macchina su commessa già in lavorazione | 409 | `Impossibile assegnare macchina: commessa in stato 'X'` |
| Aggiorna qty su commessa non avviata | 409 | `Impossibile aggiornare qty: commessa in stato 'X'` |

---

## Fase successiva — Fase 3

```
services/magazzino.py        # approntamento ordini, logica consegna
routers/magazzino.py         # F3 terminale magazzino, scansione barcode
services/logistica.py        # policy cliente, schedulazione spedizioni
routers/logistica.py         # F4 logistica, calendar view, corrieri
```
