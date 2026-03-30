# MRS Backend — API Reference

> **Base URL:** `http://localhost:8000`
> **Formato:** JSON
> **Auth:** `Authorization: Bearer <token>` (dove richiesto — vedi `03_AUTH.md`)

## Indice
- [Health](#health)
- [Auth — /api/auth](#auth----apiauth)
- [Articoli — /api/articoli](#articoli----apiarticoli)
- [Produzione — /api/produzione](#produzione----apiproduzione)
- [Reparto — /api/reparto](#reparto----apireparto-kiosk-no-auth)
- [Magazzino — /api/magazzino](#magazzino----apimagazzino-kiosk-no-auth)
- [Logistica — /api/logistica](#logistica----apilogistica)
- [Eventi — /api/eventi](#eventi----apieventi)
- [Sync — /api/sync](#sync----apisync)
- [Tipi comuni](#tipi-comuni)

---

## Health

### GET /health
Stato del server. Sempre pubblico.

**Response 200:**
```json
{"status": "ok", "version": "1.0.0"}
```

---

## Auth — /api/auth

### POST /api/auth/login *(pubblico)*
Vedi `03_AUTH.md` per dettagli completi.

**Request:** `{"username": str, "password": str}`
**Response 200:** `TokenResponse`
**401** — credenziali errate o utente disabilitato

---

### GET /api/auth/me *(get_current_user)*
Payload del token corrente.

**Response 200:**
```json
{"sub": "uuid", "username": "mario", "ruolo": "produzione", "exp": 1743000000}
```

---

### POST /api/auth/utenti *(require_admin)*
Crea utente. **201**.

**Request:**
```json
{"username": "lucia", "password": "pass123", "ruolo": "logistica"}
```
**Response 201:** `UtenteResponse`
**409** — username duplicato | ruolo invalido

---

### GET /api/auth/utenti *(require_admin)*
Lista tutti gli utenti.

**Response 200:** `UtenteResponse[]`

---

### PATCH /api/auth/utenti/{id} *(require_admin)*
Aggiorna password / ruolo / attivo.

**Request** (tutti opzionali):
```json
{"password": "nuova", "ruolo": "produzione", "attivo": false}
```
**Response 200:** `UtenteResponse`
**409** — utente non trovato | ruolo invalido

---

## Articoli — /api/articoli

> Guard: `get_current_user` (tutti i ruoli)

### GET /api/articoli
Lista articoli con filtri opzionali.

**Query params:**
| Parametro | Tipo | Descrizione |
|---|---|---|
| `categoria` | `string` | Filtra per categoria |
| `tipo_produzione` | `string` | `PEZZO` \| `BARRA` \| `FASCI` |
| `storico_sufficiente` | `boolean` | `true` \| `false` |

**Response 200:** `ArticoloResponse[]`

---

### GET /api/articoli/{id}
**Response 200:** `ArticoloResponse`
**404** — articolo non trovato

---

### PATCH /api/articoli/{id}
Aggiorna solo i campi **MRS-owned** dell'articolo. I campi sync (codice, descrizione, synced_at) non vengono mai toccati.

**Request** (tutti opzionali):
```json
{
  "mesi_scorta": 6,
  "tipo_produzione": "BARRA",
  "multipli_taglio": 5,
  "capienza": 20,
  "prd_pari": true
}
```
**Response 200:** `ArticoloResponse`
**404** — articolo non trovato

---

## Produzione — /api/produzione

> Guard: `require_ruolo("produzione")` — ammessi: `produzione`, `admin`

### GET /api/produzione/f1a
Lista righe ordine che l'ufficio produzione deve ancora processare (qty_da_produrre > 0, nessuna commessa attiva).

**Query params:**
| Parametro | Tipo | Descrizione |
|---|---|---|
| `cliente_id` | `string` | UUID cliente |
| `data_da` | `date` | Filtra per data_consegna >= |
| `data_a` | `date` | Filtra per data_consegna <= |
| `urgenza_only` | `boolean` | Solo righe con urgenza_formale aperta |

**Response 200:** `RigaF1aResponse[]`

**Esempio risposta:**
```json
[
  {
    "riga_ordine_id": "uuid",
    "ordine_id": "uuid",
    "numero_ordine": "ORD-001",
    "data_consegna": "2026-04-15",
    "flag_data_scaduta": false,
    "flag_urgenza": false,
    "codice_articolo": "ART001",
    "descrizione_articolo": "Bullone M10",
    "cliente": "Cliente SRL",
    "cliente_id": "uuid",
    "qty_ordinata": 100,
    "qty_disponibile": 20,
    "qty_in_produzione": 0,
    "qty_da_produrre": 80
  }
]
```

---

### POST /api/produzione/genera-commesse
Per ogni riga selezionata: verifica disponibilità, crea commessa `in_coda`, genera file Excel per EasyJob.

**Request:**
```json
{
  "righe": [
    {
      "riga_ordine_id": "uuid",
      "qty_ciclo_corrente": null,
      "qty_scorta": 0
    }
  ],
  "created_by": "mario"
}
```

**Response 200:** `GeneraCommesseResponse`
```json
{
  "commesse_create": 2,
  "file_excel_base64": "UEsDBBQAA..."
}
```

> Il campo `file_excel_base64` è il file `.xlsx` codificato in base64. Per scaricarlo dal frontend:
> ```javascript
> const bytes = atob(data.file_excel_base64)
> const blob = new Blob([bytes], {type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'})
> const url = URL.createObjectURL(blob)
> // trigger download...
> ```

**404** — riga ordine non trovata

---

### GET /api/produzione/f1b
Lista articoli con storico sufficiente e quantità disponibile futura sotto il target scorta.

**Query params:** `categoria`, `tipo_produzione`

**Response 200:** `ArticoloF1bResponse[]`
```json
[
  {
    "articolo_id": "uuid",
    "codice": "ART001",
    "descrizione": "Bullone M10",
    "tipo_produzione": "PEZZO",
    "scorta_mensile": 50,
    "mesi_scorta": 3,
    "target_scorta": 150,
    "qty_disponibile_futura": 30,
    "qty_da_produrre_scorta": 120,
    "scorta_calcolata_at": "2026-03-01T02:00:00Z"
  }
]
```

---

### POST /api/produzione/ricalcola-scorte
Forza ricalcolo `scorta_mensile` per tutti gli articoli o uno specifico. Legge storico vendite da EasyJob (MAG_REALE). Se EasyJob non è raggiungibile, torna `aggiornati: 0`.

**Request:**
```json
{"articolo_id": "uuid"}  // null = tutti
```

**Response 200:**
```json
{"aggiornati": 15}
```

---

### GET /api/produzione/coda
Lista commesse attive (`in_coda`, `in_produzione`, `sospesa`) ordinate per posizione coda.

**Response 200:** `CommessaResponse[]`

---

### POST /api/produzione/coda/riordina
Aggiorna manualmente le posizioni in coda (es. dopo drag&drop).

**Request:**
```json
{
  "ordine": [
    {"commessa_id": "uuid", "posizione": 1},
    {"commessa_id": "uuid", "posizione": 2}
  ]
}
```

**Response 200:** `{"aggiornate": 2}`

---

### POST /api/produzione/coda/ricalcola-priorita
Ricalcola `posizione_coda` e `priorita_suggerita` secondo l'algoritmo standard:
1. Urgenze attive → top (priorita_suggerita=1)
2. Data consegna ASC (prima le più vicine)
3. FIFO (created_at ASC)
4. Commesse senza ordine → fondo

**Response 200:** `{"aggiornate": N}`

---

### POST /api/produzione/commesse/{id}/assegna
Assegna una macchina a una commessa `in_coda` o `sospesa`.

**Request:** `{"macchina_id": "uuid"}`
**Response 200:** `CommessaResponse`
**404** — macchina non trovata
**409** — commessa non in stato assegnabile

---

### GET /api/produzione/macchine
Lista macchine.

**Query params:** `solo_attive` (boolean, default `true`)

**Response 200:** `MacchinaResponse[]`

---

## Reparto — /api/reparto *(kiosk, no auth)*

> Nessun JWT richiesto. Terminale fisico fisso in reparto produzione.

### GET /api/reparto/macchine
Lista macchine attive (per selezione operatore all'avvio terminale).

**Response 200:** `MacchinaResponse[]`

---

### GET /api/reparto/macchine/{macchina_id}/coda
Commesse assegnate a questa macchina, non completate.

**Response 200:** `CommessaResponse[]`
**404** — macchina non trovata

---

### GET /api/reparto/commesse/{commessa_id}
Dettaglio singola commessa.

**Response 200:** `CommessaResponse`
**404** — commessa non trovata

---

### POST /api/reparto/commesse/{commessa_id}/avvia
`in_coda` → `in_produzione`

**Response 200:** `CommessaResponse`
**409** — stato non corretto per questa transizione

---

### POST /api/reparto/commesse/{commessa_id}/sospendi
`in_produzione` → `sospesa`

**Request:**
```json
{"nota": "attesa materiale"}
```
**Response 200:** `CommessaResponse` (con `sospesa_at` e `sospesa_nota` valorizzati)
**409** — stato non corretto

---

### POST /api/reparto/commesse/{commessa_id}/riprendi
`sospesa` → `in_produzione`

**Response 200:** `CommessaResponse`
**409** — stato non corretto

---

### POST /api/reparto/commesse/{commessa_id}/completa
`in_produzione` → `completata`

**Response 200:** `CommessaResponse` (con `completata_at` valorizzato)
**409** — stato non corretto

---

### POST /api/reparto/commesse/{commessa_id}/aggiorna-qty
Aggiorna quantità prodotte durante la lavorazione (solo `in_produzione` o `sospesa`).

**Request** (entrambi opzionali):
```json
{
  "qty_prodotta_cliente": 40,
  "qty_prodotta_scorta": 5
}
```
**Response 200:** `CommessaResponse`
**409** — commessa non in stato modificabile

---

## Magazzino — /api/magazzino *(kiosk, no auth)*

> Nessun JWT richiesto. Terminale fisico fisso in magazzino.

### GET /api/magazzino/da-approntare
Ordini con almeno una commessa completata non ancora registrata come consegna, raggruppati per ordine.

**Response 200:** `OrdineApprontareResponse[]`
```json
[
  {
    "ordine_id": "uuid",
    "numero_ordine": "ORD-001",
    "data_consegna": "2026-04-15",
    "cliente": "Cliente SRL",
    "cliente_id": "uuid",
    "flag_urgenza": false,
    "tutte_registrate": false,
    "articoli": [
      {
        "commessa_id": "uuid",
        "articolo_id": "uuid",
        "codice_articolo": "ART001",
        "descrizione_articolo": "Bullone M10",
        "qty_prodotta_cliente": 80,
        "qty_prodotta_scorta": 0,
        "qty_totale": 80,
        "gia_registrata": false
      }
    ]
  }
]
```

---

### POST /api/magazzino/consegne
Registra che il magazzino ha messo da parte i pezzi di una commessa completata. Una sola registrazione per commessa.

**Request:**
```json
{
  "commessa_id": "uuid",
  "qty_cliente": 80,
  "qty_scorta": 0
}
```
**Response 201:** `ConsegnaResponse`
```json
{
  "id": "uuid",
  "commessa_id": "uuid",
  "articolo_id": "uuid",
  "codice_articolo": "ART001",
  "descrizione_articolo": "Bullone M10",
  "qty_consegnata": 80,
  "quota": "cliente",
  "qty_cliente": 80,
  "qty_scorta": 0,
  "stato": "in_attesa",
  "registrata_ej_at": null,
  "created_at": "2026-03-30T10:00:00Z"
}
```

> **quota** calcolato automaticamente:
> - `"cliente"` se `qty_scorta == 0`
> - `"scorta"` se `qty_cliente == 0`
> - `"mista"` se entrambi > 0

**409** — commessa già registrata | commessa non completata | commessa non trovata

---

### GET /api/magazzino/ordini/{ordine_id}/consegne
Lista consegne registrate per un ordine.

**Response 200:** `ConsegnaResponse[]`

---

### POST /api/magazzino/ordini/{ordine_id}/pronto
Crea evento `ordine_pronto` destinato alla logistica. **Idempotente**: se l'evento esiste già (aperto o in_lavorazione), lo ritorna senza crearne uno nuovo.

**Request:**
```json
{"nota": "tutto ok", "created_by": "operatore_1"}
```
**Response 201:** `EventoResponse` (semplificato — senza join ordine/cliente)
```json
{
  "id": "uuid",
  "tipo": "ordine_pronto",
  "mittente": "magazzino",
  "destinatario": "logistica",
  "stato": "aperto",
  "nota": "tutto ok",
  "ref_ordine_id": "uuid",
  "created_at": "2026-03-30T10:00:00Z"
}
```
**404** — ordine non trovato

---

## Logistica — /api/logistica

> Guard: `require_ruolo("logistica")` — ammessi: `logistica`, `admin`

### GET /api/logistica/clienti
Lista clienti con indicazione policy configurata.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "codice_easyjob": "CLI001",
    "ragione_sociale": "Rossi SRL",
    "nickname": "Rossi",
    "email": "ordini@rossi.it",
    "ha_policy": true,
    "tipo_policy": "GIORNO_FISSO",
    "corriere_preferito": "BRT"
  }
]
```

---

### PATCH /api/logistica/clienti/{cliente_id}
Aggiorna il nickname operativo (campo MRS-owned, non sovrascritto dal sync).

**Request:** `{"nickname": "Rossi"}`
**Response 204** (no body)
**404** — cliente non trovato

---

### GET /api/logistica/clienti/{cliente_id}/policy
**Response 200:** `PolicyClienteResponse`
**404** — policy non configurata per questo cliente

---

### PUT /api/logistica/clienti/{cliente_id}/policy
Crea o aggiorna la policy del cliente (idempotente).

**Request:**
```json
{
  "tipo_policy": "GIORNO_FISSO",
  "giorno_fisso": 3,
  "corriere_preferito": "GLS",
  "note_spedizione": "Consegnare al mattino"
}
```
Campi opzionali: `giorno_fisso`, `soglia_valore`, `corriere_preferito`, `note_spedizione`

**Response 200:** `PolicyClienteResponse`
**404** — cliente non trovato

---

### GET /api/logistica/da-spedire
Ordini con evento `ordine_pronto` aperto, arricchiti con policy e data di spedizione suggerita.

**Response 200:**
```json
[
  {
    "ordine_id": "uuid",
    "numero_ordine": "ORD-001",
    "data_consegna": "2026-04-15",
    "cliente": "Rossi SRL",
    "cliente_id": "uuid",
    "tipo_policy": "GIORNO_FISSO",
    "corriere_suggerito": "GLS",
    "data_spedizione_suggerita": "2026-04-09",
    "soglia_raggiunta": null,
    "flag_urgenza": false,
    "evento_id": "uuid"
  }
]
```

---

### POST /api/logistica/spedizioni
Crea una nuova spedizione per un ordine.

**Request:**
```json
{
  "ordine_id": "uuid",
  "tipo": "totale",
  "corriere": "BRT",
  "data_pianificata": "2026-04-09",
  "colli": 3,
  "peso_kg": 12.5,
  "note": null
}
```
**Response 201:** `SpedizioneResponse`
**404** — ordine non trovato

---

### GET /api/logistica/spedizioni
**Query params:** `stato` (opzionale), `cliente_id` (opzionale)

**Response 200:** `SpedizioneResponse[]`

---

### GET /api/logistica/spedizioni/{spedizione_id}
**Response 200:** `SpedizioneResponse`
**404** — spedizione non trovata

---

### PATCH /api/logistica/spedizioni/{spedizione_id}
Aggiorna corriere, data pianificata, colli, peso, note. Non modificabile se già `spedita` o `annullata`.

**Request** (tutti opzionali):
```json
{
  "corriere": "DHL",
  "data_pianificata": "2026-04-10",
  "colli": 4,
  "peso_kg": 15.0,
  "note": "fragile"
}
```
**Response 200:** `SpedizioneResponse`
**409** — spedizione già spedita/annullata | spedizione non trovata

---

### POST /api/logistica/spedizioni/{spedizione_id}/spedita
Segna la spedizione come spedita (`data_spedizione = oggi`).

**Response 200:** `SpedizioneResponse` (con `stato: "spedita"` e `data_spedizione` valorizzata)
**409** — già spedita | annullata | non trovata

---

### GET /api/logistica/calendario
Vista spedizioni pianificate in un range di date, raggruppate per giorno.

**Query params:**
| Parametro | Default | Descrizione |
|---|---|---|
| `data_da` | oggi | Data inizio range |
| `data_a` | 28 del mese corrente | Data fine range |

**Response 200:** `CalendarioGiornoItem[]`
```json
[
  {
    "data": "2026-04-09",
    "spedizioni": [
      {
        "id": "uuid",
        "ordine_id": "uuid",
        "numero_ordine": "ORD-001",
        "cliente": "Rossi SRL",
        "tipo": "totale",
        "stato": "in_preparazione",
        "corriere": "BRT",
        "data_pianificata": "2026-04-09",
        "data_spedizione": null,
        "colli": 3,
        "peso_kg": 12.5,
        "note": null,
        "created_at": "..."
      }
    ]
  }
]
```
**400** — `data_a < data_da`

---

## Eventi — /api/eventi

> Guard: `get_current_user` (tutti i ruoli autenticati)

### GET /api/eventi
Lista eventi con filtri opzionali, ordinati per `created_at` DESC.

**Query params:** `tipo`, `destinatario`, `stato`, `ref_ordine_id`

**Response 200:** `EventoResponse[]`

---

### GET /api/eventi/{evento_id}
**Response 200:** `EventoResponse`
**404** — evento non trovato

---

### POST /api/eventi/urgenza
Logistica crea un'urgenza formale su un ordine. La coda di lavorazione viene ricalcolata automaticamente.

**Request:**
```json
{
  "ordine_id": "uuid",
  "nota": "cliente VIP — consegna entro venerdì",
  "created_by": "lucia"
}
```
**Response 201:** `EventoResponse`
**404** — ordine non trovato

---

### POST /api/eventi/{evento_id}/feedback
La produzione risponde a un'urgenza. Valido solo per eventi `urgenza_formale` in stato `aperto` o `in_lavorazione`.

**Request:**
```json
{
  "feedback_stato": "accettata",
  "feedback_data_prevista": null,
  "feedback_nota": "acceleriamo i tempi",
  "corriere_override": null
}
```
oppure:
```json
{
  "feedback_stato": "non_fattibile",
  "feedback_data_prevista": "2026-04-20",
  "feedback_nota": "macchina in manutenzione fino al 18",
  "corriere_override": "BRT"
}
```
**Response 200:** `EventoResponse` (con `stato: "in_lavorazione"`)
**409** — evento non trovato | tipo non corretto | stato non corretto | feedback_stato invalido

---

### POST /api/eventi/{evento_id}/risolvi
Segna l'evento come risolto. Per `urgenza_formale`: ricalcola la coda (la commessa torna in posizione normale).

**Request:** `{"nota": "problema risolto"}`
**Response 200:** `EventoResponse` (con `stato: "risolto"` e `resolved_at` valorizzato)
**409** — evento già risolto/rifiutato

---

### POST /api/eventi/{evento_id}/rifiuta
Rifiuta o annulla un evento aperto.

**Request:** `{"nota": "falso allarme"}`
**Response 200:** `EventoResponse` (con `stato: "rifiutato"`)
**409** — evento già risolto/rifiutato

---

## Sync — /api/sync

> Guard: `require_admin`

### GET /api/sync/status
Stato sync per ogni tabella + stato connessione EasyJob.

**Response 200:**
```json
{
  "easyjob_connesso": true,
  "tabelle": [
    {
      "tabella": "articoli",
      "last_sync_at": "2026-03-30T09:00:00Z",
      "last_error": null,
      "records_updated": 450,
      "sync_duration_ms": 1240
    },
    {
      "tabella": "ordini",
      "last_sync_at": "2026-03-30T09:55:00Z",
      "last_error": null,
      "records_updated": 12,
      "sync_duration_ms": 320
    }
  ]
}
```

> **Interpretazione `last_sync_at` per indicatore colore:**
> - Verde: < 10 minuti fa
> - Giallo: 10–30 minuti fa
> - Rosso: > 30 minuti fa o `last_error != null`

---

### POST /api/sync/force/{tabella}
Forza sync immediato di una tabella specifica.

**Tabelle valide:** `articoli`, `clienti`, `ordini_e_righe`

**Response 200:**
```json
{"tabella": "articoli", "records_updated": 450, "status": "ok"}
```
**404** — tabella non supportata
**500** — errore durante il sync

---

### POST /api/sync/force-all
Forza sync completo di tutte le tabelle in ordine di dipendenze.

**Response 200:**
```json
{"status": "ok", "results": {"articoli": 450, "clienti": 85, "ordini_e_righe": 120}}
```

---

## Tipi comuni

### UtenteResponse
```typescript
{
  id: string
  username: string
  ruolo: "admin" | "produzione" | "logistica" | "magazzino"
  attivo: boolean
  created_at: string  // ISO 8601
}
```

### ArticoloResponse
```typescript
{
  id: string
  codice: string
  codice_upper: string
  descrizione: string | null
  categoria: string | null
  capienza: number | null
  scorta_mensile: number
  mesi_scorta: number
  tipo_produzione: "PEZZO" | "BARRA" | "FASCI"
  lunghezza_barra: number | null
  multipli_taglio: number | null
  prd_pari: boolean
  storico_sufficiente: boolean
  scorta_calcolata_at: string | null
  synced_at: string
}
```

### CommessaResponse
```typescript
{
  id: string
  stato: "in_coda" | "in_produzione" | "sospesa" | "completata"
  posizione_coda: number | null
  priorita_suggerita: 1 | 2 | null   // 1=urgente, 2=normale
  qty_cliente: number
  qty_scorta: number
  qty_prodotta_cliente: number
  qty_prodotta_scorta: number
  qty_totale: number          // calcolato: qty_cliente + qty_scorta
  qty_residua: number         // calcolato: max(0, totale - prodotta)
  qty_ciclo_corrente: number | null
  riga_ordine_id: string | null
  articolo_id: string
  macchina_id: string | null
  codice_articolo: string
  descrizione_articolo: string | null
  macchina_codice: string | null
  numero_ordine: string | null
  created_at: string
  created_by: string | null
  sospesa_at: string | null
  sospesa_nota: string | null
  completata_at: string | null
  ldp_easyjob: string | null
}
```

### MacchinaResponse
```typescript
{
  id: string
  codice: string
  nome: string
  operazioni_eseguibili: string[]
  stato: "disponibile" | "in_lavorazione" | "in_setup" | "in_manutenzione"
  setup_corrente: string | null
  attiva: boolean
}
```

### EventoResponse (completo, con join)
```typescript
{
  id: string
  tipo: "urgenza_formale" | "ordine_pronto"
  mittente: string
  destinatario: string
  stato: "aperto" | "in_lavorazione" | "risolto" | "rifiutato"
  ref_ordine_id: string | null
  numero_ordine: string | null   // da join
  cliente: string | null         // da join (nickname || ragione_sociale)
  ref_commessa_id: string | null
  ref_articolo_id: string | null
  nota: string | null
  feedback_stato: "accettata" | "non_fattibile" | null
  feedback_data_prevista: string | null  // date ISO
  feedback_nota: string | null
  corriere_override: string | null
  created_at: string
  updated_at: string
  resolved_at: string | null
}
```

### SpedizioneResponse
```typescript
{
  id: string
  ordine_id: string
  numero_ordine: string | null
  cliente: string | null
  tipo: "totale" | "parziale"
  stato: "in_preparazione" | "spedita" | "annullata"
  corriere: string | null
  data_pianificata: string | null   // date ISO
  data_spedizione: string | null    // date ISO
  colli: number | null
  peso_kg: number | null
  note: string | null
  created_at: string
}
```

### PolicyClienteResponse
```typescript
{
  id: string
  cliente_id: string
  tipo_policy: "GIORNO_FISSO" | "DATA_TASSATIVA" | "SOGLIA_VALORE" | "DEFAULT"
  giorno_fisso: number | null        // 1=Lun, 7=Dom
  soglia_valore: number | null
  corriere_preferito: string | null
  note_spedizione: string | null
  policy_json: object | null
  configurata_da: string | null
  updated_at: string
}
```
