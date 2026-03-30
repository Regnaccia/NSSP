# DL-ARCH-019 — State machine commesse centralizzata in services/

## Stato
Approvato

## Data
2026-03-27

---

## Decisione

Tutta la logica di transizione di stato delle commesse vive esclusivamente in `app/services/commesse.py`. I router chiamano solo la funzione `transizione(session, id, azione)` — non gestiscono mai direttamente il campo `stato`.

## Motivazione

### Stato come invariante di dominio

Le commesse hanno transizioni di stato con invarianti precisi:

- Non si può avviare una commessa già in produzione
- Non si può completare una commessa sospesa (bisogna prima riprenderla)
- Il campo `sospesa_at` deve essere scritto quando e solo quando si entra in `sospesa`
- Il campo `completata_at` deve essere scritto quando e solo quando si completa

Se la logica fosse distribuita nei router, ogni router dovrebbe replicare questi controlli — con il rischio di dimenticarne uno.

### Tabella transizioni come fonte unica di verità

```python
TRANSIZIONI_VALIDE = {
    "avvia":    ("in_coda",       "in_produzione"),
    "sospendi": ("in_produzione", "sospesa"),
    "riprendi": ("sospesa",       "in_produzione"),
    "completa": ("in_produzione", "completata"),
}
```

Aggiungere una nuova transizione richiede solo una riga in questo dict + eventuali effetti collaterali nella funzione `transizione()`. I router non cambiano.

### Errore di dominio separato da HTTP

`CommessaError` è un'eccezione di dominio pura — non sa nulla di HTTP. Il router la cattura e la trasforma in `HTTPException(409)`. Questo permette di testare la state machine senza avviare l'applicazione web.

## Diagramma stati

```
                    ┌─────────┐
    (crea commessa) │ in_coda │
  ─────────────────►│         │
                    └────┬────┘
                         │ avvia
                         ▼
                  ┌──────────────┐      completa    ┌────────────┐
                  │ in_produzione│ ────────────────► │ completata │
                  └──────┬───────┘                   └────────────┘
                         │ sospendi
                         ▼
                    ┌─────────┐
                    │ sospesa │
                    └────┬────┘
                         │ riprendi
                         └──────────► in_produzione
```

## Conseguenze

- Ogni nuovo endpoint che modifica lo stato di una commessa **deve** passare per `services/commesse.transizione()`.
- Scritture dirette a `commessa.stato` nei router sono vietate.
- La funzione ritorna sempre il dict aggiornato (via `get_commessa_detail`) — il router non deve fare un secondo round-trip.

## Estensioni future

Se in Fase 4 i cambi di stato devono generare eventi automatici (es. completare una commessa → crea evento "pronta per magazzino"), il punto di integrazione è `transizione()`, non i router.
