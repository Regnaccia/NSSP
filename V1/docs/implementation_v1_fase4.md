# IMPLEMENTATION V1 — Fase 4: Eventi Inter-Reparto + Auth JWT

*Data: 2026-03-30*

---

## Obiettivo

Completare il layer trasversale del sistema:

- **Eventi** — comunicazioni inter-reparto tracciate (urgenze formali, feedback, risoluzioni)
- **Auth JWT** — login nominale, token, CRUD utenti per postazioni operative (DL-ARCH-016)

Prerequisito: Fase 3 completata. Il backend è ora funzionale senza auth — questa fase aggiunge il layer di sicurezza e il canale di comunicazione tra reparti.

---

## File creati

### `app/schemas/evento.py`

| Schema | Uso |
|---|---|
| `UrgenzaRequest` | Body POST urgenza (ordine_id, nota, created_by) |
| `FeedbackRequest` | Body POST feedback (feedback_stato, data_prevista, nota, corriere_override) |
| `RisolviRequest` | Body POST risolvi/rifiuta (nota opzionale) |
| `EventoResponse` | Evento completo con join numero_ordine e cliente |

### `app/schemas/auth.py`

| Schema | Uso |
|---|---|
| `LoginRequest` | Body POST login (username, password) |
| `TokenResponse` | Response login (access_token, token_type, username, ruolo) |
| `UtenteCreateRequest` | Body POST utenti (username, password, ruolo) |
| `UtentePatchRequest` | Body PATCH utente (password?, ruolo?, attivo?) |
| `UtenteResponse` | Utente (id, username, ruolo, attivo, created_at) |

---

### `app/services/eventi.py`

**`get_eventi(session, tipo, destinatario, stato, ref_ordine_id) → list[dict]`**

Lista eventi con filtri opzionali. Ogni evento è arricchito con `numero_ordine` e `cliente` via join.

**`get_evento_detail(session, evento_id) → dict | None`**

Dettaglio singolo evento.

**`crea_urgenza(session, ordine_id, nota, created_by) → dict`**

Crea evento `urgenza_formale`, mittente=`logistica`, destinatario=`produzione`.
**Ricalcola automaticamente la coda** dopo la creazione — le commesse dell'ordine urgente salgono in priorità (l'algoritmo `priorita.ricalcola_coda` usa `flag_urgenza` nell'ordinamento).

**`dai_feedback(session, evento_id, feedback_stato, ...) → dict`**

La produzione risponde all'urgenza:
- `feedback_stato = 'accettata'` → la produzione accelererà
- `feedback_stato = 'non_fattibile'` → impossibile rispettare la scadenza

L'evento passa a stato `in_lavorazione`. Campi scritti: `feedback_stato`, `feedback_data_prevista`, `feedback_nota`, `corriere_override`.

**`risolvi_evento(session, evento_id, nota) → dict`**

Segna come `risolto`. Per urgenze: **ricalcola la coda** — l'urgenza non è più attiva, le commesse tornano all'ordinamento normale.

**`rifiuta_evento(session, evento_id, nota) → dict`**

Segna come `rifiutato`. Non ricalcola la coda.

---

### `app/services/auth.py`

**Password — bcrypt (passlib)**

```python
hash_password(plain: str) → str
verify_password(plain: str, hashed: str) → bool
```

**JWT — PyJWT**

```python
create_token(utente_id, username, ruolo) → str
decode_token(token) → dict   # lancia AuthError se scaduto/invalido
```

Payload JWT: `{sub: utente_id, username, ruolo, exp}`.
Durata: `JWT_EXPIRE_HOURS` (default 8h, configurabile in `easy.env`).

**CRUD utenti**

| Funzione | Descrizione |
|---|---|
| `login(session, username, password)` | Verifica credenziali → ritorna dict con token |
| `crea_utente(session, username, password, ruolo)` | Crea utente con password hashata |
| `get_utenti(session)` | Lista tutti gli utenti |
| `aggiorna_utente(session, id, data)` | Aggiorna password/ruolo/attivo |

Ruoli validi: `produzione`, `magazzino`, `logistica`, `admin`.

---

### `app/deps.py`

FastAPI dependency injections per autenticazione.

**`get_current_user`**

Legge il token dal header `Authorization: Bearer <token>`, lo decodifica, ritorna il payload.
Lancia `HTTP 401` se il token manca, è scaduto o non valido.

**`require_admin`**

Chiama `get_current_user` e verifica `ruolo == 'admin'`. Lancia `HTTP 403` altrimenti.

**`require_ruolo(*ruoli)`**

Factory per dependency a ruolo specifico:

```python
@router.get("/...", dependencies=[Depends(require_ruolo("produzione", "logistica"))])
```

