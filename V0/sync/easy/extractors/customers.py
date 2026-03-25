from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_customers import SyncCustomer


class CustomerExtractor(BaseExtractor):
    """ANACLI → sync_customers"""

    entity_type = "sync_customers"
    model_class = SyncCustomer
    pk_fields = ["source_id"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        return easy_conn.execute(text("""
            SELECT CLI_COD, CLI_RAG1, CLI_RAG2, CLI_IND,
                   NAZ_COD, CITTA, CAP, PROV,
                   CLI_PIVA, CLI_EMAIL, CLI_DTMO
            FROM ANACLI
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        name_parts = [s(row.CLI_RAG1), s(row.CLI_RAG2)]
        name = " ".join(p for p in name_parts if p) or None

        return {
            "source_id": s(row.CLI_COD),
            "name": name,
            "address": s(row.CLI_IND),
            "city": s(row.CITTA),
            "postal_code": s(row.CAP),
            "province": s(row.PROV),
            "country": s(row.NAZ_COD),
            "vat_number": s(row.CLI_PIVA),
            "email": s(row.CLI_EMAIL),
            "source_updated_at": row.CLI_DTMO,
        }
