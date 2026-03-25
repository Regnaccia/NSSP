from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_production import FactProduction
from sync.models.sync_productions import SyncProduction


class ProductionBuilder(BaseBuilder):
    entity_type = "fact_productions"
    model_class = FactProduction
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        session.execute(delete(FactProduction))

        rows = session.execute(select(SyncProduction)).scalars().all()

        for row in rows:
            session.add(FactProduction(
                source_id=row.source_id,
                production_order=self._strip(row.production_order),
                article_source_id=self._upper(row.article_source_id),
                customer_source_id=self._upper(row.customer_source_id),
                qty_total=row.qty_total,
                qty_to_produce=row.qty_to_produce,
                qty_produced=row.qty_produced,
                qty_in_progress=row.qty_in_progress,
                is_closed=row.is_closed,
                order_number=self._strip(row.order_number),
                order_line=row.order_line,
                planned_date=row.planned_date,
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
