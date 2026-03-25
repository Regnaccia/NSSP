from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_order_headers import SyncOrderHeader


class OrderHeaderExtractor(BaseExtractor):
    """V_TORDCLI (deduplicata per ID_TESTATA) → sync_order_headers"""

    entity_type = "sync_order_headers"
    model_class = SyncOrderHeader
    pk_fields = ["source_id"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        # DISTINCT su ID_TESTATA: un record per ordine, i campi header sono identici su tutte le righe
        return easy_conn.execute(text("""
            SELECT DISTINCT
                ID_TESTATA, DOC_NUM, CLI_COD, PDES_COD,
                DOC_DATA, DOC_PREV, N_ORDCLI, TMEZ_COD, DOC_NOTE
            FROM V_TORDCLI
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "source_id": int(row.ID_TESTATA),
            "order_number": s(row.DOC_NUM),
            "customer_source_id": s(row.CLI_COD),
            "destination_source_id": s(row.PDES_COD),
            "order_date": row.DOC_DATA,
            "expected_delivery_date": row.DOC_PREV,
            "customer_order_ref": s(row.N_ORDCLI),
            "delivery_method": s(row.TMEZ_COD),
            "notes": s(row.DOC_NOTE),
        }
