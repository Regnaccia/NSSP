# MRS — Contesto per Claude Code
## Decision Log architetturali + Specifiche operative unificate

> **Questo documento è il riferimento primario per lo sviluppo con Claude Code.**
> Integra i Decision Log architetturali (DL-ARCH-001→008) con le specifiche operative (MRS_Specifiche_Tecniche_v1).
> In caso di contrasto tra DL e spec operativa, **la spec operativa prevale per l'MVP**.
> I DL 009–015 sono sospesi per l'MVP e ripresi in fase post-MVP.

---

## 1. Mappa concettuale DL → struttura codice

I DL usano una terminologia astratta. Questa sezione la traduce nella struttura concreta del progetto.

| Concetto DL | Dove vive nel codice | Note |
|---|---|---|
| **Layer `sync`** (DL-001/003) | `backend/app/sync/` | `easyjob.py`, `scheduler.py`, `handlers.py` |
| **Layer `core`** (DL-001/002) | `backend/app/services/` | Tutta la business logic sta qui |
| **Layer `app`** (DL-001) | `backend/app/routers/` + `frontend/` | I router chiamano i services, non contengono logica |
| **Source Facts — external-derived** (DL-002/008) | Tabelle: `articoli`, `clienti`, `ordini`, `righe_ordine` | Alimentate da sync EasyJob. Il sync le possiede. |
| **Source Facts — native MRS** (DL-008) | Tabelle: `commesse`, `eventi`, `policy_clienti`, `consegne_magazzino`, `spedizioni` | Create e modificate solo da MRS. EasyJob non le tocca. |
| **Computed Facts meccanici** (DL-007) | Colonne calcolate o query in `services/` | Es. `qty_da_produrre`, `qty_disponibile_futura` |
| **Canonical Operational States** (DL-002) | Colonne `stato` sulle tabelle MRS + logica in `services/` | Es. `commessa.stato`, `spedizione.stato` |
| **Projections / Department views** (DL-002) | `routers/produzione.py`, `routers/magazzino.py`, ecc. | Assemblano dati già calcolati dai services. Non calcolano. |
| **Change sets / Dependency chain** (DL-005) | `sync/handlers.py` produce change sets → `services/` reagisce | Implementato con invalidation esplicita, non event bus |

---

## 2. Proprietà delle tabelle: chi può scrivere cosa

Regola fondamentale derivata da DL-003/004/008:

> **Le tabelle sync-owned sono scritte SOLO dal layer sync.**
> **Le tabelle MRS-owned sono scritte SOLO dai services MRS.**
> Nessun router scrive direttamente in nessuna tabella.

### Tabelle sync-owned (EasyJob → MRS)

| Tabella | Frequenza sync | Chi scrive |
|---|---|---|
| `articoli` | 60 min | `sync/handlers.py` |
| `clienti` | 60 min | `sync/handlers.py` |
| `ordini` | 5 min | `sync/handlers.py` |
| `righe_ordine` | 5 min | `sync/handlers.py` |
| `sync_log` | ad ogni sync | `sync/handlers.py` |

Queste tabelle non vengono mai modificate da services o router. Solo lette.

### Tabelle MRS-owned (create e gestite da MRS)

| Tabella | Service responsabile | Trigger di scrittura |
|---|---|---|
| `commesse` | `services/commesse.py` | Operatore produzione lancia commessa da F1a/F1b |
| `eventi` | `services/eventi.py` | Qualsiasi azione inter-reparto |
| `policy_clienti` | `services/logistica.py` | Logistica configura policy in F1 |
| `consegne_magazzino` | `services/reparto.py` | Terminale reparto — conferma consegna fisica |
| `spedizioni` | `services/logistica.py` | Logistica pianifica spedizione in F3a |
| `macchine` | `services/reparto.py` | Admin — configurazione anagrafica |

---

## 3. Computed Facts: strategia MVP

Derivato da DL-007. In MVP tutti i computed facts sono **calcolati live via query** nei services, senza materializzazione separata. Non esiste una tabella `computed_facts`.

Quando un computed fact diventa persistito:
- se è costoso da ricalcolare (es. `scorta_mensile` — ricalcolo mensile su storico 12m) → colonna sulla tabella source
- se serve coerenza snapshot (es. qty_da_produrre al momento del lancio commessa) → campo sulla tabella MRS

### Computed Facts meccanici — calcolati live

```python
# Questi non vengono mai salvati come colonne intermedie
# Vengono calcolati al momento della query nel service

qty_da_produrre = qty_ordinata - qty_disponibile - qty_in_produzione
qty_disponibile_futura = giacenza_attuale - impegni_ordini_aperti_futuri
target_scorta = scorta_mensile * mesi_scorta
qty_da_produrre_scorta = target_scorta - qty_disponibile_futura
```

### Computed Facts persistiti (eccezioni giustificate)

