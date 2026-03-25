from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_destinations import SyncDestination


class DestinationExtractor(BaseExtractor):
    """POT_DESTDIV → sync_destinations"""

    entity_type = "sync_destinations"
    model_class = SyncDestination
    pk_fields = ["source_id"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        return easy_conn.execute(text("""
            SELECT PDES_COD, CLI_COD, PDES_RAG1,
                   PDES_IND, CITTA, CAP, PROV, NAZ_COD, PDES_STD
            FROM POT_DESTDIV
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "source_id": s(row.PDES_COD),
            "customer_source_id": s(row.CLI_COD),
            "name": s(row.PDES_RAG1),
            "address": s(row.PDES_IND),
            "city": s(row.CITTA),
            "postal_code": s(row.CAP),
            "province": s(row.PROV),
            "country": s(row.NAZ_COD),
            "is_default": bool(row.PDES_STD) if row.PDES_STD is not None else None,
        }
