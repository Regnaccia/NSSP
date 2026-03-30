"""
Router produzione — Ufficio Produzione.

F1a: vista ordini cliente da processare
F1b: vista scorte da ricostituire
POST /genera-commesse: crea commesse + export Excel per EasyJob
POST /ricalcola-scorte: forza ricalcolo scorta_mensile

F2: schedulazione coda di lavorazione
GET  /coda                  — vista commesse attive
POST /coda/riordina         — riordina manuale (drag&drop)
POST /commesse/{id}/assegna — assegna macchina a commessa
GET  /macchine              — lista macchine attive
"""
import base64
import csv
import io
import uuid
from datetime import datetime, timezone, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.macchina import Macchina
from app.schemas.produzione import (
    RigaF1aResponse,
    GeneraCommesseRequest,
    GeneraCommesseResponse,
    ArticoloF1bResponse,
    RicalcolaScorteRequest,
    RicalcolaScorteResponse,
)
from app.schemas.commessa import (
    CommessaResponse,
    MacchinaResponse,
    AssegnaMacchinaRequest,
    RiordinaCodaRequest,
    RiordinaCodaResponse,
)
from app.deps import require_ruolo
from app.services.disponibilita import get_righe_da_processare, get_qty_disponibile_futura
from app.services.scorte import ricalcola_scorte_tutti
from app.utils import codice_sort_key, calcola_lotti
from app.services import commesse as svc_commesse
from app.services.priorita import ricalcola_coda

router = APIRouter(
    prefix="/api/produzione",
    tags=["produzione"],
    dependencies=[Depends(require_ruolo("produzione"))],
)


# ---------------------------------------------------------------------------
# F1a — Vista ordini da processare
# ---------------------------------------------------------------------------

@router.get("/f1a", response_model=list[RigaF1aResponse])
def get_f1a(
    cliente_id: Optional[str] = Query(None),
    data_da: Optional[date] = Query(None),
    data_a: Optional[date] = Query(None),
    urgenza_only: bool = Query(False),
    famiglia: Optional[str] = Query(None),   # standard | speciali | barre
    session: Session = Depends(get_db),
):
    """Lista righe ordine che l'ufficio produzione deve ancora processare."""
    righe = get_righe_da_processare(
        session,
        cliente_id=cliente_id,
        data_da=data_da,
        data_a=data_a,
        urgenza_only=urgenza_only,
        famiglia=famiglia,
    )
    return [RigaF1aResponse(**r) for r in righe]


# ---------------------------------------------------------------------------
# F1a — Genera commesse + Excel EasyJob
# ---------------------------------------------------------------------------