| Campo | Tabella | Perché persistito |
|---|---|---|
| `scorta_mensile` | `articoli` | Costoso — ricalcolo su 12 mesi di storico, eseguito 1x/mese |
| `storico_sufficiente` | `articoli` | Flag derivato dal ricalcolo mensile — coerente con `scorta_mensile` |
| `qty_prodotta_cliente` | `commesse` | Stato evolutivo — si accumula nel tempo |
| `qty_prodotta_scorta` | `commesse` | Stato evolutivo — si accumula nel tempo |

---

## 4. Propagazione cambiamenti: regola MVP

Derivato da DL-005. In MVP la propagazione è **sincrona e diretta**, senza event bus.

```
EasyJob → sync/handlers.py → aggiorna tabelle sync-owned
                           → invalida computed facts dipendenti (se persistiti)
                           → le viste ricalcolano live al prossimo accesso
```

### Regola concreta per ogni sync

Quando `sync/handlers.py` aggiorna `righe_ordine`:
1. Aggiorna i campi `qty_ordinata`, `qty_disponibile`, `qty_in_produzione`, `qty_consegnata`
2. Non fa altro — i services calcolano `qty_da_produrre` live quando la vista F1a viene caricata

Quando il ricalcolo mensile scorte gira:
1. `services/scorte.py` → `calcola_scorta_mensile()` per ogni articolo
2. Aggiorna `articoli.scorta_mensile`, `articoli.storico_sufficiente`, `articoli.scorta_calcolata_at`
3. Le viste F1b ricalcolano live al prossimo accesso

Questa semplicità è intenzionale per l'MVP. Event-driven potrà essere introdotto post-MVP senza cambiare la logica dei services.

---

## 5. Principi dai DL tradotti in regole di codice

### Da DL-001: separazione layer

```
# CORRETTO
router → chiama service → legge/scrive DB

# SBAGLIATO
router → scrive direttamente in DB
router → contiene logica di business
```

### Da DL-003: sync senza business logic

```python
# sync/handlers.py — CORRETTO
def sync_ordini(session):
    rows = fetch_from_easyjob("SELECT * FROM ordini WHERE ...")
    for row in rows:
        upsert_ordine(session, normalizza(row))  # solo normalizzazione tecnica
    update_sync_log(session, "ordini")

# sync/handlers.py — SBAGLIATO
def sync_ordini(session):
    rows = fetch_from_easyjob(...)
    for row in rows:
        if row.qty_disponibile < row.qty_ordinata:  # ← business logic nel sync
            crea_commessa(session, row)             # ← VIETATO
```

### Da DL-004: il sync assorbe la complessità della sorgente

```python
# sync/handlers.py — gestisce limiti tecnici EasyJob
# Es. righe descrizione spezzate su più record:
def ricostruisci_descrizione(righe_ej):
    """Ricompone descrizione lunga spezzata da EasyJob su più righe.
    Questo è normalizzazione tecnica — appartiene al sync, non al core."""
    return " ".join(r.descrizione_parziale for r in sorted(righe_ej, key=lambda x: x.seq))
```

### Da DL-006: il core è rigenerabile

```python
# Ogni service deve poter essere chiamato fresh senza dipendere da
# stato implicito di esecuzioni precedenti.
# CORRETTO: il service legge dal DB quello che serve e calcola
def get_f1a(session, filtri) -> list[RigaF1a]:
    righe = query_righe_ordine_aperte(session, filtri)
    return [calcola_riga_f1a(r) for r in righe]

# SBAGLIATO: dipende da cache o stato in-memory non tracciato
_cache_f1a = {}
def get_f1a(filtri):
    if filtri in _cache_f1a:
        return _cache_f1a[filtri]  # ← stato implicito non rigenerabile
```

### Da DL-008: native facts sono fonte di verità primaria per il loro dominio

```python
# commesse è MRS-owned: EasyJob NON è source of truth per lo stato commessa
# Lo stato commessa vive in MRS — EasyJob ha solo il numero LDP

# CORRETTO
def get_stato_commessa(session, commessa_id) -> StatoCommessa:
    return session.get(Commessa, commessa_id).stato  # ← legge da MRS

# SBAGLIATO
def get_stato_commessa(commessa_id):
    return fetch_from_easyjob(f"SELECT stato FROM LDP WHERE id={commessa_id}")  # ← va a EasyJob per dato MRS
```

---

## 6. Struttura services — responsabilità esplicite

Ogni file in `backend/app/services/` ha una responsabilità singola e dichiarata.

