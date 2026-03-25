from sqlalchemy import select, delete
from core.facts.builders.base import BaseBuilder, BuildResult
from core.facts.models.fact_order import FactOrder
from sync.models.sync_order_headers import SyncOrderHeader


class OrderBuilder(BaseBuilder):
    entity_type = "fact_orders"
    model_class = FactOrder
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        session.execute(delete(FactOrder))

        rows = session.execute(select(SyncOrderHeader)).scalars().all()

        for row in rows:
            session.add(FactOrder(
                source_id=row.source_id,
                order_number=self._strip(row.order_number),
                customer_source_id=self._upper(row.customer_source_id),
                destination_source_id=self._upper(row.destination_source_id),
                order_date=row.order_date,
                expected_delivery_date=row.expected_delivery_date,
                customer_order_ref=self._strip(row.customer_order_ref),
                delivery_method=self._upper(row.delivery_method),
                notes=self._strip(row.notes),
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_built += 1

        return result
