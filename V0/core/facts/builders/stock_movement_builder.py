from sqlalchemy import select, func
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_stock_movement import FactStockMovement
from sync.models.sync_stock_movements import SyncStockMovement


class StockMovementBuilder(BaseBuilder):
    """
    Strategia APPEND_ONLY: costruisce solo i movimenti non ancora presenti in fact_*.
    MAG_REALE è append-only — i record esistenti non cambiano mai.
    """

    entity_type = "fact_stock_movements"
    model_class = FactStockMovement
    strategy = "APPEND_ONLY"

    def _get_max_built_id(self, session) -> int:
        result = session.execute(
            select(func.max(FactStockMovement.source_id))
        ).scalar()
        return int(result) if result is not None else 0

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        since_id = self._get_max_built_id(session)

        rows = session.execute(
            select(SyncStockMovement)
            .where(SyncStockMovement.source_id > since_id)
            .order_by(SyncStockMovement.source_id)
        ).scalars().all()

        for row in rows:
            session.add(FactStockMovement(
                source_id=row.source_id,
                article_source_id=self._upper(row.article_source_id),
                depot_code=self._upper(row.depot_code),
                qty_in=row.qty_in,
                qty_out=row.qty_out,
                movement_type=self._upper(row.movement_type),
                document_type=self._strip(row.document_type),
                document_number=self._strip(row.document_number),
                registered_at=row.registered_at,
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
