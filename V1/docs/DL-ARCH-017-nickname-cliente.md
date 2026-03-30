# DL-ARCH-017 — Nickname operativo per clienti e destinazioni

## Stato
Approvato

## Data
2026-03-27

---

## Decisione

Ogni cliente (e in futuro ogni destinazione) può avere un **nickname operativo** usato in tutte le viste interne MRS al posto della ragione sociale completa.

## Motivazione

La ragione sociale di EasyJob è spesso lunga, formale e poco leggibile nelle viste operative ("Società Claude di Claudio AI Srl sede Online"). Gli operatori già usano nomi brevi informali nella comunicazione quotidiana. MRS formalizza questo alias nel sistema invece di ignorarlo.

## Implementazione

### Schema

Aggiungere campo `nickname` alla tabella `clienti`:

| Campo | Tipo PG | Nullable | Descrizione |
|---|---|---|---|
| `nickname` | `VARCHAR(50)` | YES | Nome operativo breve — usato nelle viste interne MRS |

- `nickname` è `NULL` di default alla prima importazione da EasyJob.
- Il sync EasyJob **non tocca mai** il campo `nickname` — è MRS-owned.
- Se `nickname` è NULL, le viste mostrano `ragione_sociale` come fallback.

### Regola di visualizzazione (applicata ovunque in MRS)

```python
def nome_cliente(cliente) -> str:
    return cliente.nickname or cliente.ragione_sociale
```

Questa funzione è l'unico punto dove si decide cosa mostrare — non duplicare la logica nelle viste.

### Dove si configura

Il nickname si imposta dalla stessa schermata della policy cliente in **Logistica F1**. È un campo opzionale nella form di configurazione cliente — chi non ha policy lo può impostare comunque dalla lista clienti.

### API

`PATCH /api/clienti/{id}` — già previsto nella spec. Il campo `nickname` è incluso nel body aggiornabile.

## Note

- Nessuna validazione di unicità — due clienti possono avere lo stesso nickname, è un alias operativo non un identificatore.
- Massimo 50 caratteri — abbastanza per un nome corto leggibile in una colonna di tabella.
- In futuro: stesso campo `nickname` su `destinazioni` quando il modulo destinazioni verrà sviluppato.
