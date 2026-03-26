"""
FifoAllocationPolicy — allocazione FIFO dello stock sulle righe ordine aperte.

Dato un article_id:
  1. Legge total_stock da computed_article_demand
  2. Legge le righe aperte (qty_remaining > 0) da computed_order_lines,
     ordinate per order_date ASC, poi order_source_id ASC (FIFO deterministico)
  3. Distribuisce lo stock residuo riga per riga:
       qty_coverable_now = min(qty_remaining, max(stock_residuo, 0))
       coverable_now     = qty_coverable_now >= qty_remaining
  4. Aggiorna i campi su computed_order_lines via UPDATE
"""

from decimal import Decimal
from sqlalchemy import select, update

from core.policies.base import BasePolicy, PolicyResult
from core.computed_facts.models.computed_article_demand import ComputedArticleDemand
from core.computed_facts.models.computed_order_line import ComputedOrderLine
from core.facts.models.fact_order import FactOrder


class FifoAllocationPolicy(BasePolicy):

    policy_type = "fifo_allocation"

    def apply(self, session, aggregate_id: str) -> PolicyResult:
        result = PolicyResult(policy_type=self.policy_type, aggregate_id=aggregate_id)
        article_id = aggregate_id.strip().upper()

        # Legge lo stock totale disponibile
        demand_row = session.execute(
            select(ComputedArticleDemand.total_stock)
            .where(ComputedArticleDemand.article_source_id == article_id)
        ).scalar_one_or_none()

        total_stock = demand_row if demand_row is not None else Decimal(0)
        stock_residuo = max(total_stock, Decimal(0))

        # Legge le righe aperte ordinate FIFO (order_date ASC, order_source_id ASC)
        open_lines = session.execute(
            select(
                ComputedOrderLine.computed_id,
                ComputedOrderLine.order_source_id,
                ComputedOrderLine.qty_remaining,
            )
            .join(
                FactOrder,
                FactOrder.source_id == ComputedOrderLine.order_source_id,
            )
            .where(ComputedOrderLine.article_source_id == article_id)
            .where(ComputedOrderLine.qty_remaining > 0)
            .order_by(FactOrder.order_date.asc(), ComputedOrderLine.order_source_id.asc())
        ).all()

        for row in open_lines:
            qty_remaining = row.qty_remaining or Decimal(0)
            qty_coverable = min(qty_remaining, stock_residuo)
            coverable_now = qty_coverable >= qty_remaining
            stock_residuo -= qty_coverable

            session.execute(
                update(ComputedOrderLine)
                .where(ComputedOrderLine.computed_id == row.computed_id)
                .values(
                    qty_coverable_now=qty_coverable,
                    coverable_now=coverable_now,
                )
            )
            result.records_updated += 1

        return result
