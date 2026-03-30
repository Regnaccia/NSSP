# DL-ARCH-020 — Algoritmo calcolo scorta mensile

## Stato
Approvato

## Data
2026-03-27

---

## Decisione

L'algoritmo di calcolo `scorta_mensile` adotta tre orizzonti temporali (12m, 6m, 3m) con rimozione outlier z-score applicata **prima** del calcolo dei percentili, e una soglia di mesi attivi per determinare `storico_sufficiente`.

## Motivazione

### Problema del V0

Il V0 aveva 3 bug documentati nell'algoritmo scorte:

**Bug 1 — Soglia storico mal calcolata**

V0 contava i mesi del periodo (es. 12 mesi = storico sufficiente). Ma un articolo venduto solo 2 volte in 12 mesi non ha uno storico affidabile.

V1 conta i **mesi distinti con almeno una vendita**. Solo se `mesi_con_vendite >= MESI_MINIMI` (default 4) lo storico è considerato sufficiente.

**Bug 2 — Filtraggio outlier applicato nell'ordine sbagliato**

V0 filtrava prima il periodo e poi rimuoveva gli outlier z-score. Questo è statisticamente scorretto: gli outlier influenzano la media e la deviazione standard usate per calcolare lo z-score degli altri punti.

V1 rimuove gli outlier prima di fare qualsiasi calcolo sui dati.

**Bug 3 — qty_disponibile_futura senza impegni**

V0 usava la giacenza attuale come proxy per la disponibilità futura. Ma se ci sono ordini aperti su quell'articolo, la giacenza sarà consumata da quegli ordini prima di raggiungere la scorta.

V1: `qty_disponibile_futura = giacenza - SUM(impegni ordini aperti)`

### Algoritmo V1

```python
def calcola_scorta_mensile(movimenti_12m):
    # 1. Filtra mesi con vendite
    mesi_attivi = [m for m in movimenti_12m if m['qty'] > 0]
    if len(mesi_attivi) < MESI_MINIMI:
        return (0, False)   # storico_sufficiente=False

    # 2. Rimuovi outlier z-score (|z| > 3.0) dai dati grezzi
    qty_list = [m['qty'] for m in mesi_attivi]
    media = statistics.mean(qty_list)
    stdev = statistics.stdev(qty_list) if len(qty_list) > 1 else 0
    if stdev > 0:
        qty_list = [q for q in qty_list if abs((q - media) / stdev) <= 3.0]

    # 3. Calcola percentile_80 su tre orizzonti
    ultimi_12 = qty_list
    ultimi_6  = qty_list[-6:]  if len(qty_list) >= 6  else qty_list
    ultimi_3  = qty_list[-3:]  if len(qty_list) >= 3  else qty_list

    p80_12 = percentile(ultimi_12, 80)
    p80_6  = percentile(ultimi_6,  80)
    p80_3  = percentile(ultimi_3,  80)

    # 4. Media dei tre orizzonti
    scorta = round((p80_12 + p80_6 + p80_3) / 3)
    return (scorta, True)
```

### Tre orizzonti — perché

Usare solo 12 mesi potrebbe sottostimare la scorta se il trend è in crescita (il recente pesa come il vecchio). Usare solo 3 mesi potrebbe sovrastimare in caso di picchi stagionali.

La media dei tre orizzonti bilancia trend e stagionalità senza aggiungere parametri da configurare.

## Parametri configurabili

| Variabile d'ambiente | Default | Descrizione |
|---|---|---|
| `SOGLIA_MESI_STORICO` | `4` | Mesi con vendite per storico_sufficiente=True |

`SOGLIA_Z` è hardcoded a `3.0` — valore statisticamente standard, non ha senso esporre come parametro.

## Quando si ricalcola

- **Automatico:** primo del mese alle 02:00 (job APScheduler `ricalcolo_scorte_mensile`)
- **Manuale:** `POST /api/produzione/ricalcola-scorte` (body opzionale: `articolo_id` per ricalcolare un solo articolo)

## Fonte dati

```sql
SELECT ART_COD,
       YEAR(DOC_DATA) AS anno,
       MONTH(DOC_DATA) AS mese,
       SUM(PEZZI_SCA) AS qty
FROM MAG_REALE
WHERE CAUM_COD = 'VEN'
  AND DOC_DATA >= DATEADD(month, -12, GETDATE())
GROUP BY ART_COD, YEAR(DOC_DATA), MONTH(DOC_DATA)
```

La query viene eseguita sulla connessione EasyJob (SQL Server) e i risultati vengono processati in memoria Python.
