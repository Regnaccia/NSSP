# DL-ARCH-018 — Export Excel via base64 in JSON response

## Stato
Approvato

## Data
2026-03-27

---

## Decisione

Il file Excel generato da `POST /api/produzione/genera-commesse` viene restituito come stringa base64 nel body JSON della response, non come file stream separato.

```json
{
  "commesse_create": 3,
  "file_excel_base64": "UEsDBBQAAAAIAA..."
}
```

## Motivazione

### Opzioni considerate

**Opzione A — File stream (Content-Type: application/octet-stream)**
Il server scrive il file su un path temporaneo e risponde con `FileResponse`. Il frontend triggera il download automaticamente.

**Opzione B — base64 in JSON** *(scelta)*
Il file viene serializzato in base64 e incluso nel body JSON. Il frontend decodifica e usa `Blob + URL.createObjectURL()` per il download.

### Perché base64

- **Atomicità**: la response contiene sia il conteggio delle commesse create che il file — in un'unica transazione HTTP. Con lo stream, il frontend non sa quante commesse sono state create.
- **Nessun filesystem temporaneo**: il server non deve gestire file temporanei con cleanup. In MVP con un singolo processo uvicorn questo è semplice, ma il cleanup affidabile è comunque complessità non necessaria.
- **Compatibilità**: il frontend può salvare il file o aprirlo in-memory senza dipendere dalla gestione sessioni per endpoint separati.
- **Dimensioni accettabili**: i file Fabisogno hanno al massimo qualche centinaio di righe — l'overhead base64 (~33%) è trascurabile.

## Limiti accettati

- Non adatto per file molto grandi (> 5 MB). Se in futuro il file cresce per ristampe storiche, si valuta lo streaming.
- Il debugging della response è meno immediato (il base64 non è human-readable inline).

## Implementazione

```python
buf = io.BytesIO()
wb.save(buf)
excel_b64 = base64.b64encode(buf.getvalue()).decode()
```

Il frontend decodifica con:
```js
const bytes = atob(response.file_excel_base64)
const blob = new Blob([bytes], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
const url = URL.createObjectURL(blob)
```
