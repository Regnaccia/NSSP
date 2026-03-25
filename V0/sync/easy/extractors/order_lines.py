from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_order_lines import SyncOrderLine


class OrderLineExtractor(BaseExtractor):
    """
    V_TORDCLI → sync_order_lines.

    Gestisce COLL_RIGA_PREC in preprocess_rows (DL-ARCH-004):
    le righe di continuazione non vengono salvate come entità indipendenti,
    ma la loro ART_DESCR viene concatenata alla descrizione della riga precedente.
    """

    entity_type = "sync_order_lines"
    model_class = SyncOrderLine
    pk_fields = ["order_source_id", "line_number"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        return easy_conn.execute(text("""
            SELECT ID_TESTATA, NUM_PROGR, ART_COD, ART_DESCR,
                   DOC_QTOR, DOC_QTEV, DOC_QTAP, RIF_CLIENTE, COLL_RIGA_PREC
            FROM V_TORDCLI
            ORDER BY ID_TESTATA, NUM_PROGR
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "order_source_id": int(row.ID_TESTATA),
            "line_number": int(row.NUM_PROGR),
            "article_source_id": s(row.ART_COD),
            "article_description": s(row.ART_DESCR),
            "qty_ordered": row.DOC_QTOR,
            "qty_shipped": row.DOC_QTEV,
            "qty_packed": row.DOC_QTAP,
            "customer_line_ref": s(row.RIF_CLIENTE),
        }

    def preprocess_rows(self, raw_rows: list) -> list[dict]:
        """
        Processa COLL_RIGA_PREC: le righe di continuazione estendono
        la descrizione della riga reale precedente e non vengono salvate.
        """
        processed = []
        current: dict | None = None

        for row in raw_rows:
            is_continuation = row.COLL_RIGA_PREC

            if is_continuation:
                if current is not None and row.ART_DESCR:
                    extra = row.ART_DESCR.strip()
                    if extra:
                        current["article_description"] = (
                            (current["article_description"] or "") + " " + extra
                        ).strip()
            else:
                if current is not None:
                    processed.append(current)
                current = self.map_row(row)

        if current is not None:
            processed.append(current)

        return processed
