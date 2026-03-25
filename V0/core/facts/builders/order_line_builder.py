from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_order_line import FactOrderLine
from sync.models.sync_order_lines import SyncOrderLine


class OrderLineBuilder(BaseBuilder):
    entity_type = "fact_order_lines"
    model_class = FactOrderLine
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        session.execute(delete(FactOrderLine))

        rows = session.execute(select(SyncOrderLine)).scalars().all()

        for row in rows:
            session.add(FactOrderLine(
                order_source_id=row.order_source_id,
                line_number=row.line_number,
                article_source_id=self._upper(row.article_source_id),
                article_description=self._strip(row.article_description),
                qty_ordered=row.qty_ordered,
                qty_shipped=row.qty_shipped,
                qty_packed=row.qty_packed,
                customer_line_ref=self._strip(row.customer_line_ref),
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