@router.post("/genera-commesse", response_model=GeneraCommesseResponse)
def genera_commesse(body: GeneraCommesseRequest, session: Session = Depends(get_db)):
    """
    Per ogni riga selezionata:
    1. Carica dati articolo/ordine (F1a: da riga_ordine_id; F1b: da articolo_id)
    2. Crea Commessa (stato=in_coda)
    3. Genera Excel formato Fabisogno EasyJob
    """
    # Mesi in italiano per la nota di consegna
    MESI_IT = ["","GENNAIO","FEBBRAIO","MARZO","APRILE","MAGGIO","GIUGNO",
               "LUGLIO","AGOSTO","SETTEMBRE","OTTOBRE","NOVEMBRE","DICEMBRE"]

    commesse_create = 0
    righe_excel = []

    for riga_input in body.righe:

        # ── F1a: riga ordine cliente ────────────────────────────────────────
        if riga_input.riga_ordine_id:
            row = session.execute(
                text("""
                    SELECT ro.id AS riga_id, ro.articolo_id,
                           ro.qty_ordinata, ro.qty_disponibile, ro.qty_in_produzione,
                           a.codice AS codice_articolo, a.descrizione,
                           a.tipo_produzione, a.multipli_taglio, a.mm_materiale,
                           a.lunghezza_barra, a.misura, a.immagine,
                           mp.codice AS materia_prima_codice,
                           COALESCE(a.lunghezza_barra, mp.lunghezza_mm) AS lunghezza_effettiva,
                           o.numero_ordine, o.data_consegna,
                           c.ragione_sociale, c.nickname
                    FROM righe_ordine ro
                    JOIN articoli a     ON a.id = ro.articolo_id
                    LEFT JOIN materie_prime mp ON mp.id = a.materia_prima_id
                    JOIN ordini o       ON o.id = ro.ordine_id
                    JOIN clienti c      ON c.id = o.cliente_id
                    WHERE ro.id = :rid
                """),
                {"rid": riga_input.riga_ordine_id},
            ).mappings().fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Riga ordine {riga_input.riga_ordine_id} non trovata"
                )

            qty_da_produrre = max(
                0,
                row["qty_ordinata"] - row["qty_disponibile"] - row["qty_in_produzione"]
            )
            if qty_da_produrre <= 0:
                continue

            qty_cliente = riga_input.qty_ciclo_corrente or qty_da_produrre
            qty_scorta  = max(0, riga_input.qty_scorta)
            articolo_id = row["articolo_id"]
            numero_ordine = row["numero_ordine"]
            data_consegna = row["data_consegna"]
            cliente_label = row["nickname"] or row["ragione_sociale"]

        # ── F1b: scorta pura (nessun ordine cliente) ────────────────────────
        else:
            if not riga_input.articolo_id:
                raise HTTPException(
                    status_code=422,
                    detail="articolo_id richiesto quando riga_ordine_id è null"
                )
            row = session.execute(
                text("""
                    SELECT a.id AS articolo_id, a.codice AS codice_articolo,
                           a.descrizione, a.tipo_produzione, a.multipli_taglio,
                           a.mm_materiale, a.lunghezza_barra, a.misura, a.immagine,
                           mp.codice AS materia_prima_codice,
                           COALESCE(a.lunghezza_barra, mp.lunghezza_mm) AS lunghezza_effettiva
                    FROM articoli a
                    LEFT JOIN materie_prime mp ON mp.id = a.materia_prima_id
                    WHERE a.id = :aid
                """),
                {"aid": riga_input.articolo_id},
            ).mappings().fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Articolo {riga_input.articolo_id} non trovato"
                )

            qty_cliente   = 0
            qty_scorta    = max(0, riga_input.qty_scorta)
            articolo_id   = riga_input.articolo_id
            numero_ordine = None
            data_consegna = None
            cliente_label = None

        qty_totale = qty_cliente + qty_scorta

        # ── Calcolo lotti per note ──────────────────────────────────────────
        nr_lotti, pezzi_per_lotto, _ = calcola_lotti(
            qty_totale,
            row["tipo_produzione"] or "PEZZO",
            row["multipli_taglio"],
            row["mm_materiale"],
            row["lunghezza_effettiva"],
        )
        tipo_prod = (row["tipo_produzione"] or "PEZZO").upper()
        lunghezza  = row["lunghezza_effettiva"]

        # Costruzione note: "2 FASCI - L 3900 - CONS: APRILE" oppure "2 PEZZI"
        note_parts = [f"{nr_lotti} {tipo_prod}"]
        if lunghezza:
            note_parts.append(f"L {lunghezza}")
        if data_consegna:
            note_parts.append(f"CONS: {MESI_IT[data_consegna.month]}")
        note = " - ".join(note_parts)

        # Formato cliente nell'Excel
        if cliente_label and qty_scorta > 0:
            cliente_excel = f"{cliente_label} + MAGAZZINO"
        elif cliente_label:
            cliente_excel = cliente_label
        else:
            cliente_excel = "MAGAZZINO"

        # ── Crea commessa ───────────────────────────────────────────────────
        session.execute(
            text("""
                INSERT INTO commesse
                    (id, riga_ordine_id, articolo_id, qty_cliente, qty_scorta,
                     qty_ciclo_corrente, qty_prodotta_cliente, qty_prodotta_scorta,
                     stato, created_at, created_by)
                VALUES
                    (:id, :rid, :aid, :qc, :qs, :qcc, 0, 0, 'in_coda', :ts, :by)
            """),
            {
                "id": str(uuid.uuid4()),
                "rid": riga_input.riga_ordine_id,
                "aid": articolo_id,
                "qc": qty_cliente,
                "qs": qty_scorta,
                "qcc": qty_totale,
                "ts": datetime.now(timezone.utc),
                "by": body.created_by or "produzione",
            },
        )
        commesse_create += 1

        righe_excel.append({
            "cliente":      cliente_excel,
            "codice":       row["codice_articolo"],
            "descrizione":  row["descrizione"] or "",
            "immagine":     row.get("immagine") or "",
            "misura":       row.get("misura") or "",
            "quantita":     qty_totale,
            "materiale":    row["materia_prima_codice"] or "",
            "mm_materiale": row["mm_materiale"] or "",
            "ordine":       numero_ordine or "",
            "note":         note,
            "user":         body.created_by or "",
        })

    session.commit()

    # ── Genera CSV ──────────────────────────────────────────────────────────
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "cliente", "codice", "descrizione", "immagine",
        "misura", "quantità", "materiale", "mm_materiale",
        "ordine", "note", "user"
    ])

    for r in righe_excel:
        des_list = str([r["descrizione"]]) if r["descrizione"] else "[]"
        writer.writerow([
            r["cliente"], r["codice"], des_list, r["immagine"],
            r["misura"], r["quantita"], r["materiale"], r["mm_materiale"],
            r["ordine"], r["note"], r["user"],
        ])

    csv_b64 = base64.b64encode(buf.getvalue().encode("utf-8")).decode()

    return GeneraCommesseResponse(
        commesse_create=commesse_create,
        file_csv_base64=csv_b64,
    )


