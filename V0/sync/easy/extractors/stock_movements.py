from datetime import datetime, timezone

from sqlalchemy import text, select, func
from sqlalchemy.dialects.postgresql import insert

from sync.easy.extractors.base import BaseExtractor, ExtractorResult
from sync.models.sync_stock_movements import SyncStockMovement


class StockMovementExtractor(BaseExtractor):
    """
    MAG_REALE → sync_stock_movements.

    MAG_REALE è un log append-only: i movimenti non vengono mai cancellati.
    La sync è incrementale per ID: vengono importati solo i record con
    ID_MAGREALE > max(source_id) già presente in sync.

    detect_deletes = False per design.
    """

    entity_type = "sync_stock_movements"
    model_class = SyncStockMovement
    pk_fields = ["source_id"]
    detect_deletes = False

    def _get_max_synced_id(self, mrs_session) -> int:
        result = mrs_session.execute(
            select(func.max(SyncStockMovement.source_id))
        ).scalar()
        return int(result) if result is not None else 0

    def fetch_rows(self, easy_conn, since_id: int = 0):
        return easy_conn.execute(text("""
            SELECT ID_MAGREALE, ART_COD, DEP_COD,
                   QTA_CAR, QTA_SCA, FLG_CARSCA,
                   TIPO_DOC, DOC_NUM, MAG_DTREG
            FROM MAG_REALE
            WHERE ID_MAGREALE > :since_id
            ORDER BY ID_MAGREALE
        """), {"since_id": since_id}).fetchall()

    def map_row(self, row) -> dict:
        def s(v):
            return v.strip() if isinstance(v, str) else v

        return {
            "source_id": int(row.ID_MAGREALE),
            "article_source_id": s(row.ART_COD),
            "depot_code": s(row.DEP_COD),
            "qty_in": row.QTA_CAR,
            "qty_out": row.QTA_SCA,
            "movement_type": s(row.FLG_CARSCA),
            "document_type": s(row.TIPO_DOC),
            "document_number": s(row.DOC_NUM),
            "registered_at": row.MAG_DTREG,
        }

    def run(self, mrs_session, easy_engine, sync_run_id: int) -> ExtractorResult:
        result = ExtractorResult(entity_type=self.entity_type)
        now = datetime.now(timezone.utc)

        since_id = self._get_max_synced_id(mrs_session)
        with easy_engine.connect() as easy_conn:
            raw_rows = self.fetch_rows(easy_conn, since_id=since_id)
        result.records_read = len(raw_rows)

        for row in raw_rows:
            mapped = self.map_row(row)
            mapped["row_hash"] = self._compute_hash(mapped)
            mapped["synced_at"] = now
            mapped["sync_run_id"] = sync_run_id

            stmt = insert(self.model_class).values(**mapped)
            stmt = stmt.on_conflict_do_update(
                index_elements=self.pk_fields,
                set_={k: v for k, v in mapped.items() if k not in self.pk_fields},
            )
            mrs_session.execute(stmt)
            result.records_inserted += 1
            self._record_change(mrs_session, sync_run_id, str(mapped["source_id"]), "INSERTED", now)

        return result
