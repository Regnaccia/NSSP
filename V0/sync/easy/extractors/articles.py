from sqlalchemy import text
from sync.easy.extractors.base import BaseExtractor
from sync.models.sync_articles import SyncArticle


class ArticleExtractor(BaseExtractor):
    """ANAART → sync_articles"""

    entity_type = "sync_articles"
    model_class = SyncArticle
    pk_fields = ["source_id"]
    detect_deletes = True

    def fetch_rows(self, easy_conn):
        return easy_conn.execute(text("""
            SELECT ART_COD, ART_DES1, ART_DES2, UM_COD,
                   ART_BLOC, MAT_COD, CAT_ART6, ART_DTMO
            FROM ANAART
        """)).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "source_id": s(row.ART_COD),
            "description": s(row.ART_DES1),
            "description_2": s(row.ART_DES2),
            "unit_of_measure": s(row.UM_COD),
            "is_blocked": bool(row.ART_BLOC) if row.ART_BLOC is not None else None,
            "material_code": s(row.MAT_COD),
            "category": s(row.CAT_ART6),
            "source_updated_at": row.ART_DTMO,
        }
