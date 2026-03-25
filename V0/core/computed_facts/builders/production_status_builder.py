from sqlalchemy import select, delete, func
from core.facts.builders.base import BaseBuilder, BuildResult
from core.computed_facts.models.computed_production_status import ComputedProductionStatus
from core.facts.models.fact_production import FactProduction


class ComputedProductionStatusBuilder(BaseBuilder):
    entity_type = "computed_production_status"
    model_class = ComputedProductionStatus
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(ComputedProductionStatus)).rowcount

        # Solo ordini aperti — aggregazione SQL per articolo
        rows = session.execute(
            select(
                FactProduction.article_source_id,
                func.sum(
                    FactProduction.qty_to_produce - FactProduction.qty_produced
                ).label("qty_in_production"),
                func.count().label("open_order_count"),
            )
            .where(FactProduction.is_closed == False)  # noqa: E712
            .where(FactProduction.article_source_id.is_not(None))
            .group_by(FactProduction.article_source_id)
        ).all()

        for row in rows:
            session.add(ComputedProductionStatus(
                article_source_id=row.article_source_id,
                qty_in_production=row.qty_in_production,
                open_order_count=row.open_order_count,
                built_at=now,
            ))
            result.records_built += 1

        return result
