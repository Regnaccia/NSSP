from sqlalchemy import select, delete, func
from core.aggregates.base import BaseAggregate, RebuildResult
from core.facts.models.fact_order import FactOrder
from core.facts.models.fact_order_line import FactOrderLine
from core.computed_facts.models.computed_order_line import ComputedOrderLine
from sync.models.sync_order_headers import SyncOrderHeader
from sync.models.sync_order_lines import SyncOrderLine


class OrderAggregate(BaseAggregate):
    """
    Unita' di rebuild per un singolo ordine.

    Ricostruisce:
      - fact_orders         (WHERE source_id = aggregate_id)
      - fact_order_lines    (WHERE order_source_id = aggregate_id)
      - computed_order_lines (WHERE order_source_id = aggregate_id)
    """

    aggregate_type = "order"

    def rebuild(self, session, aggregate_id: str) -> RebuildResult:
        result = RebuildResult(aggregate_type=self.aggregate_type, aggregate_id=aggregate_id)
        now = self._now()
        order_id = int(aggregate_id)

        # --- fact_orders ---
        session.execute(delete(FactOrder).where(FactOrder.source_id == order_id))

        header = session.execute(
            select(SyncOrderHeader).where(SyncOrderHeader.source_id == order_id)
        ).scalar_one_or_none()

        if header:
            session.add(FactOrder(
                source_id=header.source_id,
                order_number=self._strip(header.order_number),
                customer_source_id=self._upper(header.customer_source_id),
                destination_source_id=self._upper(header.destination_source_id),
                order_date=header.order_date,
                expected_delivery_date=header.expected_delivery_date,
                customer_order_ref=self._strip(header.customer_order_ref),
                delivery_method=self._upper(header.delivery_method),
                notes=self._strip(header.notes),
                built_at=now,
                sync_run_id=header.sync_run_id,
            ))
            result.records_rebuilt += 1

        # --- fact_order_lines ---
        session.execute(delete(FactOrderLine).where(FactOrderLine.order_source_id == order_id))

        lines = session.execute(
            select(SyncOrderLine).where(SyncOrderLine.order_source_id == order_id)
        ).scalars().all()

        for row in lines:
            session.add(FactOrderLine(
                order_source_id=row.order_source_id,
                line_number=row.line_number,
                article_source_id=self._upper(row.article_source_id),
                article_description=self._strip(row.article_description),
                qty_ordered=row.qty_ordered,
                qty_shipped=row.qty_shipped,
                qty_packed=row.qty_packed,
                customer_line_ref=self._strip(row.customer_line_ref),
                unit_price=row.unit_price,
                built_at=now,
                sync_run_id=row.sync_run_id,
            ))
            result.records_rebuilt += 1

        # flush per rendere visibili i fact_order_lines appena inseriti
        session.flush()

        # --- computed_order_lines ---
        session.execute(delete(ComputedOrderLine).where(ComputedOrderLine.order_source_id == order_id))

        fact_lines = session.execute(
            select(FactOrderLine).where(FactOrderLine.order_source_id == order_id)
        ).scalars().all()

        for row in fact_lines:
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
            result.records_rebuilt += 1

        return result
