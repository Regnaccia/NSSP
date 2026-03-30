# MRS — Manufacturing Resource System
## Specifiche Tecniche Unificate — v1.0

*Documento di riferimento per lo sviluppo con Claude Code | Marzo 2026*

---

## Indice

1. [Contesto e Obiettivi](#1-contesto-e-obiettivi)
2. [Stack Tecnico e Struttura Progetto](#2-stack-tecnico-e-struttura-progetto)
3. [Schema Database — PostgreSQL](#3-schema-database--postgresql)
4. [Integrazione EasyJob — Sync](#4-integrazione-easyjob--sync)
5. [Modulo Ufficio Produzione](#5-modulo-ufficio-produzione)
6. [Modulo Reparto Produzione](#6-modulo-reparto-produzione)
7. [Modulo Magazzino](#7-modulo-magazzino)
8. [Modulo Logistica](#8-modulo-logistica)
9. [Modulo Eventi Trasversale](#9-modulo-eventi-trasversale)
10. [Decisioni Architetturali per Sviluppi Futuri](#10-decisioni-architetturali-per-sviluppi-futuri)
11. [Scaletta Sviluppo Incrementale](#11-scaletta-sviluppo-incrementale)
12. [Regole e Convenzioni per Claude Code](#12-regole-e-convenzioni-per-claude-code)

---

## 1. Contesto e Obiettivi

MRS si inserisce nel flusso ordine dopo che EasyJob ha registrato l'ordine e generato il Fabisogno. L'ufficio commerciale rimane su EasyJob e non è coinvolto in questa fase. MRS copre tre reparti: Ufficio Produzione, Magazzino e Logistica, con un modulo Reparto Produzione da introdurre gradualmente.

### 1.1 Problema da risolvere

Il flusso attuale è interamente manuale e cartaceo:

- EasyJob genera il Fabisogno — documento cartaceo con righe ordine, giacenza, disponibile, in produzione
- Ufficio Produzione recupera fisicamente i fogli ogni mattina, analizza e genera commesse
- Magazzino riceve i fogli, approntare gli ordini secondo logiche note solo agli operatori
- Logistica riceve il foglio compilato con colli e peso, sceglie corriere, prepara DDT, prenota ritiro
- Comunicazioni urgenze e priorità: verbali o con appunti volanti tra i reparti

### 1.2 Cosa cambia con MRS

- Il Fabisogno cartaceo viene sostituito da viste digitali per ogni reparto
- Le logiche di spedizione cliente vengono configurate una volta in MRS invece di essere nella testa degli operatori
- Le comunicazioni inter-reparto diventano eventi tracciati nel sistema
- EasyJob rimane responsabile di tutta la parte contabile e fiscale (DDT inclusi)
- Il reparto produzione viene integrato gradualmente per portare dati reali al sistema

### 1.3 Principi architetturali fondamentali

| Principio | Regola |
|---|---|
| **Source of truth** | EasyJob è source of truth. In caso di conflitto tra dato locale MRS e dato EasyJob, EasyJob vince sempre. |
| **MRS read-only su EasyJob** | MRS non scrive mai direttamente su EasyJob in MVP. Il flusso inverso rimane manuale o via export Excel. |
| **Copia locale** | MRS mantiene una copia locale delle entità che elabora. I moduli leggono sempre dalla copia locale per velocità e disponibilità. |
| **Trasparenza sync** | Ogni modulo mostra l'indicatore di ultimo aggiornamento da EasyJob. Se il sync fallisce gli operatori lo vedono subito. |
| **Sistema suggerisce, operatore decide** | Nessun cambio automatico senza controllo umano. Il sistema propone priorità, sequenze e azioni — l'operatore approva. |
| **Espandibilità senza refactoring** | Le decisioni architetturali di MVP (layer export, servizio mail, interfaccia corrieri, JSON policy) evitano refactoring strutturali in futuro. |

---

## 2. Stack Tecnico e Struttura Progetto

### 2.1 Stack consigliato

| Layer | Tecnologia | Motivazione |
|---|---|---|
| Backend API | Python — FastAPI | Sviluppo veloce, ottimo per sync SQL Server, tipizzazione con Pydantic |
| Database MRS | PostgreSQL | Relazionale, JSONB nativo per policy clienti, robusto, supporto esteso |
| ORM | SQLAlchemy 2.x + Alembic | ORM moderno con async support, Alembic per migration |
| Sync EasyJob | APScheduler + pyodbc / sqlalchemy-pytds | Job schedulati per sync da SQL Server EasyJob |
| Frontend | React 18 + TypeScript | SPA, viste per reparto, drag&drop F2, terminale kiosk |
| State management | Zustand o TanStack Query | TanStack Query per server state (cache, polling), Zustand per UI state |
| UI Components | Tailwind CSS + shadcn/ui | Design system coerente, componenti accessibili |
| Drag & Drop | dnd-kit | Libreria moderna per F2 schedulazione — accessibile e performante |
| Barcode scanner | react-zxing o USB HID nativo | Per terminale magazzino e terminale reparto produzione |
| Real-time updates | Polling HTTP (interval 30s) o WebSocket leggero | Evita infrastruttura complessa in MVP — polling sufficiente per frequenze operative |
| Containerizzazione | Docker + docker-compose | Deploy interno semplificato |
| Export Excel | openpyxl (Python) | Generazione file .xlsx per import in EasyJob |

### 2.2 Struttura directory progetto

```
mrs/
├── backend/
│   ├── app/
│   │   ├── main.py                  # Entry point FastAPI
│   │   ├── config.py                # Settings (env vars, DB URLs)
│   │   ├── database.py              # SQLAlchemy engine + session
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── articolo.py
│   │   │   ├── cliente.py
│   │   │   ├── ordine.py
│   │   │   ├── riga_ordine.py
│   │   │   ├── commessa.py
│   │   │   ├── evento.py
│   │   │   ├── policy_cliente.py
│   │   │   ├── macchina.py
│   │   │   ├── utensile.py
│   │   │   ├── ciclo.py
│   │   │   └── sync_log.py
│   │   ├── schemas/                 # Pydantic schemas (request/response)
│   │   ├── routers/                 # FastAPI routers per modulo
│   │   │   ├── produzione.py
│   │   │   ├── magazzino.py
│   │   │   ├── logistica.py
│   │   │   ├── eventi.py
│   │   │   └── sync.py
│   │   ├── services/                # Business logic
│   │   │   ├── scorte.py            # Algoritmo calcolo scorte
│   │   │   ├── commesse.py          # Logiche commessa
│   │   │   ├── priorita.py          # Calcolo priorità schedulazione
│   │   │   ├── disponibilita.py     # qty_disponibile_futura, qty_da_produrre
│   │   │   ├── eventi.py            # Gestione eventi inter-reparto
│   │   │   ├── magazzino.py         # Filtro ordini, approntamento
│   │   │   ├── logistica.py         # Policy clienti, spedizioni, urgenze
│   │   │   ├── reparto.py           # Terminale macchina, consegne
│   │   │   └── export_easyjob.py    # Layer export Excel EasyJob
│   │   └── sync/                    # Sync da EasyJob
│   │       ├── easyjob.py           # Connessione SQL Server
│   │       ├── scheduler.py         # APScheduler jobs
│   │       └── handlers.py          # Sync per tabella
│   ├── alembic/                     # Migration DB
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Produzione/          # F1a, F1b, F2
│   │   │   ├── Magazzino/           # F1–F5
│   │   │   ├── Logistica/           # F1–F3c
│   │   │   └── Reparto/             # Terminale macchina (kiosk)
│   │   ├── components/              # Componenti condivisi
│   │   ├── hooks/                   # Custom hooks (useSyncStatus, ecc.)
│   │   ├── store/                   # Zustand stores
│   │   └── api/                     # Client HTTP per backend
└── docker-compose.yml
```

---

## 3. Schema Database — PostgreSQL

Tutte le tabelle usano UUID come chiave primaria. I timestamp sono sempre UTC. Le chiavi di collegamento con EasyJob usano i campi codice/id nativi del gestionale.

### 3.1 articoli

Anagrafica articoli MRS — arricchisce i dati base di EasyJob con parametri operativi.

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `codice` | `VARCHAR(50)` | NO | Codice articolo EasyJob — chiave di collegamento (UNIQUE) |
| `codice_upper` | `VARCHAR(50)` | NO | Codice uppercase — usato per matching EasyJob (UNIQUE) |
| `descrizione` | `TEXT` | YES | Descrizione articolo da EasyJob |
| `categoria` | `VARCHAR(50)` | YES | Categoria articolo |
| `capienza` | `INTEGER` | YES | Capacità fisica magazzino per l'articolo |
| `scorta_mensile` | `INTEGER` | NO DEFAULT 0 | Scorta mensile calcolata automaticamente — ricalcolo mensile |
| `mesi_scorta` | `INTEGER` | NO DEFAULT 3 | Parametro configurabile — mesi di copertura target |
| `tipo_produzione` | `VARCHAR(20)` | NO DEFAULT 'PEZZO' | Enum: `PEZZO` \| `BARRA` \| `FASCI` \| `SPECIALE` \| `BARRA_GREZZA` |
| `lunghezza_barra` | `INTEGER` | YES | Lunghezza barra in mm — usata per tipo BARRA |
| `multipli_taglio` | `INTEGER` | YES | Multipli di produzione — usati per tipo FASCI |
| `prd_pari` | `BOOLEAN` | NO DEFAULT false | Flag produzione in quantità pari |
| `storico_sufficiente` | `BOOLEAN` | NO DEFAULT false | True se l'articolo ha almeno N mesi distinti con vendite nell'anno |
| `scorta_calcolata_at` | `TIMESTAMPTZ` | YES | Timestamp ultimo ricalcolo scorta mensile |
| `synced_at` | `TIMESTAMPTZ` | NO | Timestamp ultimo sync da EasyJob |

### 3.2 clienti

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `codice_easyjob` | `VARCHAR(50)` | NO | ID cliente in EasyJob (UNIQUE) |
| `ragione_sociale` | `TEXT` | NO | Ragione sociale |
| `email` | `VARCHAR(255)` | YES | Email principale — usata per comunicazioni future |
| `synced_at` | `TIMESTAMPTZ` | NO | Timestamp ultimo sync da EasyJob |

### 3.3 ordini

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `numero_ordine` | `VARCHAR(50)` | NO | Numero ordine EasyJob (UNIQUE) |
| `cliente_id` | `UUID FK clienti` | NO | Cliente di riferimento |
| `data_ordine` | `DATE` | NO | Data inserimento ordine |
| `data_consegna` | `DATE` | YES | Data consegna richiesta — NULL = nessuna scadenza |
| `stato` | `VARCHAR(30)` | NO DEFAULT 'aperto' | Enum: `aperto` \| `parzialmente_spedito` \| `spedito` \| `chiuso` |
| `note` | `TEXT` | YES | Note libere ordine |
| `synced_at` | `TIMESTAMPTZ` | NO | Timestamp ultimo sync da EasyJob |

### 3.4 righe_ordine

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `ordine_id` | `UUID FK ordini` | NO | Ordine di riferimento |
| `articolo_id` | `UUID FK articoli` | NO | Articolo ordinato |
| `riga_ej_id` | `VARCHAR(50)` | NO | ID riga in EasyJob — per tracking e import commessa |
| `qty_ordinata` | `INTEGER` | NO | Quantità ordinata dal cliente |
| `qty_disponibile` | `INTEGER` | NO DEFAULT 0 | Calcolato da MRS: giacenza - impegni precedenti |
| `qty_in_produzione` | `INTEGER` | NO DEFAULT 0 | Quantità già in produzione (LDP aperti su EasyJob) |
| `qty_consegnata` | `INTEGER` | NO DEFAULT 0 | Quantità consegnata/spedita |
| `qty_da_produrre` | `INTEGER` | COMPUTED | `qty_ordinata - qty_disponibile - qty_in_produzione` (se > 0) |
| `stato` | `VARCHAR(30)` | NO DEFAULT 'aperto' | Enum: `aperto` \| `in_produzione` \| `pronto` \| `spedito` \| `chiuso` |
| `synced_at` | `TIMESTAMPTZ` | NO | Timestamp ultimo sync da EasyJob |

### 3.5 commesse

Entità centrale del reparto produzione. Gestisce lanci combinati cliente+scorta, produzione parziale pianificata e interruzioni tracciate.

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `riga_ordine_id` | `UUID FK righe_ordine` | YES | Riga ordine cliente (NULL per commesse pure scorta) |
| `articolo_id` | `UUID FK articoli` | NO | Articolo da produrre |
| `macchina_id` | `UUID FK macchine` | YES | Macchina assegnata — NULL finché non schedulata |
| `ldp_easyjob` | `VARCHAR(50)` | YES | Numero LDP EasyJob — popolato dopo export Excel e import |
| `qty_cliente` | `INTEGER` | NO DEFAULT 0 | Quantità da produrre per l'ordine cliente |
| `qty_scorta` | `INTEGER` | NO DEFAULT 0 | Quantità da produrre per scorta magazzino (0 se non applicabile) |
| `qty_prodotta_cliente` | `INTEGER` | NO DEFAULT 0 | Quantità prodotta e consegnata quota cliente |
| `qty_prodotta_scorta` | `INTEGER` | NO DEFAULT 0 | Quantità prodotta e consegnata quota scorta |
| `qty_ciclo_corrente` | `INTEGER` | YES | Quantità pianificata per il ciclo corrente — NULL = tutto il residuo |
| `stato` | `VARCHAR(30)` | NO DEFAULT 'in_coda' | Enum: `in_coda` \| `in_produzione` \| `sospesa` \| `completata` |
| `posizione_coda` | `INTEGER` | YES | Ordine nella coda macchina — gestito manualmente da F2 |
| `priorita_suggerita` | `INTEGER` | YES | Priorità calcolata dal sistema (1=alta) — solo suggerimento |
| `sospesa_at` | `TIMESTAMPTZ` | YES | Timestamp interruzione — base raccolta tempi futura |
| `sospesa_nota` | `TEXT` | YES | Motivo opzionale dell'interruzione |
| `completata_at` | `TIMESTAMPTZ` | YES | Timestamp completamento |
| `created_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp creazione commessa |
| `created_by` | `VARCHAR(50)` | YES | Reparto/utente che ha creato la commessa |

> **Nota:** La commessa è completata quando `qty_prodotta_cliente + qty_prodotta_scorta = qty_cliente + qty_scorta` E il magazzino ha registrato in EasyJob. A quel punto `ldp_easyjob` si chiude e la riga sparisce dalle viste MRS.

### 3.6 policy_clienti

Struttura JSON flessibile — permette aggiunta di condizioni future senza migration schema.

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `cliente_id` | `UUID FK clienti` | NO | Cliente di riferimento (UNIQUE — una policy per cliente) |
| `tipo_policy` | `VARCHAR(30)` | NO | Enum: `GIORNO_FISSO` \| `DATA_TASSATIVA` \| `SOGLIA_VALORE` \| `DEFAULT` \| `SPECIFICO` |
| `giorno_fisso` | `INTEGER` | YES | Giorno della settimana: 1=Lunedì … 7=Domenica |
| `soglia_valore` | `NUMERIC(10,2)` | YES | Soglia valore ordine per spedizione (in euro) |
| `corriere_preferito` | `VARCHAR(100)` | YES | Nome corriere preferito (es: BRT, GLS, DHL) |
| `note_spedizione` | `TEXT` | YES | Indicazioni specifiche per il corriere o la spedizione |
| `policy_json` | `JSONB` | YES | Estensioni future — condizioni aggiuntive sommabili |
| `configurata_da` | `VARCHAR(50)` | YES | Utente logistica che ha configurato la policy |
| `updated_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp ultima modifica |

### 3.7 eventi

Tabella trasversale per tutte le comunicazioni inter-reparto.

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `tipo` | `VARCHAR(50)` | NO | Enum: `urgenza_formale` \| `priorita_interna` \| `ordine_pronto` \| `feedback_urgenza` \| `suggerimento_scheduler` |
| `mittente` | `VARCHAR(30)` | NO | Reparto: `produzione` \| `magazzino` \| `logistica` \| `sistema` |
| `destinatario` | `VARCHAR(30)` | NO | Reparto destinatario |
| `ref_ordine_id` | `UUID FK ordini` | YES | Ordine collegato |
| `ref_commessa_id` | `UUID FK commesse` | YES | Commessa collegata |
| `ref_articolo_id` | `UUID FK articoli` | YES | Articolo collegato |
| `stato` | `VARCHAR(20)` | NO DEFAULT 'aperto' | Enum: `aperto` \| `in_lavorazione` \| `risolto` \| `rifiutato` |
| `nota` | `TEXT` | YES | Testo libero opzionale |
| `feedback_stato` | `VARCHAR(30)` | YES | Per feedback urgenza: `accettata` \| `non_fattibile` |
| `feedback_data_prevista` | `DATE` | YES | Data prevista completamento (da produzione a logistica) |
| `feedback_nota` | `TEXT` | YES | Nota libera dal feedback |
| `corriere_override` | `VARCHAR(100)` | YES | Corriere override per questa urgenza specifica |
| `created_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp creazione evento |
| `updated_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp ultima modifica |
| `resolved_at` | `TIMESTAMPTZ` | YES | Timestamp risoluzione |

### 3.8 macchine

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `codice` | `VARCHAR(30)` | NO | Codice macchina (UNIQUE) |
| `nome` | `TEXT` | NO | Nome descrittivo macchina |
| `operazioni_eseguibili` | `TEXT[]` | NO DEFAULT '{}' | Array operazioni che questa macchina può eseguire |
| `stato` | `VARCHAR(30)` | NO DEFAULT 'disponibile' | Enum: `disponibile` \| `in_lavorazione` \| `in_setup` \| `in_manutenzione` |
| `setup_corrente` | `TEXT` | YES | Attrezzatura/setup attualmente montata — base per ottimizzazione |
| `attiva` | `BOOLEAN` | NO DEFAULT true | False = macchina disattivata (fuori uso, venduta, ecc.) |

### 3.9 sync_log

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria |
| `tabella` | `VARCHAR(50)` | NO | Tabella EasyJob sincronizzata (UNIQUE per nome tabella) |
| `last_sync_at` | `TIMESTAMPTZ` | YES | Timestamp ultimo sync completato con successo |
| `last_error` | `TEXT` | YES | Errore dell'ultimo tentativo fallito |
| `records_updated` | `INTEGER` | YES | Numero record aggiornati nell'ultimo sync |
| `sync_duration_ms` | `INTEGER` | YES | Durata sync in ms |

### 3.10 consegne_magazzino

Biglietto digitale di consegna dalla produzione al magazzino — sostituisce il bigliettino cartaceo. Alimenta F5 magazzino.

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `commessa_id` | `UUID FK commesse` | NO | Commessa di riferimento |
| `articolo_id` | `UUID FK articoli` | NO | Articolo consegnato |
| `qty_consegnata` | `INTEGER` | NO | Quantità fisica consegnata al magazzino |
| `quota` | `VARCHAR(10)` | NO | Enum: `cliente` \| `scorta` \| `mista` |
| `qty_cliente` | `INTEGER` | NO DEFAULT 0 | Quota cliente su questa consegna |
| `qty_scorta` | `INTEGER` | NO DEFAULT 0 | Quota scorta su questa consegna |
| `stato` | `VARCHAR(20)` | NO DEFAULT 'in_attesa' | Enum: `in_attesa` \| `registrata_ej` |
| `registrata_ej_at` | `TIMESTAMPTZ` | YES | Timestamp registrazione in EasyJob (riga sparisce da F5) |
| `created_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp consegna fisica |

### 3.11 spedizioni

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `id` | `UUID PK` | NO | Chiave primaria MRS |
| `ordine_id` | `UUID FK ordini` | NO | Ordine spedito |
| `tipo` | `VARCHAR(20)` | NO | Enum: `totale` \| `parziale` \| `urgenza` |
| `stato` | `VARCHAR(30)` | NO DEFAULT 'in_preparazione' | Enum: `in_preparazione` \| `pronta` \| `in_spedizione` \| `spedita` \| `annullata` |
| `corriere` | `VARCHAR(100)` | YES | Corriere selezionato |
| `data_pianificata` | `DATE` | YES | Data spedizione pianificata |
| `data_spedizione` | `DATE` | YES | Data spedizione effettiva |
| `colli` | `INTEGER` | YES | Numero colli |
| `peso_kg` | `NUMERIC(8,2)` | YES | Peso totale in kg |
| `evento_id` | `UUID FK eventi` | YES | Collegamento urgenza se generata da evento |
| `note` | `TEXT` | YES | Note logista |
| `created_at` | `TIMESTAMPTZ` | NO DEFAULT now() | Timestamp creazione |

---

## 4. Integrazione EasyJob — Sync

### 4.1 Configurazione accesso

Connessione diretta al database SQL Server di EasyJob. Le credenziali sono configurate tramite variabili d'ambiente.

| Variabile env | Descrizione |
|---|---|
| `EASYJOB_SERVER` | Hostname o IP del server SQL Server EasyJob |
| `EASYJOB_DATABASE` | Nome del database EasyJob |
| `EASYJOB_USER` | Username SQL Server |
| `EASYJOB_PASSWORD` | Password SQL Server |
| `EASYJOB_PORT` | Porta SQL Server (default: 1433) |

```python
# backend/app/sync/easyjob.py
# Usare pyodbc o sqlalchemy con driver MSSQL
# CONNECTION_STRING = f"mssql+pyodbc://{user}:{pwd}@{server}/{db}?driver=ODBC+Driver+18+for+SQL+Server"
```

### 4.2 Frequenze di sync

| Tabella EasyJob | Tabella MRS | Frequenza default | Motivazione |
|---|---|---|---|
| Ordini / righe ordine | `ordini` + `righe_ordine` | 5 min | Cambiano spesso, impattano F1a e viste magazzino |
| Movimenti magazzino / giacenze | `righe_ordine.qty_disponibile` | 5 min | Base per calcolo disponibilità e F5 |
| LDP in produzione | `righe_ordine.qty_in_produzione` | 5 min | Serve per sapere cosa è già in produzione |
| Anagrafiche articoli | `articoli` (campi base) | 60 min | Cambiano raramente |
| Anagrafiche clienti | `clienti` | 60 min | Cambiano raramente |

### 4.3 Fallback — sync mirato automatico

| Trigger | Azione automatica |
|---|---|
| Ordine con cliente non in anagrafica locale | Forza sync anagrafiche clienti |
| Ordine con articolo non in anagrafica locale | Forza sync anagrafiche articoli |
| LDP riferisce articolo senza record MRS | Forza sync + avviso configurazione mancante |
| Urgenza su ordine non trovato localmente | Forza sync tabella ordini |
| Giacenza negativa inattesa | Forza sync movimenti magazzino |

### 4.4 API endpoint — stato sync

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/sync/status` | Stato sync per tutte le tabelle — `last_sync_at`, `last_error`, `records_updated` |
| `POST` | `/api/sync/force/{tabella}` | Forza sync immediato di una tabella specifica |
| `POST` | `/api/sync/force-all` | Forza sync completo di tutte le tabelle |

### 4.5 Indicatore sync in frontend

Ogni modulo frontend mostra un indicatore "Ultimo aggiornamento: X min fa" con colore basato sull'età del dato:

- **Verde:** < 10 minuti fa
- **Giallo:** 10–30 minuti fa
- **Rosso:** > 30 minuti fa o errore sync

> In caso di rosso viene mostrato il pulsante "Aggiorna ora" che chiama `/api/sync/force/{tabella}`.

### 4.6 Layer export EasyJob — decisione architettuale

La logica di generazione commessa è separata dall'export. Questo permette di sostituire l'export Excel con chiamata API diretta senza refactoring.

```python
# services/export_easyjob.py

def genera_riga_commessa(commessa: Commessa) -> dict:
    """Costruisce la struttura dati della commessa — indipendente dal formato export"""
    ...

def esporta_su_easyjob(righe: list[dict]) -> bytes:
    """Oggi: genera file Excel. Domani: chiama API EasyJob. Interfaccia invariata."""
    ...
```

---

## 5. Modulo Ufficio Produzione

Primo reparto nel flusso. Riceve gli ordini da EasyJob, identifica cosa deve essere prodotto e gestisce la schedulazione del reparto produttivo.

### 5.1 F1a — Vista ordini cliente (commesse da lanciare)

#### Logica di filtro

Mostrare **SOLO** le righe ordine che soddisfano **TUTTI** i seguenti criteri:

- `qty_ordinata - qty_disponibile - qty_in_produzione > 0` (c'è ancora qualcosa da produrre)
- Non esiste già una commessa MRS in stato ≠ `completata` per quella riga ordine
- Lo stato della riga ordine non è `spedito` o `chiuso`

Lista vuota = tutto processato. Zero ambiguità.

#### Campi da mostrare per ogni riga

| Campo | Fonte | Note UI |
|---|---|---|
| Codice articolo | `articoli.codice` | |
| Descrizione | `articoli.descrizione` | |
| Cliente | `clienti.ragione_sociale` | |
| Numero ordine | `ordini.numero_ordine` | |
| Data consegna | `ordini.data_consegna` | Colore rosso se nel passato (flag data scaduta) |
| Qty ordinata | `righe_ordine.qty_ordinata` | |
| Disponibile | `righe_ordine.qty_disponibile` | |
| In produzione | `righe_ordine.qty_in_produzione` | |
| Da produrre | `qty_ordinata - qty_disponibile - qty_in_produzione` | Calcolato live |
| Flag urgenza | `FROM eventi WHERE tipo=urgenza_formale AND ref_ordine_id=ordine AND stato=aperto` | Badge visibile |
| Flag data scaduta | `data_consegna < today()` | Informativo, non bloccante |

#### Export Excel per EasyJob

- L'operatore seleziona le righe da lanciare (checkbox)
- Può modificare `qty_ciclo_corrente` per produzione parziale pianificata
- Può aggiungere `qty_scorta` per lancio combinato
- L'export chiama `POST /api/produzione/genera-commesse` con le righe selezionate
- Il backend: crea record commessa in DB + genera file Excel + restituisce file per download

> **Nota:** La commessa viene creata in MRS al momento dell'export, con stato `in_coda`. Il campo `ldp_easyjob` rimane NULL finché l'operatore non importa il file in EasyJob e riporta il numero LDP. Un sync successivo da EasyJob aggiornerà `qty_in_produzione` sulla riga ordine.

#### API F1a

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/produzione/f1a` | Lista righe ordine da processare (con filtri: `cliente`, `data_da`, `data_a`, `urgenza_only`) |
| `POST` | `/api/produzione/genera-commesse` | Body: lista righe selezionate con `qty_ciclo`, `qty_scorta`. Crea commesse + export Excel |

### 5.2 F1b — Vista scorte magazzino da ricostituire

#### Logica filtro articoli

Mostrare **SOLO** gli articoli che soddisfano **TUTTI** i seguenti criteri:

- `tipo_produzione` ∈ `{PEZZO, BARRA, FASCI}` — esclusi `SPECIALE` e `BARRA_GREZZA`
- `storico_sufficiente = true`
- `qty_disponibile_futura < target_scorta`

#### Formula target scorta

```python
qty_disponibile_futura = giacenza_attuale - impegni_ordini_aperti_futuri
target_scorta = scorta_mensile * mesi_scorta
qty_da_produrre_scorta = target_scorta - qty_disponibile_futura
# Mostrare solo se qty_da_produrre_scorta > 0
```

> `impegni_ordini_aperti_futuri` = somma di `(qty_ordinata - qty_consegnata)` per le righe ordine aperte future di quell'articolo.

#### Algoritmo calcolo `scorta_mensile` — bug corretti da implementare

| Bug v0 | Correzione da implementare in v1 |
|---|---|
| **FILTRO MOVIMENTI MINIMI:** usava movimenti totali | Contare mesi distinti con vendite nell'anno. Un articolo entra nel calcolo SOLO se ha vendite in almeno N mesi distinti (N configurabile, default 4). Altrimenti: `scorta_mensile = 0` e `storico_sufficiente = false`. |
| **ORDINE Z-SCORE:** filtrava per periodo DOPO Z-score | Filtrare per periodo PRIMA di applicare Z-score. Sequenza corretta: (1) prendi movimenti degli ultimi 12m, (2) raggruppa per mese, (3) calcola media e deviazione standard mensile, (4) rimuovi outlier con z > 3, (5) calcola percentile 80 per ognuno dei tre orizzonti. |
| **IMPEGNI FUTURI non considerati** | Target = `(scorta_mensile × mesi_scorta) - qty_disponibile_futura` dove `qty_disponibile_futura = giacenza - impegni_ordini_aperti_futuri`. |

#### Algoritmo completo `scorta_mensile`

```python
# services/scorte.py

def calcola_scorta_mensile(articolo_id: UUID, movimenti: list[dict]) -> int:
    """
    Parametri: movimenti = lista di {mese: date, qty: int} ultimi 12 mesi
    Ritorna: scorta_mensile (int) — 0 se storico insufficiente
    """
    MESI_MINIMI = 4  # configurabile via env SOGLIA_MESI_STORICO
    SOGLIA_Z = 3.0

    # 1. Raggruppa per mese e conta mesi distinti con vendite
    per_mese = group_by_month(movimenti)  # {mese: qty_totale}
    mesi_con_vendite = [m for m, q in per_mese.items() if q > 0]
    if len(mesi_con_vendite) < MESI_MINIMI:
        return 0

    # 2. Tre orizzonti: 12m, 6m, 3m
    orizzonti = [12, 6, 3]
    risultati = []
    for n_mesi in orizzonti:
        periodo = per_mese_last_n(per_mese, n_mesi)
        # 3. Z-score per rimuovere outlier nel periodo
        valori = list(periodo.values())
        media = mean(valori)
        std = stdev(valori)
        filtrati = [v for v in valori if std == 0 or abs((v - media) / std) < SOGLIA_Z]
        # 4. Percentile 80 dei valori filtrati
        risultati.append(percentile_80(filtrati))

    # 5. Media dei tre risultati
    return round(mean(risultati))
```

#### Ricalcolo mensile automatico

Il ricalcolo di `scorta_mensile` viene eseguito automaticamente il primo giorno del mese tramite APScheduler in `backend/app/sync/scheduler.py`. Il campo `scorta_calcolata_at` viene aggiornato ad ogni ricalcolo. Se un articolo perde lo storico sufficiente, `storico_sufficiente` viene impostato a `false` e `scorta_mensile` a `0`.

#### API F1b

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/produzione/f1b` | Lista articoli sotto scorta target (con filtri: `categoria`, `tipo_produzione`) |
| `POST` | `/api/produzione/ricalcola-scorte` | Forza ricalcolo scorte per tutti gli articoli (o per un articolo specifico se `articolo_id` in body) |

### 5.3 F2 — Schedulazione e coda di lavorazione

#### Struttura della coda

F2 mostra la coda di lavorazione per macchina. Le commesse sono ordinate per `posizione_coda` (INTEGER gestito manualmente con drag&drop). L'operatore trascina le commesse per riordinare la coda.

#### Priorità suggerita automaticamente

Il sistema calcola `priorita_suggerita` per ogni commessa incrociando:

- Data consegna dell'ordine (più vicina = priorità più alta)
- Policy spedizione del cliente (giorno fisso imminente = boost priorità)
- Urgenze formali attive collegate all'ordine (boost massimo)
- Segnalazioni priorità interna dal magazzino

> `priorita_suggerita` è solo un suggerimento. Il campo `posizione_coda` è quello effettivo. Il sistema non modifica mai la coda senza azione esplicita dell'operatore.

#### Stati commessa

| Stato | Transizioni ammesse | Trigger |
|---|---|---|
| `in_coda` | → `in_produzione` | Operatore seleziona "Avvia" su terminale o in F2 |
| `in_produzione` | → `sospesa`, → `completata` | Operatore sospende o completa |
| `sospesa` | → `in_produzione` | Operatore riprende |
| `completata` | — | Terminale: pezzi inseriti + magazzino registra in EasyJob |

#### Produzione parziale pianificata

L'operatore può impostare `qty_ciclo_corrente` per indicare quanti pezzi produrre in questo ciclo (`NULL` = tutto il residuo). Questo valore appare nella lista di produzione stampata per la macchina.

#### Visibilità condivisa

F2 è visibile (sola lettura) anche da magazzino e logistica. Permette a magazzino e logistica di sapere in qualsiasi momento cosa è in produzione senza dover chiamare.

#### API F2

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/produzione/f2` | Lista commesse per macchina, ordinate per `posizione_coda` |
| `PATCH` | `/api/produzione/commesse/{id}/posizione` | Body: `{posizione_coda: int}`. Aggiorna posizione nella coda |
| `PATCH` | `/api/produzione/commesse/{id}/stato` | Body: `{stato, nota?}`. Transizione di stato con validazione |
| `PATCH` | `/api/produzione/commesse/{id}/qty-ciclo` | Body: `{qty_ciclo_corrente: int\|null}`. Imposta qty del ciclo corrente |
| `GET` | `/api/produzione/f2/lista-produzione/{macchina_id}` | Genera PDF lista produzione per macchina |

### 5.4 Anagrafica articoli MRS

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/articoli` | Lista articoli con filtri (`categoria`, `tipo_produzione`, `storico_sufficiente`) |
| `GET` | `/api/articoli/{id}` | Dettaglio articolo con storico scorta e commesse recenti |
| `PATCH` | `/api/articoli/{id}` | Aggiorna campi MRS: `mesi_scorta`, `tipo_produzione`, `multipli_taglio`, ecc. |

---

## 6. Modulo Reparto Produzione

Modulo introdotto gradualmente con 4 fasi operative. Non blocca gli altri reparti.

### 6.1 Piano di introduzione graduale

| Fase | Periodo | Cosa si introduce | Input richiesto all'operatore |
|---|---|---|---|
| Fase 0 — Preparazione | Apr–Mag 2026 | Configurazione anagrafica macchine, utensili, cicli. Nessun impatto reparto. | Zero (in ufficio) |
| Fase 1 — Solo output | Giu–Lug 2026 | Terminale in sola lettura: coda schedulata per macchina. | Zero |
| Fase 2 — Un gesto | Ago–Set 2026 | Scansione barcode a fine lavoro per alimentare F5 magazzino. | Scansione barcode: 2 secondi |
| Fase 3 — Setup guidato | Ott 2026 | Schermata setup all'avvio commessa: il sistema dice cosa serve. | Selezione da lista in apertura commessa |
| Fase 4 — Tempi e scarti | Nov–Dic 2026 | Raccolta tempi implicita + pezzi prodotti a fine fase. | Quantità prodotta a chiusura fase |

> **Principio guida:** il sistema deve dare sempre più di quanto chiede. Ogni step deve portare un vantaggio percepibile per l'operatore prima di richiedere qualcosa in più.

### 6.2 Terminale macchina — UI Kiosk

Schermo dedicato su ogni macchina. Ottimizzato per touch. Font grandi, pulsanti grandi, zero navigazione complessa.

| Momento | Azione operatore | Comportamento sistema |
|---|---|---|
| Inizio turno | Guarda la coda schedulata | Mostra lista lavori ordinata per priorità — nessun input richiesto |
| Avvio commessa | Seleziona la commessa da iniziare | Confronta setup richiesto con setup attuale macchina |
| Setup compatibile | Nessuna azione | Conferma che non è necessario alcun cambio — prosegue |
| Setup incompatibile | Seleziona attrezzatura da montare | Mostra lista attrezzature consentite per quella fase |
| Fine fase | Inserisce pezzi prodotti reali e scarti (con motivo opzionale) | Aggiorna avanzamento commessa, propaga a magazzino e logistica |
| Fine commessa | Conferma completamento | Prompt smontaggio utensili dedicati — macchina torna a stato base |
| Guasto / problema | Segnala interruzione | Timer sospeso, commessa in stato sospeso, schedulatore ricalcola |

### 6.3 Raccolta tempi — implicita

Il timer parte e si ferma con le azioni già previste dal flusso. Nessun input aggiuntivo dedicato.

- Avvio commessa → start timer
- Sospensione commessa → stop timer, salva `sospesa_at` e `sospesa_nota`
- Ripresa commessa → start nuovo timer per questo ciclo
- Completamento commessa → stop timer, salva `completata_at`

### 6.4 Anagrafica utensili

| Campo | Tipo | Descrizione |
|---|---|---|
| `id` | `UUID PK` | Chiave primaria |
| `codice` | `VARCHAR(30)` | Codice utensile (UNIQUE) |
| `tipo` | `TEXT` | Tipo/famiglia utensile |
| `standard_o_dedicato` | `VARCHAR(20)` | Enum: `standard` \| `dedicato` |
| `giacenza` | `INTEGER` | Quantità disponibile in magazzino utensili |
| `vita_media_pezzi` | `INTEGER` | Vita media calcolata su dati reali — pezzi per utensile |
| `soglia_riordino` | `INTEGER` | Quantità minima — sotto questa soglia alert acquisto |
| `costo_unitario` | `NUMERIC(8,2)` | Costo per utensile — per calcolo costo per articolo |

### 6.5 Cicli di lavorazione

Ogni articolo standard ha un ciclo associato. Il ciclo è un grafo di dipendenze: alcune fasi hanno dipendenza rigida, altre sono intercambiabili.

| Tabella | Campi principali | Note |
|---|---|---|
| `cicli` | `id, articolo_id, nome, tipo (standard\|adhoc), attivo` | Un articolo può avere più cicli ma uno solo attivo |
| `fasi_ciclo` | `id, ciclo_id, nome_fase, operazione, macchine_idonee[], utensili_necessari[], dipende_da[]` | `dipende_da` = array di id fasi da completare prima |

### 6.6 API Reparto Produzione

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/reparto/terminale/{macchina_id}` | Coda commesse per questa macchina — ottimizzata per kiosk |
| `POST` | `/api/reparto/commesse/{id}/avvia` | Avvia commessa — cambia stato, start timer |
| `POST` | `/api/reparto/commesse/{id}/sospendi` | Body: `{nota?}`. Sospende commessa, salva `sospesa_at` |
| `POST` | `/api/reparto/commesse/{id}/completa-fase` | Body: `{qty_prodotte, qty_scarti, motivo_scarto?}`. Chiude una fase, propaga avanzamento |
| `POST` | `/api/reparto/commesse/{id}/consegna-magazzino` | Body: `{qty_consegnata}`. Crea `consegna_magazzino`, alimenta F5 |
| `GET` | `/api/reparto/macchine` | Lista macchine con stato operativo |
| `PATCH` | `/api/reparto/macchine/{id}/stato` | Body: `{stato, setup_corrente?}`. Aggiorna stato macchina |

---

## 7. Modulo Magazzino

Il magazzino riceve gli ordini da processare e gestisce l'approntamento fisico. Le logiche di spedizione per cliente non sono più nella testa degli operatori ma configurate dalla logistica nel sistema.

### 7.1 F1 — Vista ordini da approntare

#### Logica filtro e ordinamento per policy

| Tipo policy | Regola di ordinamento | Evidenza UI |
|---|---|---|
| `GIORNO_FISSO` | In cima quando `giorno_fisso = day_of_week(today)`. Ordinati per distanza dal giorno fisso. | Badge con giorno. Colore arancione se è il giorno target. |
| `DATA_TASSATIVA` | Ordinati per `data_consegna` ASC. | Badge data con colore rosso se `data_consegna ≤ today + 1`. |
| `SOGLIA_VALORE` | Mostrati solo se valore ordine ≥ `soglia_valore`. Ordinati per valore DESC. | Badge con valore corrente vs soglia. |
| `DEFAULT` | Ordinati per `data_ordine` ASC. | Badge "Default" — avviso policy non configurata. |

> Clienti senza policy configurata: evidenziati con avviso arancione "Policy non configurata — applica default". Si applica comunque la policy DEFAULT. Il magazzino non è bloccato.

#### Campi da mostrare per ogni ordine

| Campo | Fonte | Note UI |
|---|---|---|
| Cliente | `clienti.ragione_sociale` | Prominente |
| Numero ordine | `ordini.numero_ordine` | |
| Data consegna | `ordini.data_consegna` | Rosso se scaduta o imminente (≤ 1 giorno) |
| Righe ordine | `righe_ordine` (aggregate) | Espandibile — mostra articoli, qtà, stato per riga |
| Disponibilità per riga | `qty_disponibile` per riga | Semaforo verde/giallo/rosso per riga |
| Flag urgenza | FROM eventi urgenze attive | Badge prominente se urgenza attiva |
| Policy applicata | `policy_clienti.tipo_policy` | Icona/badge piccolo |

### 7.2 F2 — Vista tutti gli ordini attivi

Vista completa di tutti gli ordini attivi filtrabili per mese. Permette visione d'insieme e anticipazione del carico di lavoro.

- Filtro per mese (default: mese corrente)
- Filtro per stato: `in_attesa` \| `parzialmente_pronto` \| `pronto`
- Filtro per cliente
- Ordinamento: per `data_consegna`, per cliente, per `data_ordine`

### 7.3 F3 — Conferma approntamento

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| Tipo approntamento | SÌ | Enum: `totale` \| `parziale` |
| Nota su mancanti (se parziale) | NO | Testo libero su cosa manca e perché |
| Numero colli | SÌ | Inserito manualmente — dato fisico rilevato |
| Peso kg | SÌ | Inserito manualmente — dato fisico rilevato |
| Segnalazione priorità interna | NO | Checkbox + nota per segnalare articolo bloccante a produzione — crea evento `priorita_interna` |

Se approntamento parziale: la parte mancante rimane in coda F1 con nota automatica.

### 7.4 F4 — Handoff a logistica

| Azione | Chi | Comportamento |
|---|---|---|
| Marca pronto | Magazzino in F3/F4 | Crea evento `ordine_pronto` → logistica. Ordine appare in F3a logistica. |
| Logistica valida | Logistica in F3a | Ordine entra nel calendario spedizioni. |
| Logistica rimanda con nota | Logistica in F3a | Ordine rientra in F1 magazzino con nota. Stato torna a "in_approntamento". |
| Logistica blocca | Logistica in F3a | Ordine bloccato in attesa completamento. Badge "Bloccato" in F2 magazzino. |

### 7.5 F5 — Articoli da processare (biglietto digitale)

Vista articoli in attesa di registrazione EasyJob — produzione completata fisicamente ma LDP non ancora chiuso.

| Campo | Fonte | Descrizione |
|---|---|---|
| Articolo | `articoli.codice` + `descrizione` | Quello che è arrivato fisicamente |
| Qty consegnata | `consegne_magazzino.qty_consegnata` | Quanti pezzi fisici sono arrivati |
| Quota | `consegne_magazzino.quota` | `cliente` \| `scorta` \| `mista` |
| Qty cliente / scorta | `qty_cliente` + `qty_scorta` | Dettaglio quota |
| Riferimento commessa | `commesse.id` abbreviato | Tracciabilità |
| Arrivato alle | `consegne_magazzino.created_at` | Timestamp consegna fisica |

Quando il magazzino registra l'LDP in EasyJob, clicca "Registrato in EasyJob" su ogni riga F5. Questo aggiorna `registrata_ej_at` e la riga sparisce da F5.

> F5 è il sostituto digitale del bigliettino cartaceo che la produzione attaccava al pallet. Elimina la comunicazione verbale "è arrivato il lotto di X".

### 7.6 API Magazzino

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/magazzino/f1` | Vista ordini da approntare, filtrati e ordinati per policy cliente |
| `GET` | `/api/magazzino/f2` | Tutti gli ordini attivi con filtri `mese`/`stato`/`cliente` |
| `POST` | `/api/magazzino/ordini/{id}/approntamento` | Body: `{tipo, colli, peso, nota?, segnala_priorita?, nota_priorita?}`. Conferma approntamento |
| `POST` | `/api/magazzino/ordini/{id}/pronto-spedire` | Marca ordine pronto, crea evento `ordine_pronto` per logistica |
| `GET` | `/api/magazzino/f5` | Lista articoli in attesa registrazione EasyJob |
| `POST` | `/api/magazzino/consegne/{id}/registrata-ej` | Marca riga F5 come registrata in EasyJob — riga sparisce da F5 |

---

## 8. Modulo Logistica

Reparto con il ruolo più trasversale: configura le regole operative per gli altri reparti, gestisce le urgenze formali e supervisiona il flusso di spedizione finale.

### 8.1 F1 — Configurazione policy clienti

#### Struttura policy

| `tipo_policy` | Campi attivi | Comportamento magazzino |
|---|---|---|
| `GIORNO_FISSO` | `giorno_fisso` (1–7) | Spedire tutto il disponibile nel giorno indicato ogni settimana |
| `DATA_TASSATIVA` | — | Spedire alla `data_consegna` indicata sull'ordine |
| `SOGLIA_VALORE` | `soglia_valore` (€) | Spedire quando il valore dell'ordine ≥ soglia |
| `SPECIFICO` | `corriere_preferito`, `note_spedizione` | Indicazioni specifiche — gestione manuale |
| `DEFAULT` | — | Policy di default per clienti non ancora configurati. Ordina per `data_ordine` ASC. |

> In MVP le policy sono esclusive (un solo tipo per cliente). In futuro: policy sommabili via `policy_json`.

#### Home logistica

- Lista clienti senza policy configurata + link rapido alla configurazione
- Contatore urgenze attive
- Spedizioni pianificate per oggi

#### API F1 Logistica

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/logistica/policy-clienti` | Lista policy clienti (filtro: `non_configurati=true`) |
| `PUT` | `/api/logistica/policy-clienti/{cliente_id}` | Crea o aggiorna policy cliente (upsert) |
| `DELETE` | `/api/logistica/policy-clienti/{cliente_id}` | Rimuove policy — cliente torna a DEFAULT |

### 8.2 F2 — Gestione urgenze formali

#### Creazione urgenza

| Campo | Obbligatorio | Descrizione |
|---|---|---|
| `cliente_id` | SÌ | Cliente per cui si crea l'urgenza |
| `ordini_righe` | SÌ | Selezione ordini interi o righe specifiche |
| `corriere_override` | NO | Corriere specifico per questa urgenza — sovrascrive policy F1 |
| `nota` | NO | Motivazione o istruzioni specifiche |

#### Flusso urgenza

| Step | Chi | Azione | Stato urgenza |
|---|---|---|---|
| 1 | Logistica | Crea urgenza | `aperto` |
| 2 | Sistema | Notifica automatica a produzione (se articoli in lavorazione) e magazzino | `aperto` |
| 3 | Produzione | Risponde: `accettata` \| `non_fattibile` + `data_prevista` + nota | `in_lavorazione` |
| 4a | Logistica (se accettata) | Attende completamento produzione | `in_lavorazione` |
| 4b | Logistica (se non fattibile) | Decide: attende o spedizione parziale subito + remainder | `in_lavorazione` |
| 5 | Logistica | Spedizione parziale: crea due spedizioni collegate | `parzialmente_risolto` |
| 6 | Magazzino/Logistica | Completamento totale | `risolto` |

> Urgenza parzialmente risolta: rimane aperta per il residuo fino a completamento totale.

#### API F2 Logistica

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/logistica/urgenze` | Lista urgenze attive con stato e feedback produzione |
| `POST` | `/api/logistica/urgenze` | Body: `{cliente_id, ordini_righe[], corriere_override?, nota?}`. Crea urgenza |
| `POST` | `/api/logistica/urgenze/{id}/spedizione-parziale` | Body: `{righe_immediate[], righe_differite[]}`. Gestisce split spedizione |
| `POST` | `/api/logistica/urgenze/{id}/risolvi` | Marca urgenza come risolta |

### 8.3 F3a — Ordini pronti da spedire

| Azione | Descrizione |
|---|---|
| Seleziona righe da spedire | Checkbox su ogni riga — può selezionare subset di un ordine |
| Assegna corriere | Regola preimpostata da F1 + override manuale |
| Pianifica spedizione | Sceglie data spedizione → aggiunge al calendario F3b |
| Rimanda con nota | Ordine torna a F1 magazzino con nota logistica |
| Blocca in attesa | Ordine bloccato fino a sblocco esplicito |
| Annulla spedizione | Resetta stato — riporta ordine in F3a (corriere non passato, merce danneggiata, ecc.) |

#### API F3a

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/logistica/f3a` | Lista ordini pronti da spedire |
| `POST` | `/api/logistica/spedizioni` | Body: `{ordine_id, righe[], corriere, data_pianificata}`. Crea spedizione pianificata |
| `POST` | `/api/logistica/spedizioni/{id}/annulla` | Annulla spedizione — riporta ordine in F3a |

### 8.4 F3b — Calendario spedizioni

Vista completa: urgenze attive + spedizioni pianificate + spedizioni confermate del giorno.

- Vista settimanale o mensile — switcher UI
- Colori per corriere — ottimizza visione raggruppamento ritiri
- Urgenze in evidenza (colore diverso)
- Spostamento spedizioni pianificate su altri giorni (drag&drop)

### 8.5 F3c — Lista operativa in spedizione

Lista di tutto ciò che deve uscire oggi. Tutti i dati già pronti per creare DDT in EasyJob e prenotare ritiro sul portale corriere.

| Campo | Descrizione |
|---|---|
| Cliente | Ragione sociale + codice |
| Ordine / righe | Numero ordine + articoli con qty |
| Colli e peso | Dato inserito dal magazzino in F3 |
| Corriere | Corriere selezionato + eventuale override |
| Note spedizione | Da policy cliente F1 |
| Riferimento DDT | Campo compilabile manualmente dopo creazione DDT in EasyJob |

> DDT generato in EasyJob — fuori scope MRS. La lista operativa MRS fornisce tutti i dati già pronti.

#### API F3b/F3c

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/logistica/f3b` | Calendario spedizioni — query param: `da`, `a` (range date) |
| `GET` | `/api/logistica/f3c` | Lista operativa oggi — spedizioni in stato `in_spedizione` per oggi |
| `PATCH` | `/api/logistica/spedizioni/{id}` | Aggiorna spedizione (`data`, `corriere`, `colli`, `peso`, `ddt_ref`) |

---

## 9. Modulo Eventi Trasversale

Tutte le comunicazioni inter-reparto vengono gestite da un unico modulo eventi. Ogni reparto ha un'area notifiche nel proprio layout.

### 9.1 Mappa eventi MVP

| Mittente | Destinatario | Tipo evento | Trigger |
|---|---|---|---|
| Logistica | Magazzino + Produzione | `urgenza_formale` | Logistica crea urgenza in F2 |
| Magazzino | Produzione | `priorita_interna` | Magazzino segnala articolo bloccante in F3 |
| Magazzino | Logistica | `ordine_pronto` | Magazzino marca ordine pronto in F4 |
| Produzione | Logistica | `feedback_urgenza` | Produzione risponde a urgenza formale da F2 |
| Sistema | Produzione | `suggerimento_scheduler` | Calcolo automatico priorità da dati ordini/urgenze |

### 9.2 Calendario operativo condiviso

| Reparto | Cosa vede | Filtri disponibili |
|---|---|---|
| Produzione | Urgenze aperte + spedizioni pianificate non ancora confermate. Alimenta priorità suggerita F2. | Per data, per tipo |
| Magazzino | Urgenze + spedizioni pianificate + spedizioni confermate del giorno. | Per data, per corriere |
| Logistica | Vista completa — urgenze attive, calendario spedizioni pianificate e confermate. | Per data, per corriere, per cliente |

### 9.3 API Modulo Eventi

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/eventi` | Lista eventi — filtri: `destinatario`, `tipo`, `stato`, `created_after` |
| `GET` | `/api/eventi/non-letti/{reparto}` | Contatore eventi non letti per un reparto — usato per badge notifiche |
| `POST` | `/api/eventi/{id}/feedback` | Body: `{feedback_stato, feedback_data_prevista?, feedback_nota?}` |
| `POST` | `/api/eventi/{id}/segna-letto` | Marca evento come visto dal destinatario |
| `GET` | `/api/calendario` | Vista calendario — query param: `da`, `a`, `reparto` |

### 9.4 Notifiche in-app

Implementazione MVP: polling dal frontend ogni 30 secondi su `/api/eventi/non-letti/{reparto}`. Se `count > 0` mostra badge rosso sull'icona notifiche.

> In futuro: WebSocket per notifiche real-time. L'architettura polling → WebSocket non richiede cambiamenti al backend REST.

---

## 10. Decisioni Architetturali per Sviluppi Futuri

Costo implementativo minimo, risparmio futuro alto. Da implementare in MVP come fondamenta, non come feature complete.

| Decisione | Implementazione MVP | Cosa sblocca in futuro |
|---|---|---|
| **Layer export EasyJob** | Separare `genera_commessa()` da `esporta_su_easyjob()`. Oggi `esporta_su_easyjob()` produce il file Excel. | Sostituire solo `esporta_su_easyjob()` con chiamata API diretta. Zero refactor sulla logica di generazione. |
| **Servizio mail integrato ma non automatico** | Integrare subito un servizio mail (es. Resend). La funzione `componi_mail_cliente()` esiste ma viene chiamata manualmente dal logista. | Automazione = cambiare solo il trigger. La funzione non cambia. |
| **Interfaccia `prenota_ritiro()` astratta** | `prenota_ritiro()` mostra una schermata con tutti i dati pronti per il portale manuale. | Domani `prenota_ritiro()` chiama l'API di BRT o GLS. Zero impatto sulla logica spedizione. |
| **Policy clienti come JSONB flessibile** | `policy_json` come colonna JSONB invece di colonne fisse aggiuntive. | Aggiungere condizioni sommabili senza migration schema. |
| **Timestamp su commessa** | `sospesa_at` e `sospesa_nota` già nel modello dati commessa. | Raccolta tempi reali futura: i dati ci sono già, zero refactor. |
| **Timer impliciti sul terminale** | Il timer parte/ferma con azioni già previste dal flusso. | Analisi efficienza e scheduler automatico: i dati storici sono già disponibili. |

---

## 11. Scaletta Sviluppo Incrementale

Ogni fase rilascia valore operativo reale e autonomo.

### Fase 0 — Fondamenta

| Deliverable | Criterio di completamento |
|---|---|
| Schema database PostgreSQL completo (tutte le tabelle di sezione 3) | Migration Alembic applicata senza errori |
| Connessione SQL Server EasyJob + sync batch per le 5 tabelle | I dati di EasyJob sono leggibili e aggiornati in PostgreSQL |
| APScheduler configurato con frequenze tabella 4.2 | Job schedulati in esecuzione, `sync_log` aggiornato |
| Admin panel minimo: mostra dati importati, errori, timestamp | Dati visibili e sync log leggibile |
| Docker-compose con PostgreSQL + backend FastAPI | `docker-compose up` avvia tutto correttamente |

### Fase 1 — Produzione: viste F1a e F1b (solo lettura)

| Deliverable | Criterio di completamento |
|---|---|
| F1a: vista ordini cliente filtrata con flag urgenza e data scaduta | Operatore produzione usa F1a ogni mattina per almeno una settimana |
| Export Excel commesse importabile in EasyJob | File generato importato con successo in EasyJob almeno una volta |
| F1b: vista scorte da ricostituire con algoritmo corretto | Algoritmo scorte con le 3 correzioni bug implementate e verificate |
| Anagrafica articoli MRS — interfaccia configurazione parametri | Ogni articolo ha `tipo_produzione` e `mesi_scorta` configurati |

### Fase 2 — Produzione: schedulazione F2 + terminale magazzino

| Deliverable | Criterio di completamento |
|---|---|
| F2: coda drag&drop per macchina con stati commessa | Produzione usa F2 per pianificare la giornata |
| Terminale magazzino kiosk: scansione barcode, conferma qty consegnata | Terminale attivo, scansione funzionante |
| Magazzino F5: vista articoli in attesa registrazione EasyJob | F5 si aggiorna dopo scansione e si svuota dopo registrazione EasyJob |
| Lista di produzione PDF per macchina | PDF generato correttamente con `qty_ciclo_corrente` |

### Fase 3 — Magazzino completo

| Deliverable | Criterio di completamento |
|---|---|
| Logistica F1: configurazione policy clienti | Almeno l'80% dei clienti attivi ha policy configurata |
| Magazzino F1: vista ordini filtrata per policy | Magazzino approntisce ordini usando F1 invece dei fogli |
| Magazzino F2/F3/F4 | Operativi con dati colli/peso registrati in MRS |
| Magazzino F4: handoff digitale a logistica | Flusso cartaceo magazzino → logistica sostituito da evento digitale |

### Fase 4 — Logistica completa + Modulo eventi

| Deliverable | Criterio di completamento |
|---|---|
| Modulo eventi: infrastruttura + notifiche in-app | Tutti e 5 i tipi di evento della mappa MVP funzionanti |
| Logistica F2: gestione urgenze formali con feedback produzione | Prima urgenza gestita interamente via MRS |
| Logistica F3a/F3b/F3c | Logista usa F3c come riferimento per creare DDT in EasyJob |
| Calendario operativo condiviso | Flusso ordine completo da Fabisogno a spedizione senza fogli cartacei |

### Fase 5 — Reparto Produzione (parallela, introduzione graduale)

| Sotto-fase | Deliverable | Periodo |
|---|---|---|
| Fase 0 reparto | Anagrafica macchine, utensili, cicli. In ufficio, nessun impatto reparto. | Apr–Mag 2026 |
| Fase 1 reparto | Terminale kiosk sola lettura: coda per macchina | Giu–Lug 2026 |
| Fase 2 reparto | Scansione barcode a fine lavoro → alimenta F5 magazzino | Ago–Set 2026 |
| Fase 3 reparto | Schermata setup all'avvio commessa | Ott 2026 |
| Fase 4 reparto | Raccolta tempi implicita + pezzi prodotti a fine fase | Nov–Dic 2026 |

---

## 12. Regole e Convenzioni per Claude Code

### 12.1 Convenzioni backend (Python / FastAPI)

| Regola | Dettaglio |
|---|---|
| UUID ovunque | Tutte le PK sono UUID. Usare `uuid.uuid4()` in Python o `gen_random_uuid()` in PostgreSQL. |
| Timestamp sempre UTC | Tutti i campi timestamp usano `TIMESTAMPTZ` in PostgreSQL. In Python: `datetime.now(timezone.utc)`. |
| Pydantic per validazione | Ogni endpoint ha schema Pydantic per request e response. Mai accedere a `dict` grezzi nei router. |
| Service layer | La business logic sta in `services/`, non nei router. I router chiamano i service. |
| Errori HTTP standard | 400 = dati errati, 404 = risorsa non trovata, 409 = conflitto stato, 422 = validation error Pydantic. |
| Transizioni stato validate | Ogni endpoint che cambia stato valida la transizione prima di applicarla. Se non ammessa: 409 con messaggio chiaro. |
| Export Excel | Usare `openpyxl`. La funzione `esporta_su_easyjob()` in `services/export_easyjob.py` è l'unico punto di generazione. |

### 12.2 Convenzioni database

| Regola | Dettaglio |
|---|---|
| Nomi tabelle in italiano | `articoli`, `clienti`, `ordini`, `righe_ordine`, `commesse`, `eventi`, ecc. Coerenti con questo documento. |
| Nomi colonne snake_case | `qty_ordinata`, `data_consegna`, `tipo_produzione`, ecc. |
| Migration via Alembic | Ogni modifica schema va in una migration Alembic. Mai `ALTER TABLE` manuale in produzione. |
| Indici su chiavi esterne | Ogni FK ha il suo indice. Aggiungere indici su: `codice_easyjob`, `numero_ordine`, `stato` (commesse), `tipo+stato` (eventi). |
| Soft delete | Non cancellare mai record storici. Usare campo `attivo` (BOOLEAN) o `stato='annullato'`. |

### 12.3 Convenzioni frontend (React / TypeScript)

| Regola | Dettaglio |
|---|---|
| Un file per pagina | `src/pages/Produzione/F1a.tsx`, `src/pages/Magazzino/F3.tsx`, ecc. |
| Componenti condivisi | Tutto ciò che appare in più moduli va in `src/components/`. Es: `SyncIndicator`, `UrgenzaBadge`, `CommessaStatus`. |
| TanStack Query per dati | Ogni vista usa `useQuery` per il fetch e `useMutation` per le azioni. La cache viene invalidata dopo ogni mutation. |
| Polling ogni 30s | Le viste operative usano `refetchInterval: 30000` in `useQuery`. |
| Indicatore sync | Il componente `SyncIndicator` è presente in ogni pagina di reparto. Verde/giallo/rosso basato su `last_sync_at`. |
| Kiosk mode | Le pagine `Reparto/` usano layout dedicato: font size 120%, pulsanti min 48px height, no sidebar. |

### 12.4 Convenzioni API

| Regola | Dettaglio |
|---|---|
| Base URL | Tutti gli endpoint iniziano con `/api/` |
| Filtri come query params | `GET /api/produzione/f1a?cliente_id=...&urgenza_only=true&data_da=2026-01-01` |
| Response envelope | Lista: `{"data": [...], "total": N}`. Singolo: l'oggetto direttamente. Errore: `{"detail": "messaggio"}`. |
| CORS | In development: `allow_origins=["*"]`. In production: solo il dominio del frontend MRS. |

### 12.5 Variabili d'ambiente

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `DATABASE_URL` | SÌ | PostgreSQL connection string: `postgresql+asyncpg://user:pwd@host/mrs` |
| `EASYJOB_SERVER` | SÌ | Hostname SQL Server EasyJob |
| `EASYJOB_DATABASE` | SÌ | Nome database EasyJob |
| `EASYJOB_USER` | SÌ | Username SQL Server |
| `EASYJOB_PASSWORD` | SÌ | Password SQL Server |
| `EASYJOB_PORT` | NO DEFAULT 1433 | Porta SQL Server |
| `SECRET_KEY` | SÌ | Chiave per JWT / session (min 32 chars) |
| `RESEND_API_KEY` | NO | API key Resend per servizio mail — opzionale in MVP |
| `SYNC_INTERVAL_FAST_MIN` | NO DEFAULT 5 | Intervallo sync tabelle veloci in minuti |
| `SYNC_INTERVAL_SLOW_MIN` | NO DEFAULT 60 | Intervallo sync tabelle lente in minuti |
| `SOGLIA_MESI_STORICO` | NO DEFAULT 4 | Mesi distinti minimi per calcolo scorta mensile |

---

*MRS — Documento interno di progettazione | Versione 1.0 — Marzo 2026*
