# IMPLEMENTATION V1 — Fase 3: Magazzino + Logistica

*Data: 2026-03-30*

---

## Obiettivo

Completare il flusso dopo la produzione:

- **Magazzino** — Vede le commesse completate, registra cosa ha approntato per ciascun ordine, segnala l'ordine pronto alla logistica
- **Logistica** — Riceve gli ordini pronti, applica la policy cliente per decidere quando spedire, gestisce il ciclo di vita delle spedizioni

Prerequisito: Fase 2 completata, commesse vengono completate dal reparto.

---

## File creati

### `app/schemas/magazzino.py`

| Schema | Uso |
|---|---|
| `ArticoloProntoItem` | Un articolo pronto per l'approntamento (commessa_id, qty, flag gia_registrata) |
| `OrdineApprontareResponse` | Ordine con lista articoli pronti e flag `tutte_registrate` |
| `RegistraConsegnaRequest` | Body POST consegne (commessa_id, qty_cliente, qty_scorta) |
| `ConsegnaResponse` | Consegna registrata con dettagli articolo e quota |
| `OrdineProontoRequest` | Body POST pronto (nota opzionale, created_by) |
| `EventoResponse` | Evento creato (tipo, mittente, destinatario, stato) |

### `app/schemas/logistica.py`

| Schema | Uso |
|---|---|
| `PolicyClienteResponse` | Policy completa di un cliente |
| `PolicyClienteRequest` | Body PUT policy (tipo, giorno_fisso, soglia_valore, corriere, note) |
| `OrdineDaSpedireResponse` | Ordine pronto arricchito con tipo_policy, corriere_suggerito, data_spedizione_suggerita |
| `ClienteLogisticaResponse` | Cliente con flag ha_policy e tipo_policy |
| `ClienteNicknamePatch` | Body PATCH nickname cliente |
| `SpedizioneCreateRequest` | Body POST spedizione (ordine_id, tipo, corriere, data, colli, peso, note) |
| `SpedizionePatchRequest` | Body PATCH spedizione (tutti i campi opzionali) |
| `SpedizioneResponse` | Spedizione con numero_ordine e cliente da join |
| `CalendarioGiornoItem` | Una giornata nel calendario con lista spedizioni |

---

### `app/services/magazzino.py`

**`get_ordini_da_approntare(session) → list[dict]`**

Ritorna gli ordini con almeno una commessa `completata` e `qty_prodotta_cliente > 0`.
Per ogni ordine raggruppa gli articoli pronti, con flag `gia_registrata` che indica se il magazzino ha già creato il record consegna.

**`registra_consegna(session, commessa_id, qty_cliente, qty_scorta) → dict`**

Crea un record `ConsegnaMagazzino`. Determina automaticamente la `quota`:
- `qty_cliente > 0` e `qty_scorta > 0` → `"mista"`
- Solo `qty_scorta > 0` → `"scorta"`
- Altrimenti → `"cliente"`

Errore 409 se la commessa non è `completata` o se la consegna è già registrata.

**`get_consegne_ordine(session, ordine_id) → list[dict]`**

Lista consegne registrate per un ordine (join articolo per descrizione).

**`segna_ordine_pronto(session, ordine_id, nota, created_by) → Evento`**

Crea evento `tipo='ordine_pronto'`, `mittente='magazzino'`, `destinatario='logistica'`.
**Idempotente**: se esiste già un evento aperto per quell'ordine, lo ritorna senza crearne un duplicato.

---

### `app/services/logistica.py`

**`get_policy(session, cliente_id) → PolicyCliente | None`**

Ritorna la policy del cliente o `None` se non configurata.

**`upsert_policy(session, cliente_id, data) → PolicyCliente`**

Crea o aggiorna la policy. Usa UPDATE se esiste, INSERT se non esiste.

**`calcola_data_spedizione_suggerita(tipo_policy, giorno_fisso, data_consegna) → date | None`**

| Tipo policy | Logica |
|---|---|
| `DATA_TASSATIVA` | Ritorna `data_consegna` dell'ordine |
| `GIORNO_FISSO` | Prossimo giorno della settimana (1=Lun…7=Dom) dalla data odierna, non oltre `data_consegna` |
| `SOGLIA_VALORE` | `None` — richiede verifica separata via `_soglia_raggiunta()` |
| `DEFAULT` | `None` — operatore decide |

**`_soglia_raggiunta(session, cliente_id, soglia_valore) → bool`**

Per policy `SOGLIA_VALORE`: verifica se la somma delle `qty_ordinata` degli ordini pronti del cliente supera `soglia_valore`. Usa qty come proxy del valore (prezzi non presenti in MRS in MVP).

**`get_ordini_da_spedire(session) → list[dict]`**

Ordini con evento `ordine_pronto` aperto. Arricchisce ogni ordine con:
- policy del cliente (tipo, corriere, data suggerita)
- `soglia_raggiunta` per policy `SOGLIA_VALORE`
- `flag_urgenza`