| File | Responsabilità | DL di riferimento |
|---|---|---|
| `services/scorte.py` | Algoritmo calcolo `scorta_mensile`. Funzione `calcola_scorta_mensile(articolo_id, movimenti)`. Ricalcolo batch. | DL-007 (computed fact persistito) |
| `services/commesse.py` | Creazione commessa, transizioni di stato, validazione, calcolo `qty_ciclo_corrente`. | DL-008 (native fact) |
| `services/export_easyjob.py` | `genera_riga_commessa()` separata da `esporta_su_easyjob()`. Architettura espandibile. | DL-001 (layer separation) |
| `services/priorita.py` | Calcolo `priorita_suggerita` per commessa. Input: date, policy cliente, urgenze. Output: intero 1-N. | DL-007 (computed fact meccanico) |
| `services/eventi.py` | Creazione eventi, cambio stato, lettura notifiche per reparto. | DL-008 (native fact) |
| `services/logistica.py` | Policy clienti (upsert, validazione), gestione spedizioni, urgenze. | DL-008 (native fact) |
| `services/magazzino.py` | Filtro ordini per policy, approntamento, handoff logistica. | DL-002 (projection logic) |
| `services/reparto.py` | Terminale macchina, avanzamento commessa, consegna magazzino. | DL-008 (native fact) |
| `services/disponibilita.py` | Calcolo `qty_disponibile_futura`, `qty_da_produrre`. Riusato da F1a, F1b e magazzino. | DL-007 (computed fact meccanico, cross-reparto) |

> **Regola**: se una logica serve a più di un router, sta in `services/disponibilita.py` o nel service pertinente — **mai duplicata nei router**.

---

## 7. Routers — cosa possono e non possono fare

I router sono **projection layer** (DL-002). Assemblano risposte a partire dai services.

```python
# routers/produzione.py — CORRETTO
@router.get("/f1a")
def get_f1a(session: Session = Depends(get_db), filtri: FiltriF1a = Depends()):
    righe = commesse_service.get_righe_da_processare(session, filtri)
    return [RigaF1aResponse.from_orm(r) for r in righe]

# routers/produzione.py — SBAGLIATO
@router.get("/f1a")
def get_f1a(session: Session = Depends(get_db)):
    # ← logica di filtro direttamente nel router
    righe = session.query(RigaOrdine).filter(
        RigaOrdine.qty_ordinata - RigaOrdine.qty_disponibile > 0,
        ...
    ).all()
```

---

## 8. Decisioni architetturali aperte (post-MVP)

Questi punti derivano dai DL 009–015 e sono **intenzionalmente rimandati**. Non implementare in MVP.

| Decisione | Quando | DL di origine |
|---|---|---|
| Aggregate Roots formali e rebuild boundaries | Quando lo scheduler automatico diventa operativo | DL-010 |
| Policy Governance framework con gerarchia 6 livelli | Quando le policy diventano > 5 tipi con conflitti reali | DL-011 |
| Decision Trace & Explainability model | Quando si introduce AI/suggerimento automatico | DL-012 |
| Projection schema versionati e contracts servizi | Quando si introducono servizi esterni o team multipli | DL-015 |
| Event bus per change propagation | Quando la latenza del polling diventa un problema operativo reale | DL-005 esteso |

---

## 9. Sequenza di sviluppo raccomandata

Rispetta la dependency chain naturale del sistema:

```
Fase 0: sync/ + schema DB
    ↓ (i dati ci sono)
Fase 1: services/disponibilita.py + services/scorte.py
        routers/produzione.py (F1a, F1b)
    ↓ (produzione legge)
Fase 2: services/commesse.py + services/priorita.py
        routers/produzione.py (F2)
        services/reparto.py (terminale)
    ↓ (produzione agisce, magazzino vede F5)
Fase 3: services/logistica.py (policy)
        services/magazzino.py
        routers/magazzino.py (F1-F5)
    ↓ (magazzino opera)
Fase 4: services/eventi.py
        services/logistica.py (urgenze, spedizioni)
        routers/logistica.py (F2, F3a, F3b, F3c)
        Calendario condiviso
```

---

## 10. Riferimenti

- `MRS_Specifiche_Tecniche_v1.docx` — schema DB completo, API endpoints, logiche operative per reparto
- `DL-ARCH-001` — architettura 3-layer: sync / core / app
- `DL-ARCH-002` — modello fact-centric: source facts → computed facts → operational states → projections
- `DL-ARCH-003` — layer sync: capability di riallineamento, non business logic
- `DL-ARCH-004` — confine sync/core: source-oriented vs domain-oriented
- `DL-ARCH-005` — change propagation: change sets espliciti, dependency chain
- `DL-ARCH-006` — rigenerabilità core: da EasyJob si ricostruisce tutto, zero stato implicito
- `DL-ARCH-007` — computed facts: livello intermedio tra source facts e operational states
- `DL-ARCH-008` — native MRS facts: il sistema non è EasyJob-centric, ma core-centric

---

*MRS — Documento di contesto per Claude Code | Marzo 2026*
*Versione 1.0 — da aggiornare ad ogni decisione architetturale rilevante*
