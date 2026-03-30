"""
Sync handlers: EasyJob → tabelle MRS.

Regola (DL-ARCH-003): questi handler fanno solo normalizzazione tecnica.
Nessuna business logic — solo fetch + upsert + aggiornamento sync_log.
"""
import uuid
import time
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.sync.easyjob import fetch_easyjob
from app.models.sync_log import SyncLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: sync_log
# ---------------------------------------------------------------------------

def _update_sync_log(
    session: Session,
    tabella: str,
    records_updated: int | None = None,
    duration_ms: int | None = None,
    error: str | None = None,
) -> None:
    row = session.query(SyncLog).filter_by(tabella=tabella).first()
    if row is None:
        row = SyncLog(id=str(uuid.uuid4()), tabella=tabella)
        session.add(row)

    if error:
        row.last_error = error
    else:
        row.last_sync_at = datetime.now(timezone.utc)
        row.last_error = None
        row.records_updated = records_updated
        row.sync_duration_ms = duration_ms

    session.commit()


def _s(v) -> str | None:
    """Strip stringa o ritorna None."""
    return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# sync_materie_prime — ANAART (CAT_ART1 = '0') → materie_prime
# ---------------------------------------------------------------------------

def sync_materie_prime(session: Session) -> int:
    """Sincronizza le materie prime da ANAART (CAT_ART1='0') → tabella materie_prime.
    Non tocca lunghezza_mm (campo MRS-owned).
    """
    t0 = time.monotonic()
    try:
        rows = fetch_easyjob("""
            SELECT ART_COD, ART_DES1
            FROM ANAART
            WHERE CAT_ART1 = '0'
              AND (ART_BLOC IS NULL OR ART_BLOC = 0)
        """)
        count = 0
        for row in rows:
            codice = _s(row["ART_COD"])
            if not codice:
                continue
            existing = session.execute(
                text("SELECT id FROM materie_prime WHERE codice = :c"),
                {"c": codice},
            ).fetchone()
            if existing:
                session.execute(
                    text("""
                        UPDATE materie_prime SET
                            descrizione = :des,
                            synced_at   = :ts
                        WHERE codice = :c
                    """),
                    {"des": _s(row.get("ART_DES1")), "ts": datetime.now(timezone.utc), "c": codice},
                )
            else:
                session.execute(
                    text("""
                        INSERT INTO materie_prime (id, codice, codice_upper, descrizione, synced_at)
                        VALUES (:id, :c, :cu, :des, :ts)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "c": codice,
                        "cu": codice.upper(),
                        "des": _s(row.get("ART_DES1")),
                        "ts": datetime.now(timezone.utc),
                    },
                )
            count += 1
        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "materie_prime", count, ms)
        logger.info("sync_materie_prime OK: %d record in %d ms", count, ms)
        return count
    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "materie_prime", error=str(exc))
        logger.error("sync_materie_prime ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_categorie_articolo — CATART1 → categorie_articolo
# ---------------------------------------------------------------------------

def sync_categorie_articolo(session: Session) -> int:
    """Sincronizza CATART1 → categorie_articolo.
    Non tocca il campo famiglia (MRS-owned).
    """
    t0 = time.monotonic()
    try:
        rows = fetch_easyjob("""
            SELECT CAT_ART1, CAT_DES1
            FROM CATART1
        """)
        count = 0
        now = datetime.now(timezone.utc)
        for row in rows:
            codice = _s(row.get("CAT_ART1"))
            if not codice:
                continue
            descrizione = _s(row.get("CAT_DES1"))
            existing = session.execute(
                text("SELECT codice FROM categorie_articolo WHERE codice = :c"),
                {"c": codice},
            ).fetchone()
            if existing:
                session.execute(
                    text("UPDATE categorie_articolo SET descrizione = :d, synced_at = :ts WHERE codice = :c"),
                    {"d": descrizione, "ts": now, "c": codice},
                )
            else:
                session.execute(
                    text("""
                        INSERT INTO categorie_articolo (codice, descrizione, synced_at)
                        VALUES (:c, :d, :ts)
                    """),
                    {"c": codice, "d": descrizione, "ts": now},
                )
            count += 1
        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "categorie_articolo", count, ms)
        logger.info("sync_categorie_articolo OK: %d record in %d ms", count, ms)
        return count
    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "categorie_articolo", error=str(exc))
        logger.error("sync_categorie_articolo ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_articoli — ANAART → articoli
# ---------------------------------------------------------------------------

def _parse_contenitori(val) -> float:
    """
    Parsa ART_CONTEN da ANAART: può essere int, float, o stringa tipo '3/2'.
    Ritorna 0.0 se non interpretabile.
    """
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    if '/' in s:
        try:
            a, b = s.split('/', 1)
            return float(a) / float(b)
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _calcola_capienza(contenitori: float, peso_kg) -> int | None:
    """
    capienza = 75_000g × contenitori / peso_articolo_g
    peso_kg: peso articolo in kg da ANAART.ART_KG.
    Ritorna None se dati mancanti o nulli.
    """
    MAX_PESO_CONTENITORE_G = 75_000
    if not contenitori:
        return None
    try:
        p = float(peso_kg)
    except (TypeError, ValueError):
        return None
    if p <= 0:
        return None
    return max(1, round(MAX_PESO_CONTENITORE_G * contenitori / p))


def sync_articoli(session: Session) -> int:
    """Sincronizza ANAART → tabella articoli. Ritorna numero record aggiornati."""
    t0 = time.monotonic()
    try:
        rows = fetch_easyjob("""
            SELECT ART_COD, ART_DES1, CAT_ART1, ART_CONTEN, ART_KG,
                   REGN_QT_OCCORR, REGN_QT_SCARTO, MAT_COD,
                   ART_MISURA, COD_IMM
            FROM ANAART
            WHERE ART_BLOC IS NULL OR ART_BLOC = 0
        """)

        # Pre-carica mappa codice → id per materie_prime
        mp_rows = session.execute(text("SELECT codice, id FROM materie_prime")).fetchall()
        mp_map: dict[str, str] = {r[0]: r[1] for r in mp_rows}

        count = 0
        for row in rows:
            codice = _s(row["ART_COD"])
            if not codice:
                continue

            contenitori = _parse_contenitori(row.get("ART_CONTEN"))
            capienza_calc = _calcola_capienza(contenitori, row.get("ART_KG"))

            # mm_materiale = occorrenza + scarto (da ANAART)
            def _to_int(v) -> int | None:
                try:
                    return int(round(float(v))) if v is not None else None
                except (TypeError, ValueError):
                    return None
            mm_occ = _to_int(row.get("REGN_QT_OCCORR"))
            mm_sca = _to_int(row.get("REGN_QT_SCARTO"))
            mm_calc = (mm_occ + mm_sca) if (mm_occ is not None and mm_sca is not None) else None

            # materia_prima_id: sync-owned, sempre aggiornato da MAT_COD
            mat_cod = _s(row.get("MAT_COD"))
            materia_prima_id = mp_map.get(mat_cod) if mat_cod else None

            misura   = _s(row.get("ART_MISURA"))
            immagine = _s(row.get("COD_IMM"))

            existing = session.execute(
                text("SELECT id, capienza, mm_materiale FROM articoli WHERE codice = :c"),
                {"c": codice},
            ).fetchone()

            if existing:
                # capienza e mm_materiale: aggiorna solo se non sono mai stati impostati (NULL)
                # tutti gli altri campi: sync-owned, sempre aggiornati
                updates = {
                    "des":    _s(row.get("ART_DES1")),
                    "cat":    _s(row.get("CAT_ART1")),
                    "mp_id":  materia_prima_id,
                    "misura": misura,
                    "imm":    immagine,
                    "ts":     datetime.now(timezone.utc),
                    "c":      codice,
                }
                set_cap = existing[1] is None and capienza_calc is not None
                set_mm  = existing[2] is None and mm_calc is not None
                if set_cap:
                    updates["cap"] = capienza_calc
                if set_mm:
                    updates["mm"] = mm_calc

                extra_sets = ""
                if set_cap:
                    extra_sets += ", capienza = :cap"
                if set_mm:
                    extra_sets += ", mm_materiale = :mm"

                session.execute(
                    text(f"""
                        UPDATE articoli SET
                            descrizione      = :des,
                            categoria        = :cat,
                            materia_prima_id = :mp_id,
                            misura           = :misura,
                            immagine         = :imm,
                            synced_at        = :ts
                            {extra_sets}
                        WHERE codice = :c
                    """),
                    updates,
                )
            else:
                session.execute(
                    text("""
                        INSERT INTO articoli
                            (id, codice, codice_upper, descrizione, categoria,
                             capienza, mm_materiale, materia_prima_id,
                             misura, immagine, synced_at)
                        VALUES
                            (:id, :c, :cu, :des, :cat, :cap, :mm, :mp_id,
                             :misura, :imm, :ts)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "c": codice,
                        "cu": codice.upper(),
                        "des": _s(row.get("ART_DES1")),
                        "cat": _s(row.get("CAT_ART1")),
                        "cap": capienza_calc,
                        "mm": mm_calc,
                        "mp_id": materia_prima_id,
                        "misura": misura,
                        "imm": immagine,
                        "ts": datetime.now(timezone.utc),
                    },
                )
            count += 1

        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "articoli", count, ms)
        logger.info("sync_articoli OK: %d record in %d ms", count, ms)
        return count

    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "articoli", error=str(exc))
        logger.error("sync_articoli ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_clienti — ANACLI → clienti
# ---------------------------------------------------------------------------

def sync_clienti(session: Session) -> int:
    """Sincronizza ANACLI → tabella clienti. Ritorna numero record aggiornati."""
    t0 = time.monotonic()
    try:
        rows = fetch_easyjob("""
            SELECT CLI_COD, CLI_RAG1, CLI_RAG2, CLI_EMAIL
            FROM ANACLI
        """)

        count = 0
        for row in rows:
            codice_ej = _s(row["CLI_COD"])
            if not codice_ej:
                continue

            rag1 = _s(row.get("CLI_RAG1")) or ""
            rag2 = _s(row.get("CLI_RAG2")) or ""
            ragione_sociale = " ".join(p for p in [rag1, rag2] if p) or codice_ej

            existing = session.execute(
                text("SELECT id FROM clienti WHERE codice_easyjob = :c"),
                {"c": codice_ej},
            ).fetchone()

            if existing:
                # nickname NON toccato — è MRS-owned (DL-ARCH-017)
                session.execute(
                    text("""
                        UPDATE clienti SET
                            ragione_sociale = :rs,
                            email           = :em,
                            synced_at       = :ts
                        WHERE codice_easyjob = :c
                    """),
                    {
                        "rs": ragione_sociale,
                        "em": _s(row.get("CLI_EMAIL")),
                        "ts": datetime.now(timezone.utc),
                        "c": codice_ej,
                    },
                )
            else:
                session.execute(
                    text("""
                        INSERT INTO clienti
                            (id, codice_easyjob, ragione_sociale, email, synced_at)
                        VALUES
                            (:id, :c, :rs, :em, :ts)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "c": codice_ej,
                        "rs": ragione_sociale,
                        "em": _s(row.get("CLI_EMAIL")),
                        "ts": datetime.now(timezone.utc),
                    },
                )
            count += 1

        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "clienti", count, ms)
        logger.info("sync_clienti OK: %d record in %d ms", count, ms)
        return count

    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "clienti", error=str(exc))
        logger.error("sync_clienti ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_ordini_e_righe — V_TORDCLI → ordini + righe_ordine
# ---------------------------------------------------------------------------

def _build_qty_in_produzione_map() -> dict[str, int]:
    """
    Calcola qty_in_produzione per articolo da DPRE_PROD (LDP aperti).
    Ritorna dict {art_cod_upper: qty_in_produzione}.
    Formula: SUM(DOC_QTOR - DOC_QTEV) per ART_COD dove DOC_QTOR > DOC_QTEV.
    """
    try:
        rows = fetch_easyjob("""
            SELECT ART_COD, SUM(DOC_QTOR - DOC_QTEV) AS qty_ip
            FROM DPRE_PROD
            WHERE DOC_QTOR > DOC_QTEV
            GROUP BY ART_COD
        """)
        return {
            (_s(r["ART_COD"]) or "").upper(): int(r["qty_ip"] or 0)
            for r in rows
            if r.get("ART_COD")
        }
    except Exception as exc:
        logger.warning("Impossibile leggere DPRE_PROD: %s — qty_in_produzione sarà 0", exc)
        return {}


def sync_ordini_e_righe(session: Session) -> int:
    """
    Sincronizza V_TORDCLI → ordini + righe_ordine.
    - Ordini aperti (DOC_QTEV < DOC_QTOR o ordini senza righe evase)
    - Righe di continuazione (COLL_RIGA_PREC=1) scartate (DL-ARCH-004)
    - qty_disponibile = DOC_QTAP (appartato da EasyJob)
    - qty_in_produzione calcolato da DPRE_PROD per articolo
    Ritorna numero righe_ordine aggiornate.
    """
    t0 = time.monotonic()
    try:
        # --- Fetch raw rows ---
        raw_rows = fetch_easyjob("""
            SELECT DISTINCT
                ID_TESTATA, DOC_NUM, CLI_COD, DOC_DATA, DOC_PREV, DOC_NOTE,
                NUM_PROGR, ART_COD, DOC_QTOR, DOC_QTEV, DOC_QTAP, COLL_RIGA_PREC
            FROM V_TORDCLI
            ORDER BY ID_TESTATA, NUM_PROGR
        """)

        # --- Precalcola qty_in_produzione per articolo ---
        qty_ip_map = _build_qty_in_produzione_map()

        # --- Raggruppa: header + righe reali (senza COLL_RIGA_PREC) ---
        headers: dict[int, dict] = {}
        lines_by_testata: dict[int, list[dict]] = {}

        for row in raw_rows:
            tid = int(row["ID_TESTATA"])
            if tid not in headers:
                headers[tid] = row
            if row.get("COLL_RIGA_PREC"):
                continue  # riga descrizione collaterale — scartata (DL-ARCH-004)
            if row.get("ART_COD"):
                lines_by_testata.setdefault(tid, []).append(row)

        # --- Lookup: articolo_id per codice ---
        def get_articolo_id(art_cod: str) -> str | None:
            r = session.execute(
                text("SELECT id FROM articoli WHERE codice_upper = :c"),
                {"c": art_cod.upper()},
            ).fetchone()
            return r[0] if r else None

        # --- Lookup: cliente_id per codice_easyjob ---
        def get_cliente_id(cli_cod: str) -> str | None:
            r = session.execute(
                text("SELECT id FROM clienti WHERE codice_easyjob = :c"),
                {"c": cli_cod},
            ).fetchone()
            return r[0] if r else None

        riga_count = 0

        for tid, hdr in headers.items():
            doc_num = _s(hdr.get("DOC_NUM"))
            cli_cod = _s(hdr.get("CLI_COD"))
            if not doc_num or not cli_cod:
                continue

            cliente_id = get_cliente_id(cli_cod)
            if cliente_id is None:
                logger.warning("Cliente %s non trovato per ordine %s — skip", cli_cod, doc_num)
                continue

            doc_data = hdr.get("DOC_DATA")
            if hasattr(doc_data, "date"):
                doc_data = doc_data.date()

            doc_prev = hdr.get("DOC_PREV")
            if hasattr(doc_prev, "date"):
                doc_prev = doc_prev.date()

            # --- Upsert ordine ---
            existing_ordine = session.execute(
                text("SELECT id FROM ordini WHERE numero_ordine = :n"),
                {"n": doc_num},
            ).fetchone()

            if existing_ordine:
                ordine_id = existing_ordine[0]
                session.execute(
                    text("""
                        UPDATE ordini SET
                            cliente_id    = :cid,
                            data_ordine   = :do,
                            data_consegna = :dc,
                            note          = :note,
                            synced_at     = :ts
                        WHERE id = :oid
                    """),
                    {
                        "cid": cliente_id,
                        "do": doc_data,
                        "dc": doc_prev,
                        "note": _s(hdr.get("DOC_NOTE")),
                        "ts": datetime.now(timezone.utc),
                        "oid": ordine_id,
                    },
                )
            else:
                ordine_id = str(uuid.uuid4())
                session.execute(
                    text("""
                        INSERT INTO ordini
                            (id, numero_ordine, cliente_id, data_ordine, data_consegna, note, synced_at)
                        VALUES
                            (:id, :n, :cid, :do, :dc, :note, :ts)
                    """),
                    {
                        "id": ordine_id,
                        "n": doc_num,
                        "cid": cliente_id,
                        "do": doc_data,
                        "dc": doc_prev,
                        "note": _s(hdr.get("DOC_NOTE")),
                        "ts": datetime.now(timezone.utc),
                    },
                )

            # --- Righe ordine ---
            for line in lines_by_testata.get(tid, []):
                art_cod = _s(line.get("ART_COD"))
                num_progr = str(int(line["NUM_PROGR"]))
                if not art_cod:
                    continue

                articolo_id = get_articolo_id(art_cod)
                if articolo_id is None:
                    logger.warning("Articolo %s non trovato per ordine %s — skip", art_cod, doc_num)
                    continue

                qty_ord = int(line.get("DOC_QTOR") or 0)
                qty_disp = int(line.get("DOC_QTAP") or 0)  # appartato da EasyJob (0 se non usato)
                qty_cons = int(line.get("DOC_QTEV") or 0)
                qty_ip = qty_ip_map.get(art_cod.upper(), 0)
                stato_riga = "spedito" if qty_cons >= qty_ord and qty_ord > 0 else "aperto"

                existing_riga = session.execute(
                    text("""
                        SELECT id FROM righe_ordine
                        WHERE ordine_id = :oid AND riga_ej_id = :rid
                    """),
                    {"oid": ordine_id, "rid": num_progr},
                ).fetchone()

                if existing_riga:
                    session.execute(
                        text("""
                            UPDATE righe_ordine SET
                                articolo_id       = :aid,
                                qty_ordinata      = :qo,
                                qty_disponibile   = :qd,
                                qty_in_produzione = :qi,
                                qty_consegnata    = :qc,
                                stato             = :stato,
                                synced_at         = :ts
                            WHERE id = :rid
                        """),
                        {
                            "aid": articolo_id,
                            "qo": qty_ord,
                            "qd": qty_disp,
                            "qi": qty_ip,
                            "qc": qty_cons,
                            "stato": stato_riga,
                            "ts": datetime.now(timezone.utc),
                            "rid": existing_riga[0],
                        },
                    )
                else:
                    session.execute(
                        text("""
                            INSERT INTO righe_ordine
                                (id, ordine_id, articolo_id, riga_ej_id,
                                 qty_ordinata, qty_disponibile, qty_in_produzione,
                                 qty_consegnata, stato, synced_at)
                            VALUES
                                (:id, :oid, :aid, :rjid,
                                 :qo, :qd, :qi, :qc, :stato, :ts)
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "oid": ordine_id,
                            "aid": articolo_id,
                            "rjid": num_progr,
                            "qo": qty_ord,
                            "qd": qty_disp,
                            "qi": qty_ip,
                            "qc": qty_cons,
                            "stato": stato_riga,
                            "ts": datetime.now(timezone.utc),
                        },
                    )
                riga_count += 1

        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "ordini", riga_count, ms)
        _update_sync_log(session, "righe_ordine", riga_count, ms)
        logger.info("sync_ordini_e_righe OK: %d righe in %d ms", riga_count, ms)
        return riga_count

    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "ordini", error=str(exc))
        _update_sync_log(session, "righe_ordine", error=str(exc))
        logger.error("sync_ordini_e_righe ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_giacenze — MAG_REALE → articoli.giacenza_attuale
# ---------------------------------------------------------------------------

def sync_giacenze(session: Session) -> int:
    """
    Legge giacenza attuale da MAG_REALE (SUM(QTA_CAR - QTA_SCA) per articolo)
    e aggiorna articoli.giacenza_attuale.
    Ritorna numero articoli aggiornati.
    """
    t0 = time.monotonic()
    try:
        rows = fetch_easyjob("""
            SELECT ART_COD, SUM(QTA_CAR - QTA_SCA) AS giacenza
            FROM MAG_REALE
            GROUP BY ART_COD
            HAVING SUM(QTA_CAR - QTA_SCA) > 0
        """)

        count = 0
        now = datetime.now(timezone.utc)

        for row in rows:
            art_cod = (_s(row["ART_COD"]) or "").upper()
            if not art_cod:
                continue
            giacenza = int(row["giacenza"] or 0)

            updated = session.execute(
                text("""
                    UPDATE articoli
                    SET giacenza_attuale = :g, synced_at = :ts
                    WHERE codice_upper = :c
                """),
                {"g": giacenza, "ts": now, "c": art_cod},
            ).rowcount
            if updated:
                count += 1

        # Azzera articoli non presenti in MAG_REALE (nessuna giacenza)
        art_cods_with_stock = {(_s(r["ART_COD"]) or "").upper() for r in rows if r.get("ART_COD")}
        if art_cods_with_stock:
            session.execute(
                text("""
                    UPDATE articoli SET giacenza_attuale = 0
                    WHERE codice_upper NOT IN :cods
                      AND giacenza_attuale != 0
                """),
                {"cods": tuple(art_cods_with_stock)},
            )

        session.commit()
        ms = int((time.monotonic() - t0) * 1000)
        _update_sync_log(session, "giacenze", count, ms)
        logger.info("sync_giacenze OK: %d articoli in %d ms", count, ms)
        return count

    except Exception as exc:
        session.rollback()
        _update_sync_log(session, "giacenze", error=str(exc))
        logger.error("sync_giacenze ERRORE: %s", exc)
        raise


# ---------------------------------------------------------------------------
# sync_all — esegue tutti i sync nell'ordine corretto
# ---------------------------------------------------------------------------

HANDLER_MAP: dict[str, callable] = {
    "categorie_articolo": sync_categorie_articolo,
    "materie_prime": sync_materie_prime,
    "articoli": sync_articoli,
    "clienti": sync_clienti,
    "ordini": sync_ordini_e_righe,
    "righe_ordine": sync_ordini_e_righe,  # stesso handler, idempotente
    "giacenze": sync_giacenze,
}


def sync_tabella(session: Session, tabella: str) -> int:
    """Esegue il sync di una singola tabella. Usato da /api/sync/force/{tabella}."""
    handler = HANDLER_MAP.get(tabella)
    if handler is None:
        raise ValueError(f"Tabella sync sconosciuta: {tabella}")
    return handler(session)


def sync_all(session: Session) -> dict[str, int]:
    """
    Esegue tutti i sync nell'ordine dipendenza-safe:
    articoli → clienti → ordini+righe → giacenze.
    Ritorna dict {tabella: records_updated}.
    """
    results = {}
    results["categorie_articolo"] = sync_categorie_articolo(session)
    results["materie_prime"] = sync_materie_prime(session)
    results["articoli"] = sync_articoli(session)
    results["clienti"] = sync_clienti(session)
    results["ordini_e_righe"] = sync_ordini_e_righe(session)
    results["giacenze"] = sync_giacenze(session)
    return results