**`get_clienti_con_policy(session) → list[dict]`**

Lista clienti con indicazione policy. Ordina per `nickname || ragione_sociale`.

**`aggiorna_nickname(session, cliente_id, nickname)`**

Aggiorna il nickname operativo (MRS-owned, DL-ARCH-017). Non tocca `ragione_sociale`.

**`crea_spedizione(session, data) → dict`**

Crea record `Spedizione` con `stato='in_preparazione'`. Verifica che l'ordine esista.

**`aggiorna_spedizione(session, id, data) → dict`**

Aggiorna corriere, data, colli, peso. Errore 409 se già `spedita` o `annullata`.

**`segna_spedita(session, id) → dict`**

Imposta `stato='spedita'` e `data_spedizione=today()`.

**`get_spedizioni(session, stato, cliente_id) → list[dict]`**

Lista con filtri opzionali. Include join numero_ordine e cliente.

**`get_calendario(session, data_da, data_a) → list[dict]`**

Spedizioni pianificate nel range, raggruppate per giorno `[{data, spedizioni: [...]}]`.

---

### `app/routers/magazzino.py`

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/magazzino/da-approntare` | Ordini con commesse completate da approntare |
| `POST` | `/api/magazzino/consegne` | Registra consegna da commessa (201) |
| `GET` | `/api/magazzino/ordini/{id}/consegne` | Consegne di un ordine |
| `POST` | `/api/magazzino/ordini/{id}/pronto` | Segnala ordine pronto a logistica (201) |

### `app/routers/logistica.py`

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/logistica/da-spedire` | Ordini pronti con policy e data suggerita |
| `GET` | `/api/logistica/clienti` | Lista clienti con policy |
| `PATCH` | `/api/logistica/clienti/{id}` | Aggiorna nickname (204) |
| `GET` | `/api/logistica/clienti/{id}/policy` | Policy di un cliente |
| `PUT` | `/api/logistica/clienti/{id}/policy` | Configura/aggiorna policy |
| `POST` | `/api/logistica/spedizioni` | Crea spedizione (201) |
| `GET` | `/api/logistica/spedizioni` | Lista spedizioni (filtri: stato, cliente_id) |
| `GET` | `/api/logistica/spedizioni/{id}` | Dettaglio spedizione |
| `PATCH` | `/api/logistica/spedizioni/{id}` | Aggiorna spedizione |
| `POST` | `/api/logistica/spedizioni/{id}/spedita` | Segna come spedita |
| `GET` | `/api/logistica/calendario` | Calendario spedizioni (data_da, data_a) |

---

## Flusso completo end-to-end

```
EasyJob  →  sync  →  ordini/righe (DB)
                           │
                    F1a (produzione)
                           │ genera-commesse
                           ▼
                     Commessa in_coda
                           │ avvia (reparto)
                           ▼
                   Commessa in_produzione
                           │ completa (reparto)
                           ▼
                    Commessa completata
                           │
                  /da-approntare (magazzino)
                           │ POST /consegne
                           ▼
                ConsegnaMagazzino in_attesa
                           │ POST /pronto
                           ▼
              Evento ordine_pronto → logistica
                           │
                   /da-spedire (logistica)
                           │ POST /spedizioni
                           ▼
                  Spedizione in_preparazione
                           │ POST /spedita
                           ▼
                    Spedizione spedita
```

---

## Errori gestiti

| Condizione | HTTP | Dove |
|---|---|---|
| Commessa non trovata | 404 | registra_consegna |
| Commessa non completata | 409 | registra_consegna |
| Consegna già registrata per commessa | 409 | registra_consegna |
| Ordine non trovato (segna pronto) | 404 | segna_ordine_pronto |
| Cliente non trovato | 404 | upsert_policy, aggiorna_nickname |
| Spedizione non trovata | 404 | aggiorna, segna_spedita |
| Spedizione già spedita/annullata | 409 | aggiorna, segna_spedita |
| data_a < data_da nel calendario | 400 | router calendario |

---

## Decisioni architetturali applicate

| Decisione | Come implementato |
|---|---|
| DL-ARCH-017 (nickname) | `aggiorna_nickname` in logistica; sync non tocca mai questo campo |
| Evento idempotente | `segna_ordine_pronto` verifica se evento già aperto prima di crearne uno nuovo |
| Soglia valore senza prezzi | Usa `qty_ordinata` come proxy — prezzi non presenti in MRS MVP |
| Policy upsert | Una sola policy per cliente (`UNIQUE cliente_id`); PUT fa sempre upsert |

---

## Fase successiva — Fase 4

```
services/eventi.py       # urgenze formali, feedback, calendario condiviso
routers/eventi.py        # API eventi inter-reparto
Auth JWT                 # login, middleware, protezione endpoint
```
