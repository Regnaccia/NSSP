"""
services/scorte.py — Algoritmo calcolo scorta mensile (DL-ARCH-007, computed fact persistito).

Bug corretti rispetto a V0 (da spec MRS_Specifiche_Tecniche_v1.md §5.2):
1. MESI_MINIMI: conta mesi distinti con vendite, non movimenti totali
2. ORDINE Z-SCORE: filtra periodo PRIMA di applicare z-score (non dopo)
3. IMPEGNI FUTURI: qty_disponibile_futura = giacenza - impegni aperti
"""
import logging
import os
from datetime import datetime, timezone
from statistics import mean, stdev, quantiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.sync.easyjob import fetch_easyjob

logger = logging.getLogger(__name__)

MESI_MINIMI = int(os.getenv("SOGLIA_MESI_STORICO", "4"))
SOGLIA_Z = 3.0


# ---------------------------------------------------------------------------
# Algoritmo puro (senza DB — testabile in isolamento)
# ---------------------------------------------------------------------------

def calcola_scorta_mensile(movimenti_12m: list[dict]) -> tuple[int, bool]:
    """
    Calcola scorta mensile da lista movimenti ultimi 12 mesi.

    Args:
        movimenti_12m: lista di {"anno": int, "mese": int, "qty": int}

    Returns:
        (scorta_mensile, storico_sufficiente)
        Se storico insufficiente → (0, False)
    """
    # 1. Raggruppa per mese, conta mesi distinti con vendite
    per_mese: dict[tuple[int, int], int] = {}
    for m in movimenti_12m:
        k = (m["anno"], m["mese"])
        per_mese[k] = per_mese.get(k, 0) + int(m["qty"] or 0)

    mesi_con_vendite = [k for k, q in per_mese.items() if q > 0]
    if len(mesi_con_vendite) < MESI_MINIMI:
        return 0, False

    def _percentile_80(valori: list[float]) -> float:
        if not valori:
            return 0.0
        if len(valori) == 1:
            return float(valori[0])
        return quantiles(valori, n=10)[7]  # 80° percentile (indice 7 di 10 quantili)

    def _filtra_zscore(valori: list[float]) -> list[float]:
        if len(valori) < 2:
            return valori
        m = mean(valori)
        s = stdev(valori)
        if s == 0:
            return valori
        return [v for v in valori if abs((v - m) / s) < SOGLIA_Z]

    def _ultimi_n_mesi(n: int) -> list[float]:
        """Prende i valori degli ultimi n mesi (ordinati cronologicamente)."""
        chiavi_ordinate = sorted(per_mese.keys())
        chiavi_periodo = chiavi_ordinate[-n:] if len(chiavi_ordinate) >= n else chiavi_ordinate
        return [float(per_mese[k]) for k in chiavi_periodo]

    # 2. Tre orizzonti: 12m, 6m, 3m
    # CORRETTO: filtra periodo PRIMA dello z-score
    risultati = []
    for n_mesi in [12, 6, 3]:
        valori_periodo = _ultimi_n_mesi(n_mesi)
        valori_filtrati = _filtra_zscore(valori_periodo)
        risultati.append(_percentile_80(valori_filtrati))

    # 3. Media dei tre risultati
    scorta = round(mean(risultati))
    return max(0, scorta), True


# ---------------------------------------------------------------------------
# Ricalcolo batch: legge da EasyJob + aggiorna DB
# ---------------------------------------------------------------------------

def _fetch_movimenti_vendite() -> dict[str, list[dict]]:
    """
    Legge storico vendite ultimi 12 mesi da MAG_REALE (EasyJob).
    Ritorna dict {art_cod_upper: [{anno, mese, qty}]}.
    """
    rows = fetch_easyjob("""
        SELECT
            ART_COD,
            YEAR(DOC_DATA)  AS anno,
            MONTH(DOC_DATA) AS mese,
            SUM(PEZZI_SCA)  AS qty
        FROM MAG_REALE
        WHERE CAUM_COD = 'VEN'
          AND DOC_DATA >= DATEADD(month, -12, GETDATE())
          AND PEZZI_SCA > 0
        GROUP BY ART_COD, YEAR(DOC_DATA), MONTH(DOC_DATA)
    """)

    result: dict[str, list[dict]] = {}
    for r in rows:
        cod = (r["ART_COD"] or "").strip().upper()
        if not cod:
            continue
        result.setdefault(cod, []).append({
            "anno": int(r["anno"]),
            "mese": int(r["mese"]),
            "qty": int(r["qty"] or 0),
        })
    return result


def ricalcola_scorte_tutti(session: Session, articolo_id: str | None = None) -> int:
    """
    Ricalcola scorta_mensile per tutti gli articoli (o uno solo se articolo_id fornito).
    Aggiorna: articoli.scorta_mensile, storico_sufficiente, scorta_calcolata_at.
    Ritorna numero articoli aggiornati.
    """
    try:
        movimenti_per_articolo = _fetch_movimenti_vendite()
    except Exception as exc:
        logger.error("Impossibile leggere MAG_REALE per ricalcolo scorte: %s", exc)
        return 0

    # Articoli da aggiornare
    if articolo_id:
        articoli = session.execute(
            text("SELECT id, codice_upper FROM articoli WHERE id = :id"),
            {"id": articolo_id},
        ).mappings().all()
    else:
        articoli = session.execute(
            text("""
                SELECT id, codice_upper FROM articoli
                WHERE tipo_produzione IN ('PEZZO', 'BARRA', 'FASCI')
            """)
        ).mappings().all()

    aggiornati = 0
    now = datetime.now(timezone.utc)

    for art in articoli:
        cod_upper = (art["codice_upper"] or "").upper()
        movimenti = movimenti_per_articolo.get(cod_upper, [])
        scorta, sufficiente = calcola_scorta_mensile(movimenti)

        session.execute(
            text("""
                UPDATE articoli SET
                    scorta_mensile      = :scorta,
                    storico_sufficiente = :suff,
                    scorta_calcolata_at = :ts
                WHERE id = :id
            """),
            {
                "scorta": scorta,
                "suff": sufficiente,
                "ts": now,
                "id": art["id"],
            },
        )
        aggiornati += 1

    session.commit()
    logger.info("Ricalcolo scorte completato: %d articoli aggiornati", aggiornati)
    return aggiornati
