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
    session: Session = Depends(get_db),
):
    """Lista righe ordine che l'ufficio produzione deve ancora processare."""
    righe = get_righe_da_processare(
        session,
        cliente_id=cliente_id,
        data_da=data_da,
        data_a=data_a,
        urgenza_only=urgenza_only,
    )
    return [RigaF1aResponse(**r) for r in righe]


# ---------------------------------------------------------------------------
# F1a — Genera commesse + Excel EasyJob
# ---------------------------------------------------------------------------

@router.post("/genera-commesse", response_model=GeneraCommesseResponse)
def genera_commesse(body: GeneraCommesseRequest, session: Session = Depends(get_db)):
    """
    Per ogni riga selezionata:
    1. Verifica che la riga esista e sia ancora da processare
    2. Crea una Commessa (stato=in_coda)
    3. Genera file Excel con le righe commessa (formato Fabisogno EasyJob)
    """
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl non installato — eseguire: pip install openpyxl"
        )

    commesse_create = 0
    righe_excel = []

    for riga_input in body.righe:
        # Leggi riga ordine
        riga = session.execute(
            text("""
                SELECT ro.*, a.codice AS codice_articolo, a.descrizione,
                       o.numero_ordine, o.data_consegna, c.ragione_sociale, c.nickname
                FROM righe_ordine ro
                JOIN articoli a ON a.id = ro.articolo_id
                JOIN ordini o   ON o.id = ro.ordine_id
                JOIN clienti c  ON c.id = o.cliente_id
                WHERE ro.id = :rid
            """),
            {"rid": riga_input.riga_ordine_id},
        ).mappings().fetchone()

        if not riga:
            raise HTTPException(
                status_code=404,
                detail=f"Riga ordine {riga_input.riga_ordine_id} non trovata"
            )

        qty_da_produrre = max(
            0,
            riga["qty_ordinata"] - riga["qty_disponibile"] - riga["qty_in_produzione"]
        )
        if qty_da_produrre <= 0:
            continue  # nel frattempo già coperta — skip silenzioso

        qty_cliente = qty_da_produrre
        qty_ciclo = riga_input.qty_ciclo_corrente  # None = tutto
        qty_scorta = max(0, riga_input.qty_scorta)

        # Crea commessa
        commessa_id = str(uuid.uuid4())
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
                "id": commessa_id,
                "rid": riga_input.riga_ordine_id,
                "aid": riga["articolo_id"],
                "qc": qty_cliente,
                "qs": qty_scorta,
                "qcc": qty_ciclo,
                "ts": datetime.now(timezone.utc),
                "by": body.created_by or "produzione",
            },
        )
        commesse_create += 1

        righe_excel.append({
            "numero_ordine": riga["numero_ordine"],
            "codice_articolo": riga["codice_articolo"],
            "descrizione": riga["descrizione"] or "",
            "cliente": riga["nickname"] or riga["ragione_sociale"],
            "data_consegna": riga["data_consegna"],
            "qty_cliente": qty_cliente,
            "qty_scorta": qty_scorta,
            "qty_totale": qty_cliente + qty_scorta,
            "qty_ciclo": qty_ciclo or (qty_cliente + qty_scorta),
            "note": f"Ordine {riga['numero_ordine']}",
        })

    session.commit()

    # Genera Excel
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Commesse MRS"

    intestazioni = [
        "N. Ordine", "Codice Articolo", "Descrizione", "Cliente",
        "Data Consegna", "Qty Cliente", "Qty Scorta", "Qty Totale",
        "Qty Ciclo Corrente", "Note"
    ]
    ws.append(intestazioni)

    for r in righe_excel:
        ws.append([
            r["numero_ordine"],
            r["codice_articolo"],
            r["descrizione"],
            r["cliente"],
            r["data_consegna"].isoformat() if r["data_consegna"] else "",
            r["qty_cliente"],
            r["qty_scorta"],
            r["qty_totale"],
            r["qty_ciclo"],
            r["note"],
        ])

    buf = io.BytesIO()
    wb.save(buf)
    excel_b64 = base64.b64encode(buf.getvalue()).decode()

    return GeneraCommesseResponse(
        commesse_create=commesse_create,
        file_excel_base64=excel_b64,
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
        SELECT id, codice, codice_upper, descrizione, tipo_produzione, categoria,
               scorta_mensile, mesi_scorta, storico_sufficiente, scorta_calcolata_at,
               capienza, giacenza_attuale
        FROM articoli
        WHERE storico_sufficiente = true
          AND (
              :famiglia IS NULL
              OR (:famiglia = 'barre'    AND categoria IN ('M','L'))
              OR (:famiglia = 'speciali' AND (categoria = 'S' OR codice_upper LIKE 'S%'))
              OR (:famiglia = 'standard' AND categoria NOT IN ('M','L','S','0','Z','MC','U')
                                        AND codice_upper NOT LIKE 'S%'
                                        AND codice_upper NOT LIKE 'BCL%'
                                        AND codice_upper NOT LIKE 'CERT%'
                                        AND codice_upper NOT IN ('XS','CONF','0'))
          )
        ORDER BY codice
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

        result.append(ArticoloF1bResponse(
            articolo_id=art["id"],
            codice=art["codice"],
            descrizione=art["descrizione"],
            tipo_produzione=art["tipo_produzione"],
            scorta_mensile=art["scorta_mensile"],
            mesi_scorta=art["mesi_scorta"],
            target_scorta=target_scorta,
            qty_disponibile_futura=qty_disp_futura,
            qty_da_produrre_scorta=qty_da_produrre_scorta,
            scorta_calcolata_at=art["scorta_calcolata_at"],
        ))

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
