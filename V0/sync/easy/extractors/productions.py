from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_productions import SyncProduction


class ProductionExtractor(BaseExtractor):
    """DPRE_PROD → sync_productions"""

    entity_type = "sync_productions"
    model_class = SyncProduction
    pk_fields = ["source_id"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        return easy_conn.execute(text("""
            SELECT ID_DETTAGLIO, ART_COD, CLI_COD, DOC_NUM,
                   DOC_QTOR, QTA_DAPR, DOC_QTEV, QTA_ORAPR,
                   DOC_EVAS, NUM_ORDINE, RIGA_ORDINE, DATA_PROD
            FROM DPRE_PROD
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "source_id": int(row.ID_DETTAGLIO),
            "article_source_id": s(row.ART_COD),
            "customer_source_id": s(row.CLI_COD),
            "production_order": s(row.DOC_NUM),
            "qty_total": row.DOC_QTOR,
            "qty_to_produce": row.QTA_DAPR,
            "qty_produced": row.DOC_QTEV,
            "qty_in_progress": row.QTA_ORAPR,
            "is_closed": bool(row.DOC_EVAS) if row.DOC_EVAS is not None else None,
            "order_number": s(row.NUM_ORDINE),
            "order_line": int(row.RIGA_ORDINE) if row.RIGA_ORDINE is not None else None,
            "planned_date": row.DATA_PROD,
        }