Accetta anche `admin` in aggiunta ai ruoli specificati.

**Terminali kiosk (DL-ARCH-016)**

I router `/api/reparto` e `/api/magazzino` non usano queste dependency in MVP — sono terminali fisici con contesto configurato via `KIOSK_CONTEXT`. In produzione si può aggiungere un token kiosk statico.

---

### `app/routers/eventi.py`

| Method | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/eventi` | Lista con filtri (tipo, destinatario, stato, ref_ordine_id) |
| `GET` | `/api/eventi/{id}` | Dettaglio evento |
| `POST` | `/api/eventi/urgenza` | Crea urgenza_formale (201) |
| `POST` | `/api/eventi/{id}/feedback` | Risposta produzione a urgenza |
| `POST` | `/api/eventi/{id}/risolvi` | Segna come risolto |
| `POST` | `/api/eventi/{id}/rifiuta` | Rifiuta/annulla |

### `app/routers/auth.py`

| Method | Endpoint | Accesso | Descrizione |
|---|---|---|---|
| `POST` | `/api/auth/login` | Pubblico | Login → JWT token |
| `GET` | `/api/auth/me` | JWT valido | Info utente corrente |
| `POST` | `/api/auth/utenti` | Admin | Crea utente |
| `GET` | `/api/auth/utenti` | Admin | Lista utenti |
| `PATCH` | `/api/auth/utenti/{id}` | Admin | Aggiorna utente |

---

## Flusso urgenza completo

```
Logistica         Produzione         Sistema
    │                                    │
    │── POST /eventi/urgenza ────────────►│
    │                                    │ crea_urgenza()
    │                                    │ ricalcola_coda()  ← urgenza pesa nell'ordine
    │                                    │
    │            F1a mostra flag_urgenza=True su quell'ordine
    │                  │
    │                  │── POST /eventi/{id}/feedback ──────►│
    │                  │   {feedback_stato: "accettata",      │
    │                  │    feedback_data_prevista: ...}       │ ev.stato = in_lavorazione
    │                  │
    │◄─── Logistica vede feedback in GET /eventi ────────────│
    │
    │── POST /eventi/{id}/risolvi ──────────────────────────►│
    │                                                        │ ev.stato = risolto
    │                                                        │ ricalcola_coda()  ← urgenza rimossa
```

---

## Setup primo utente admin

Dopo `alembic upgrade head`, creare il primo admin via psql o script:

```bash
# via psql
docker exec -it nssp_postgres psql -U nssp_user -d mrs_v1 -c "
INSERT INTO utenti (id, username, password_hash, ruolo, attivo, created_at)
VALUES (
  gen_random_uuid()::text,
  'admin',
  '\$2b\$12\$...',   -- hash generato con: python -c \"from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('password'))\"
  'admin',
  true,
  NOW()
);"
```

Oppure aggiungere uno script di seed a `V1/backend/scripts/create_admin.py` (non incluso nel backend, esecuzione manuale una tantum).

---

## Errori gestiti

| Condizione | HTTP |
|---|---|
| Token assente | 401 |
| Token scaduto | 401 |
| Token non valido | 401 |
| Ruolo insufficiente | 403 |
| Credenziali login errate | 401 |
| Username già in uso | 409 |
| Ruolo non valido | 409 |
| Evento non trovato | 404 |
| Feedback su evento non-urgenza | 409 |
| Evento già risolto/rifiutato | 409 |
| Feedback_stato non valido | 409 |

---

## Stato finale backend — API complete

### Sync
| `GET /api/sync/status` | `POST /api/sync/force/{tabella}` | `POST /api/sync/force-all` |

### Produzione (Ufficio)
| F1a | F1b | genera-commesse | ricalcola-scorte | coda | riordina | ricalcola-priorita | assegna | macchine |

### Reparto (Terminale)
| macchine | coda macchina | avvia | sospendi | riprendi | aggiorna-qty | completa |

### Articoli
| lista | dettaglio | PATCH MRS-owned |

### Magazzino
| da-approntare | consegne | consegne ordine | pronto |

### Logistica
| da-spedire | clienti | patch-nickname | policy GET/PUT | spedizioni CRUD | spedita | calendario |

### Eventi
| lista | dettaglio | urgenza | feedback | risolvi | rifiuta |

### Auth
| login | me | utenti CRUD (admin) |

---

## Fase successiva

Il backend MVP è completo. Il passo successivo naturale è:

1. **Frontend React** — viste per reparto (F1a, F2 drag&drop, terminale kiosk, logistica)
2. **Script seed admin** — creazione primo utente admin
3. **Protezione endpoint** — aggiungere `Depends(get_current_user)` sugli endpoint operativi
4. **Deploy** — docker-compose con nginx reverse proxy per produzione
