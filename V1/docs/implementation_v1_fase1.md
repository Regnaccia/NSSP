# IMPLEMENTATION V1 — Fase 1: Business Logic Layer (F1a, F1b, Articoli)

*Data: 2026-03-27*

---

## Obiettivo

Introdurre il primo layer di business logic leggibile dagli utenti:

- **F1a** — Vista ordini cliente da processare (Ufficio Produzione)
- **F1b** — Vista articoli sotto scorta target (Ufficio Produzione)
- **Genera commesse** — Crea commesse + export Excel per EasyJob
- **Anagrafica articoli** — Lettura e aggiornamento campi MRS-owned

Prerequisito: Fase 0 completata, tabelle sync popolate.

---

## File creati

### `app/schemas/produzione.py`

Schemi Pydantic v2 per le response e i body di questa fase.

| Schema | Uso |
|---|---|
| `RigaF1aResponse` | Una riga nella vista F1a |
| `RigaSelezionataInput` | Input riga nel body genera-commesse |
| `GeneraCommesseRequest` | Body POST genera-commesse |
| `GeneraCommesseResponse` | Response genera-commesse (count + Excel base64) |
| `ArticoloF1bResponse` | Un articolo nella vista F1b |
| `RicalcolaScorteRequest` | Body POST ricalcola-scorte |
| `RicalcolaScorteResponse` | Response ricalcolo |
| `ArticoloPatchRequest` | Body PATCH articolo (solo campi MRS-owned) |
| `ArticoloResponse` | Response GET articolo completo |

### `app/services/disponibilita.py`

Computed facts calcolati live (DL-ARCH-007 — mai colonne DB).

**`get_qty_da_produrre(riga) → int`**

```
max(0, qty_ordinata - qty_disponibile - qty_in_produzione)
```

**`get_righe_da_processare(session, filtri) → list[dict]`**

