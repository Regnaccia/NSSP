# DL-ARCH-016 — Modello di autenticazione e accesso

## Stato
Approvato

## Data
2026-03-27

---

## Decisione

Il sistema adotta un modello di accesso ibrido:

### Terminali kiosk — accesso aperto per contesto fisico

I terminali fissi associati a una macchina o a un reparto rimangono sempre autenticati. Nessun login richiesto all'operatore.

- **Terminale reparto produzione** — associato a una macchina (`macchina_id` configurato a livello di installazione). Mostra sempre la coda di quella macchina.
- **Terminale magazzino** — associato al reparto magazzino. Mostra F5 e la funzione di scansione barcode.

L'identità del terminale è configurata una volta sola tramite variabile d'ambiente o config locale (`KIOSK_CONTEXT=macchina:{id}` oppure `KIOSK_CONTEXT=magazzino`). Non ci sono dati sensibili su questi terminali — il rischio di accesso non autorizzato è accettabile in MVP.

### Postazioni operative — utenti nominali con ruolo

Le postazioni di ufficio (produzione, magazzino, logistica) richiedono login nominale.

Ogni utente ha un ruolo che determina le viste accessibili:

| Ruolo | Accesso |
|---|---|
| `produzione` | F1a, F1b, F2, anagrafica articoli MRS, F2 (sola lettura da magazzino e logistica) |
| `magazzino` | F1, F2, F3, F4, F5, F2 produzione (sola lettura) |
| `logistica` | F1 (policy), F2 (urgenze), F3a, F3b, F3c, calendario, F2 produzione (sola lettura) |
| `admin` | Tutto + gestione utenti + admin sync |

### Implementazione MVP

- **Autenticazione:** JWT con scadenza 8h (giornata lavorativa). Refresh manuale al login.
- **Gestione utenti:** endpoint admin CRUD minimal — nessuna UI elaborata in MVP, basta funzionare.
- **Tabella `utenti`:** `id`, `username`, `password_hash`, `ruolo`, `attivo`, `created_at`.
- **`created_by` sulle tabelle MRS:** stringa `username` dell'utente o `kiosk:{contesto}` per i terminali. Non è FK — è traccia leggera, non audit system.
- **Nessun SSO, nessun LDAP** in MVP.

## Variabili d'ambiente aggiuntive

| Variabile | Obbligatoria | Descrizione |
|---|---|---|
| `KIOSK_CONTEXT` | Solo su terminali kiosk | Es: `macchina:uuid-macchina` oppure `magazzino` |
| `JWT_SECRET` | SÌ | Chiave firma JWT (min 32 chars) |
| `JWT_EXPIRE_HOURS` | NO DEFAULT 8 | Durata token in ore |

## Conseguenze

- Fase 0: aggiungere tabella `utenti` allo schema e migration Alembic.
- Fase 1+: ogni endpoint operativo richiede JWT valido, eccetto gli endpoint kiosk che accettano il token di contesto configurato staticamente.
- I terminali kiosk non espongono endpoint di scrittura dati sensibili — solo azioni operative del proprio contesto (avanza commessa, scansiona barcode).
