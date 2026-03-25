from sqlalchemy import select, delete, func
from core.facts.builders.base import BaseBuilder, BuildResult
from core.computed_facts.models.computed_stock_balance import ComputedStockBalance
from core.facts.models.fact_stock_movement import FactStockMovement


class ComputedStockBalanceBuilder(BaseBuilder):
    entity_type = "computed_stock_balances"
    model_class = ComputedStockBalance
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(ComputedStockBalance)).rowcount

        # Aggregazione SQL — nessun loop sui 337k movimenti
        rows = session.execute(
            select(
                FactStockMovement.article_source_id,
                FactStockMovement.depot_code,
                func.sum(FactStockMovement.qty_in).label("qty_in_total"),
                func.sum(FactStockMovement.qty_out).label("qty_out_total"),
                func.count().label("movement_count"),
            )
            .group_by(
                FactStockMovement.article_source_id,
                FactStockMovement.depot_code,
            )
        ).all()

        for row in rows:
            qty_in = row.qty_in_total or 0
            qty_out = row.qty_out_total or 0

            session.add(ComputedStockBalance(
                article_source_id=row.article_source_id,
                depot_code=row.depot_code,
                qty_in_total=row.qty_in_total,
                qty_out_total=row.qty_out_total,
                stock_balance=qty_in - qty_out,
                movement_count=row.movement_count,
                built_at=now,
            ))
            result.records_built += 1

        return result
