# MRS Backend — Autenticazione e Autorizzazione

## Indice
1. [Meccanismo JWT](#1-meccanismo-jwt)
2. [Ruoli e permessi](#2-ruoli-e-permessi)
3. [Come usare il token (frontend)](#3-come-usare-il-token-frontend)
4. [Matrice guard per router](#4-matrice-guard-per-router)
5. [Endpoint Auth](#5-endpoint-auth)
6. [Codici di errore](#6-codici-di-errore)

---

## 1. Meccanismo JWT

### Flusso login

```
POST /api/auth/login  {"username": "mario", "password": "..."}
        │
        ▼
bcrypt.checkpw(plain, hash_db)
        │ OK
        ▼
jwt.encode({sub, username, ruolo, exp}, JWT_SECRET, HS256)
        │
        ▼
{"access_token": "eyJ...", "token_type": "bearer", "username": "mario", "ruolo": "produzione"}
```

### Payload del token

```json
{
  "sub": "uuid-utente",
  "username": "mario",
  "ruolo": "produzione",
  "exp": 1743000000
}
```

### Parametri

| Parametro | Valore | Configurazione |
|---|---|---|
| Algoritmo | HS256 | fisso |
| Scadenza | 8 ore | `JWT_EXPIRE_HOURS` in env |
| Chiave | `insecure-dev-secret-change-in-production` | `JWT_SECRET` in env — **cambiare in prod** |

### Dipendenze FastAPI

**`app/deps.py`** espone tre dipendenze:

| Dipendenza | Uso | Comportamento |
|---|---|---|
| `get_current_user` | Qualsiasi utente autenticato | 401 se token mancante/invalido/scaduto |
| `require_admin` | Solo ruolo `admin` | 403 se ruolo ≠ admin |
| `require_ruolo("logistica")` | Ruolo specifico (+ admin sempre ammesso) | 403 se ruolo non autorizzato |

---

## 2. Ruoli e permessi

| Ruolo | Descrizione | Router accessibili |
|---|---|---|
| `admin` | Amministratore di sistema | Tutto |
| `produzione` | Ufficio produzione | `/api/produzione`, `/api/articoli`, `/api/eventi` |
| `logistica` | Ufficio logistica | `/api/logistica`, `/api/articoli`, `/api/eventi` |
| `magazzino` | Operatore magazzino | Il router `/api/magazzino` è kiosk (no auth) |

> **Regola admin:** il ruolo `admin` ha sempre accesso a tutti i router protetti, anche quelli riservati a un singolo ruolo (`require_ruolo` lo include esplicitamente).

---

## 3. Come usare il token (frontend)

### 3.1 Login e salvataggio token

```typescript
const response = await fetch('/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username, password })
})
const { access_token, ruolo, username } = await response.json()
// Salva in localStorage o memory store (Zustand)
localStorage.setItem('mrs_token', access_token)
```

### 3.2 Aggiungere il token a ogni richiesta

```typescript
const token = localStorage.getItem('mrs_token')
const response = await fetch('/api/produzione/f1a', {
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  }
})
```

### 3.3 Gestione scadenza (8 ore)

Quando il token scade, il backend risponde:
```json
HTTP 401
{"detail": "Token scaduto — effettuare nuovamente il login"}
```

Il frontend deve intercettare il 401 e reindirizzare al login. Con axios:
```typescript
axios.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('mrs_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)
```

### 3.4 Decodifica payload lato client (senza verifica firma)

```typescript
function parseJwt(token: string) {
  const base64 = token.split('.')[1]
  return JSON.parse(atob(base64))
}
const { ruolo, username, exp } = parseJwt(token)
```

Utile per mostrare il nome utente e nascondere elementi UI in base al ruolo — **non** usare per controllo accesso critico (quello lo fa il backend).

---

## 4. Matrice guard per router

| Router | Prefisso | Guard | Note |
|---|---|---|---|
| Auth | `/api/auth` | Misto (vedi sotto) | Login è pubblico |
| Articoli | `/api/articoli` | `get_current_user` | Tutti gli utenti autenticati |
| Produzione | `/api/produzione` | `require_ruolo("produzione")` | Admin ammesso |
| Reparto | `/api/reparto` | **Nessuno** | Kiosk fisso in reparto |
| Magazzino | `/api/magazzino` | **Nessuno** | Kiosk fisso in magazzino |
| Logistica | `/api/logistica` | `require_ruolo("logistica")` | Admin ammesso |
| Eventi | `/api/eventi` | `get_current_user` | Tutti gli utenti autenticati |
| Sync | `/api/sync` | `require_admin` | Solo admin |

### Dettaglio router Auth

| Endpoint | Guard |
|---|---|
| `POST /api/auth/login` | Pubblico |
| `GET /api/auth/me` | `get_current_user` |
| `POST /api/auth/utenti` | `require_admin` |
| `GET /api/auth/utenti` | `require_admin` |
| `PATCH /api/auth/utenti/{id}` | `require_admin` |

---

## 5. Endpoint Auth

### POST /api/auth/login

Autentica un utente e restituisce il token JWT.

**Request:**
```json
{
  "username": "mario",
  "password": "password123"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "mario",
  "ruolo": "produzione"
}
```

**Errori:**
- `401` — credenziali non valide o utente disabilitato

---

### GET /api/auth/me

Restituisce le informazioni dell'utente corrente dal token.

**Response 200:**
```json
{
  "sub": "uuid",
  "username": "mario",
  "ruolo": "produzione",
  "exp": 1743000000
}
```

---

### POST /api/auth/utenti *(solo admin)*

Crea un nuovo utente.

**Request:**
```json
{
  "username": "lucia",
  "password": "password123",
  "ruolo": "logistica"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "username": "lucia",
  "ruolo": "logistica",
  "attivo": true,
  "created_at": "2026-03-27T10:00:00Z"
}
```

**Errori:**
- `409` — username già in uso
- `409` — ruolo non valido (validi: `admin`, `produzione`, `logistica`, `magazzino`)
- `403` — non sei admin

---

### GET /api/auth/utenti *(solo admin)*

Lista tutti gli utenti.

**Response 200:**
```json
[
  {"id": "uuid", "username": "mario", "ruolo": "produzione", "attivo": true, "created_at": "..."},
  ...
]
```

---

### PATCH /api/auth/utenti/{id} *(solo admin)*

Aggiorna password, ruolo o stato attivo di un utente.

**Request** (tutti i campi opzionali):
```json
{
  "password": "nuovapassword",
  "ruolo": "logistica",
  "attivo": false
}
```

**Response 200:** oggetto `UtenteResponse` aggiornato

**Errori:**
- `409` — utente non trovato
- `409` — ruolo non valido

---

## 6. Codici di errore

| HTTP | Quando |
|---|---|
| `400` | Parametri query invalidi (es. `data_a < data_da` nel calendario) |
| `401` | Token mancante, scaduto o con firma invalida |
| `403` | Token valido ma ruolo non autorizzato |
| `404` | Risorsa non trovata (ordine, articolo, commessa, ecc.) |
| `409` | Conflitto di business logic (duplicato, transizione invalida, stato non corretto) |
| `500` | Errore interno imprevisto (raro, loggato server-side) |

### Formato errore

Tutti gli errori usano il formato standard FastAPI:
```json
{
  "detail": "Messaggio descrittivo dell'errore"
}
```
