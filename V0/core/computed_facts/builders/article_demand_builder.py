from sqlalchemy import select, delete, func
from core.facts.builders.base import BaseBuilder, BuildResult
from core.computed_facts.models.computed_article_demand import ComputedArticleDemand
from core.facts.models.fact_stock_movement import FactStockMovement
from core.facts.models.fact_order_line import FactOrderLine


class ComputedArticleDemandBuilder(BaseBuilder):
    entity_type = "computed_article_demand"
    model_class = ComputedArticleDemand
    strategy = "FULL_REBUILD"

    def build(self, session) -> BuildResult:
        result = BuildResult(entity_type=self.entity_type)
        now = self._now()

        result.records_deleted = session.execute(delete(ComputedArticleDemand)).rowcount

        # Stock totale per articolo (somma su tutti i depositi)
        stock_rows = session.execute(
            select(
                FactStockMovement.article_source_id,
                func.sum(FactStockMovement.qty_in - FactStockMovement.qty_out).label("total_stock"),
            )
            .where(FactStockMovement.article_source_id.is_not(None))
            .group_by(FactStockMovement.article_source_id)
        ).all()

        stock_by_article = {row.article_source_id: row.total_stock for row in stock_rows}

        # Domanda aperta per articolo: SUM(qty_ordered - qty_shipped) dove qty_remaining > 0
        demand_rows = session.execute(
            select(
                FactOrderLine.article_source_id,
                func.sum(
                    FactOrderLine.qty_ordered - func.coalesce(FactOrderLine.qty_shipped, 0)
                ).label("total_open_demand"),
            )
            .where(FactOrderLine.article_source_id.is_not(None))
            .where(FactOrderLine.qty_ordered.is_not(None))
            .where(
                FactOrderLine.qty_ordered - func.coalesce(FactOrderLine.qty_shipped, 0) > 0
            )
            .group_by(FactOrderLine.article_source_id)
        ).all()

        demand_by_article = {row.article_source_id: row.total_open_demand for row in demand_rows}

        # Unione degli articoli noti (con stock o con domanda)
        all_articles = set(stock_by_article.keys()) | set(demand_by_article.keys())

        for article_id in all_articles:
            total_stock = stock_by_article.get(article_id)
            total_open_demand = demand_by_article.get(article_id)

            if total_stock is not None or total_open_demand is not None:
                s = total_stock or 0
                d = total_open_demand or 0
                net_available_raw = s - d
            else:
                net_available_raw = None

            session.add(ComputedArticleDemand(
                article_source_id=article_id,
                total_stock=total_stock,
                total_open_demand=total_open_demand,
                net_available_raw=net_available_raw,
                built_at=now,
            ))
            result.records_built += 1

        return result