# ---------------------------------------------------------------------------
# F1b — Vista scorte da ricostituire
# ---------------------------------------------------------------------------

@router.get("/f1b", response_model=list[ArticoloF1bResponse])
def get_f1b(
    famiglia: Optional[str] = Query(None),  # standard | speciali | barre
    session: Session = Depends(get_db),
):
    """
    Lista articoli sotto scorta target.
    Famiglia: standard (prodotti finiti), speciali (cod S*), barre (cat M/L).
    Formula da_produrre = min(gap_scorta, cap_residua) — capienza come limite fisico.
    """
    sql = text("""
        SELECT a.id, a.codice, a.codice_upper, a.descrizione, a.tipo_produzione, a.categoria,
               a.scorta_mensile, a.mesi_scorta, a.storico_sufficiente, a.scorta_calcolata_at,
               a.capienza, a.giacenza_attuale, a.multipli_taglio, a.mm_materiale,
               a.lunghezza_barra, a.materia_prima_id,
               mp.codice AS materia_prima_codice,
               mp.lunghezza_mm AS mp_lunghezza_mm,
               COALESCE(a.lunghezza_barra, mp.lunghezza_mm) AS lunghezza_effettiva
        FROM articoli a
        LEFT JOIN materie_prime mp      ON mp.id = a.materia_prima_id
        LEFT JOIN categorie_articolo ca ON ca.codice = a.categoria
        WHERE a.storico_sufficiente = true
          AND (:famiglia IS NULL OR ca.famiglia = :famiglia)
        ORDER BY a.codice
    """)

    articoli_rows = session.execute(sql, {"famiglia": famiglia}).mappings().all()

    result = []
    for art in articoli_rows:
        target_scorta = art["scorta_mensile"] * art["mesi_scorta"]
        qty_disp_futura = get_qty_disponibile_futura(session, art["id"])
        gap_scorta = max(0, target_scorta - qty_disp_futura)

        if gap_scorta <= 0:
            continue

        # Capienza fisica: se impostata, limita la produzione allo spazio disponibile in magazzino
        if art["capienza"] and art["capienza"] > 0:
            cap_residua = max(0, art["capienza"] - max(0, qty_disp_futura))
            qty_da_produrre_scorta = min(gap_scorta, cap_residua)
        else:
            qty_da_produrre_scorta = gap_scorta

        if qty_da_produrre_scorta <= 0:
            continue

        tipo_prod = art["tipo_produzione"] or "PEZZO"
        lunghezza_eff = art["lunghezza_effettiva"]
        nr_lotti, pezzi_per_lotto, qty_suggerita = calcola_lotti(
            qty_da_produrre_scorta,
            tipo_prod,
            art["multipli_taglio"],
            art["mm_materiale"],
            lunghezza_eff,
        )
        result.append(ArticoloF1bResponse(
            articolo_id=art["id"],
            codice=art["codice"],
            descrizione=art["descrizione"],
            tipo_produzione=tipo_prod,
            scorta_mensile=art["scorta_mensile"],
            mesi_scorta=art["mesi_scorta"],
            target_scorta=target_scorta,
            qty_disponibile_futura=qty_disp_futura,
            qty_da_produrre_scorta=qty_da_produrre_scorta,
            scorta_calcolata_at=art["scorta_calcolata_at"],
            giacenza_attuale=art["giacenza_attuale"] or 0,
            multipli_taglio=art["multipli_taglio"],
            mm_materiale=art["mm_materiale"],
            lunghezza_barra=art["lunghezza_barra"],
            lunghezza_effettiva=lunghezza_eff,
            materia_prima_id=art["materia_prima_id"],
            materia_prima_codice=art["materia_prima_codice"],
            capienza=art["capienza"],
            flag_no_materia=art["materia_prima_id"] is None,
            nr_lotti=nr_lotti,
            pezzi_per_lotto=pezzi_per_lotto,
            qty_suggerita=qty_suggerita,
        ))

    result.sort(key=lambda r: codice_sort_key(r.codice))
    return result