Restituisce le righe ordine che l'ufficio produzione deve ancora processare:
- `stato` riga NOT IN (`spedito`, `chiuso`)
- `qty_da_produrre > 0`
- Nessuna commessa attiva (stato != `completata`) già esistente per quella riga
- Join con articoli, ordini, clienti per dati completi
- Calcola `flag_data_scaduta` (data_consegna < oggi)
- Calcola `flag_urgenza` (esiste evento `urgenza_formale` aperto su quell'ordine)
- Supporta filtri: `cliente_id`, `data_da`, `data_a`, `urgenza_only`

**`get_qty_disponibile_futura(session, articolo_id) → int`**

```
giacenza_attuale - impegni_ordini_aperti
```

- `giacenza_attuale` = `MAX(qty_disponibile)` tra tutte le righe aperte di quell'articolo (campo sync-owned da EasyJob)
- `impegni` = `SUM(qty_ordinata - qty_consegnata)` righe aperte di quell'articolo
- Ritorna `max(0, giacenza - impegni)`

Usato da F1b per calcolare se la scorta è sufficiente.

### `app/services/scorte.py`

Algoritmo calcolo `scorta_mensile` con 3 bug corretti rispetto a V0.

**`calcola_scorta_mensile(movimenti_12m) → tuple[int, bool]`**

```
movimenti_12m = [{mese: date, qty: int}]
→ (scorta_mensile, storico_sufficiente)
```

Algoritmo:
1. Conta i mesi distinti con `qty > 0`
2. Se mesi < `MESI_MINIMI` (default 4 da env) → ritorna `(0, False)`
3. Rimuove outlier z-score (`|z| > 3.0`) **prima** di calcolare i percentili
4. Calcola `percentile_80` su tre orizzonti: 12m, 6m, 3m
5. `scorta_mensile = media dei tre percentili`

**3 bug corretti vs V0:**

| Bug | V0 (sbagliato) | V1 (corretto) |
|---|---|---|
| Soglia storico | Contava tutti i mesi del periodo (inclusi mesi a zero) | Conta solo mesi con vendite effettive ≥ `MESI_MINIMI` |
| Filtro outlier | Applicato dopo il filtraggio del periodo | Applicato prima del calcolo (corretto statisticamente) |
| Calcolo disponibile futura | Usava solo `giacenza` | Sottrae anche gli impegni aperti (`giacenza - impegni`) |

**`ricalcola_scorte_tutti(session, articolo_id=None) → int`**

- Legge movimenti vendita da EasyJob (`MAG_REALE` dove `CAUM_COD='VEN'`, ultimi 12 mesi)
- Aggiorna `articoli.scorta_mensile`, `storico_sufficiente`, `scorta_calcolata_at`
- Solo per `tipo_produzione IN ('PEZZO', 'BARRA', 'FASCI')`
- Se `articolo_id` specificato → aggiorna solo quell'articolo
- Ritorna il numero di articoli aggiornati

**Variabili d'ambiente:**

| Variabile | Default | Descrizione |
|---|---|---|
| `SOGLIA_MESI_STORICO` | `4` | Mesi minimi con vendite per storico_sufficiente=True |

### `app/routers/produzione.py`

Router `/api/produzione` con endpoint F1a e F1b.

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/produzione/f1a` | Lista righe da processare (filtri: cliente_id, data_da, data_a, urgenza_only) |
| `POST` | `/api/produzione/genera-commesse` | Crea commesse + Excel EasyJob in base64 |
| `GET` | `/api/produzione/f1b` | Articoli sotto scorta target |
| `POST` | `/api/produzione/ricalcola-scorte` | Forza ricalcolo scorta_mensile |

**Genera commesse — logica:**

Per ogni riga selezionata:
1. Legge la riga ordine (join articolo, ordine, cliente)
2. Ricalcola `qty_da_produrre` live — se nel frattempo è diventata 0, skip silenzioso
3. Crea record `Commessa` con `stato=in_coda`
4. Accumula i dati per il foglio Excel

Genera un file `.xlsx` con colonne EasyJob (stesso formato Fabisogno):
`N. Ordine | Codice Articolo | Descrizione | Cliente | Data Consegna | Qty Cliente | Qty Scorta | Qty Totale | Qty Ciclo Corrente | Note`

La response contiene il file Excel codificato in base64 per il download diretto dal frontend senza passare per il filesystem.

**F1b — logica:**

- Filtra articoli: `storico_sufficiente=True` AND `tipo_produzione IN ('PEZZO','BARRA','FASCI')`
- Per ogni articolo calcola `target_scorta = scorta_mensile * mesi_scorta`
- Calcola `qty_disponibile_futura` live (via `disponibilita.py`)
- Mostra solo articoli dove `target_scorta > qty_disponibile_futura`

### `app/routers/articoli.py`

Router `/api/articoli`.

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/articoli` | Lista con filtri: categoria, tipo_produzione, storico_sufficiente |
| `GET` | `/api/articoli/{id}` | Dettaglio articolo |
| `PATCH` | `/api/articoli/{id}` | Aggiorna campi MRS-owned |

**Campi aggiornabili via PATCH (MRS-owned):**
`mesi_scorta`, `tipo_produzione`, `multipli_taglio`, `capienza`, `prd_pari`, `lunghezza_barra`

**Campi MAI aggiornabili via PATCH (sync-owned):**
`codice`, `descrizione`, `categoria`, `synced_at` — questi appartengono al sync EasyJob.

---

## File modificati

### `app/main.py`

Aggiunto include dei nuovi router:

```python
from app.routers import produzione as produzione_router
from app.routers import articoli as articoli_router
# ...
app.include_router(produzione_router.router)
app.include_router(articoli_router.router)
```

### `app/sync/scheduler.py`

Aggiunto job mensile ricalcolo scorte:

```python
_scheduler.add_job(
    lambda: _run_in_session(ricalcola_scorte_tutti),
    trigger=CronTrigger(day=1, hour=2, timezone="Europe/Rome"),
    id="ricalcolo_scorte_mensile",
    name="Ricalcolo scorte mensili (primo del mese alle 2:00)",
)
```

---

## API completa Fase 1

| Method | Endpoint | Tag | Descrizione |
|---|---|---|---|
| `GET` | `/api/produzione/f1a` | produzione | Vista ordini da processare |
| `POST` | `/api/produzione/genera-commesse` | produzione | Crea commesse + Excel |
| `GET` | `/api/produzione/f1b` | produzione | Articoli sotto scorta |
| `POST` | `/api/produzione/ricalcola-scorte` | produzione | Forza ricalcolo scorte |
| `GET` | `/api/articoli` | articoli | Lista articoli |
| `GET` | `/api/articoli/{id}` | articoli | Dettaglio articolo |
| `PATCH` | `/api/articoli/{id}` | articoli | Aggiorna articolo (MRS-owned) |

---

## Decisioni architetturali applicate

| Decisione | DL | Come implementato |
|---|---|---|
| Computed facts live, mai colonne | DL-007 | `qty_da_produrre`, `qty_disponibile_futura`, `target_scorta` calcolati in memoria, mai scritti nel DB |
| Separazione services / routers | DL-001 | `routers/produzione.py` chiama solo funzioni di `services/`, non esegue SQL direttamente |
| Sync-owned vs MRS-owned | DL-008 | PATCH articoli blocca i campi sync-owned; sync handlers non toccano `scorta_mensile`, `mesi_scorta` |
| Nickname cliente | DL-017 | `RigaF1aResponse.cliente` usa `COALESCE(nickname, ragione_sociale)` |
| Excel via base64 | DL-018 | File Excel in response JSON, nessun filesystem temporaneo sul server |

---

## Fase successiva — Fase 2

```
services/commesse.py    # state machine commessa
services/priorita.py    # calcolo posizione coda
routers/produzione.py   # F2 (schedulazione coda)
routers/reparto.py      # terminale operatore reparto
```
