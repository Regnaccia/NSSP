from sqlalchemy import select, delete, func
from core.aggregates.base import BaseAggregate, RebuildResult
from core.facts.models.fact_article import FactArticle
from core.computed_facts.models.computed_stock_balance import ComputedStockBalance
from core.computed_facts.models.computed_production_status import ComputedProductionStatus
from core.computed_facts.models.computed_article_demand import ComputedArticleDemand
from core.facts.models.fact_stock_movement import FactStockMovement
from core.facts.models.fact_production import FactProduction
from core.facts.models.fact_order_line import FactOrderLine
from sync.models.sync_articles import SyncArticle


class ArticleSupplyDemandAggregate(BaseAggregate):
    """
    Unita' di rebuild per un singolo articolo.

    Ricostruisce:
      - fact_articles              (WHERE source_id = aggregate_id)
      - computed_stock_balances    (WHERE article_source_id = aggregate_id)
      - computed_production_status (WHERE article_source_id = aggregate_id)
      - computed_article_demand    (WHERE article_source_id = aggregate_id)
    """

    aggregate_type = "article_supply_demand"

    def rebuild(self, session, aggregate_id: str) -> RebuildResult:
        result = RebuildResult(aggregate_type=self.aggregate_type, aggregate_id=aggregate_id)
        now = self._now()
        article_id = self._upper(aggregate_id)

        # --- fact_articles ---
        session.execute(delete(FactArticle).where(FactArticle.source_id == article_id))

        article = session.execute(
            select(SyncArticle).where(SyncArticle.source_id == article_id)
        ).scalar_one_or_none()

        if article:
            session.add(FactArticle(
                source_id=self._upper(article.source_id),
                code=self._upper(article.source_id),
                description=self._strip(article.description),
                description_2=self._strip(article.description_2),
                unit_of_measure=self._upper(article.unit_of_measure),
                is_blocked=article.is_blocked,
                material_code=self._upper(article.material_code),
                category=self._upper(article.category),
                built_at=now,
                sync_run_id=article.sync_run_id,
            ))
            result.records_rebuilt += 1

        # --- computed_stock_balances ---
        session.execute(
            delete(ComputedStockBalance).where(ComputedStockBalance.article_source_id == article_id)
        )

        stock_rows = session.execute(
            select(
                FactStockMovement.depot_code,
                func.sum(FactStockMovement.qty_in).label("qty_in_total"),
                func.sum(FactStockMovement.qty_out).label("qty_out_total"),
                func.count().label("movement_count"),
            )
            .where(FactStockMovement.article_source_id == article_id)
            .group_by(FactStockMovement.depot_code)
        ).all()

        for row in stock_rows:
            qty_in = row.qty_in_total or 0
            qty_out = row.qty_out_total or 0
            session.add(ComputedStockBalance(
                article_source_id=article_id,
                depot_code=row.depot_code,
                qty_in_total=row.qty_in_total,
                qty_out_total=row.qty_out_total,
                stock_balance=qty_in - qty_out,
                movement_count=row.movement_count,
                built_at=now,
            ))
            result.records_rebuilt += 1

        # --- computed_production_status ---
        session.execute(
            delete(ComputedProductionStatus).where(ComputedProductionStatus.article_source_id == article_id)
        )

        prod_row = session.execute(
            select(
                func.sum(FactProduction.qty_to_produce - FactProduction.qty_produced).label("qty_in_production"),
                func.count().label("open_order_count"),
            )
            .where(FactProduction.article_source_id == article_id)
            .where(FactProduction.is_closed == False)  # noqa: E712
        ).one()

        if prod_row.open_order_count and prod_row.open_order_count > 0:
            session.add(ComputedProductionStatus(
                article_source_id=article_id,
                qty_in_production=prod_row.qty_in_production,
                open_order_count=prod_row.open_order_count,
                built_at=now,
            ))
            result.records_rebuilt += 1

        # --- computed_article_demand ---
        session.execute(
            delete(ComputedArticleDemand).where(ComputedArticleDemand.article_source_id == article_id)
        )

        total_stock_row = session.execute(
            select(func.sum(FactStockMovement.qty_in - FactStockMovement.qty_out).label("total_stock"))
            .where(FactStockMovement.article_source_id == article_id)
        ).one()

        demand_row = session.execute(
            select(
                func.sum(
                    FactOrderLine.qty_ordered - func.coalesce(FactOrderLine.qty_shipped, 0)
                ).label("total_open_demand")
            )
            .where(FactOrderLine.article_source_id == article_id)
            .where(FactOrderLine.qty_ordered.is_not(None))
            .where(FactOrderLine.qty_ordered - func.coalesce(FactOrderLine.qty_shipped, 0) > 0)
        ).one()

        total_stock = total_stock_row.total_stock
        total_open_demand = demand_row.total_open_demand

        if total_stock is not None or total_open_demand is not None:
            s = total_stock or 0
            d = total_open_demand or 0
            session.add(ComputedArticleDemand(
                article_source_id=article_id,
                total_stock=total_stock,
                total_open_demand=total_open_demand,
                net_available_raw=s - d,
                built_at=now,
            ))
            result.records_rebuilt += 1

        return result