# ---------------------------------------------------------------------------
# F1b — Forza ricalcolo scorte
# ---------------------------------------------------------------------------

@router.post("/ricalcola-scorte", response_model=RicalcolaScorteResponse)
def ricalcola_scorte(body: RicalcolaScorteRequest, session: Session = Depends(get_db)):
    """Forza ricalcolo scorta_mensile per tutti gli articoli o uno specifico."""
    try:
        aggiornati = ricalcola_scorte_tutti(session, articolo_id=body.articolo_id)
        return RicalcolaScorteResponse(aggiornati=aggiornati)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# F2 — Coda di lavorazione (schedulazione)
# ---------------------------------------------------------------------------

@router.get("/coda", response_model=list[CommessaResponse])
def get_coda(session: Session = Depends(get_db)):
    """Lista commesse attive (in_coda, in_produzione, sospesa) ordinate per posizione."""
    return svc_commesse.get_commesse_attive(session)


@router.post("/coda/riordina", response_model=RiordinaCodaResponse)
def riordina_coda(body: RiordinaCodaRequest, session: Session = Depends(get_db)):
    """
    Aggiorna manualmente le posizioni in coda (es. drag&drop nel frontend).
    Riceve lista [{commessa_id, posizione}] e scrive posizione_coda su ogni commessa.
    """
    from sqlalchemy import text as _text

    for voce in body.ordine:
        session.execute(
            _text("UPDATE commesse SET posizione_coda = :pos WHERE id = :cid"),
            {"pos": voce.posizione, "cid": voce.commessa_id},
        )
    session.commit()
    return RiordinaCodaResponse(aggiornate=len(body.ordine))


@router.post("/commesse/{commessa_id}/assegna", response_model=CommessaResponse)
def assegna_macchina(
    commessa_id: str,
    body: AssegnaMacchinaRequest,
    session: Session = Depends(get_db),
):
    """Assegna una macchina a una commessa in_coda o sospesa."""
    macchina = session.get(Macchina, body.macchina_id)
    if not macchina:
        raise HTTPException(status_code=404, detail="Macchina non trovata")
    try:
        return svc_commesse.assegna_macchina(session, commessa_id, body.macchina_id)
    except svc_commesse.CommessaError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/coda/ricalcola-priorita", response_model=RiordinaCodaResponse)
def ricalcola_priorita(session: Session = Depends(get_db)):
    """Ricalcola posizione_coda e priorita_suggerita in base all'algoritmo (urgenza → data → FIFO)."""
    aggiornate = ricalcola_coda(session)
    return RiordinaCodaResponse(aggiornate=aggiornate)


# ---------------------------------------------------------------------------
# F2 — Macchine (ufficio produzione)
# ---------------------------------------------------------------------------

@router.get("/macchine", response_model=list[MacchinaResponse])
def get_macchine(
    solo_attive: bool = Query(True),
    session: Session = Depends(get_db),
):
    """Lista macchine. Per default mostra solo le macchine attive."""
    q = session.query(Macchina)
    if solo_attive:
        q = q.filter(Macchina.attiva.is_(True))
    return [MacchinaResponse.model_validate(m) for m in q.order_by(Macchina.codice).all()]
