from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.computed_facts.models.computed_order_line import ComputedOrderLine
from core.facts.models.fact_order_line import FactOrderLine


class ComputedOrderLineBuilder(BaseBuilder):
    entity_type = "computed_order_lines"
    model_class = ComputedOrderLine
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(ComputedOrderLine)).rowcount

        rows = session.execute(select(FactOrderLine)).scalars().all()

        for row in rows:
            if row.qty_ordered is not None:
                qty_remaining = row.qty_ordered - (row.qty_shipped or 0)
                is_fully_shipped = qty_remaining <= 0
                is_open_line = qty_remaining > 0
            else:
                qty_remaining = None
                is_fully_shipped = None
                is_open_line = None

            if qty_remaining is not None and row.unit_price is not None:
                value_remaining = qty_remaining * row.unit_price
            else:
                value_remaining = None

            session.add(ComputedOrderLine(
                order_source_id=row.order_source_id,
                line_number=row.line_number,
                article_source_id=row.article_source_id,
                qty_ordered=row.qty_ordered,
                qty_shipped=row.qty_shipped,
                qty_remaining=qty_remaining,
                is_fully_shipped=is_fully_shipped,
                is_open_line=is_open_line,
                unit_price=row.unit_price,
                value_remaining=value_remaining,
                built_at=now,
            ))
            result.records_built += 1

        return result
