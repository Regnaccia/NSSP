"""
DependencyRegistry — risolve un change_set in aggregates da ricostruire.

Dato un insieme di SyncChangeItem, produce:
    {
        OrderAggregate:                {"107511", "107512"},
        ArticleSupplyDemandAggregate:  {"ART001", "ART002"},
    }

Strategia: batch lookup per entity_type — una query IN per tipo,
nessuna modifica al layer sync.
"""

from sqlalchemy import select, tuple_
from core.aggregates.order_aggregate import OrderAggregate
from core.aggregates.article_supply_demand_aggregate import ArticleSupplyDemandAggregate
from sync.models.sync_order_lines import SyncOrderLine
from sync.models.sync_stock_movements import SyncStockMovement
from sync.models.sync_productions import SyncProduction


class DependencyRegistry:

    def resolve(self, session, change_items: list) -> dict:
        """
        Riceve una lista di SyncChangeItem e ritorna un dict:
            { AggregateClass: set(aggregate_id_str) }
        """
        order_ids: set[str] = set()
        article_ids: set[str] = set()

        # Raggruppa i change items per entity_type per il batch lookup
        by_type: dict[str, list] = {}
        for item in change_items:
            by_type.setdefault(item.entity_type, []).append(item)

        # sync_order_headers → OrderAggregate diretto
        for item in by_type.get("sync_order_headers", []):
            order_ids.add(item.source_id)

        # sync_order_lines → OrderAggregate (order_source_id dal composite key)
        #                  → ArticleSupplyDemandAggregate (batch lookup article_source_id)
        order_line_items = by_type.get("sync_order_lines", [])
        if order_line_items:
            pks = []
            for item in order_line_items:
                parts = item.source_id.split("|")
                order_ids.add(parts[0])
                pks.append((int(parts[0]), int(parts[1])))

            # Batch lookup article_source_id
            rows = session.execute(
                select(SyncOrderLine.article_source_id)
                .where(
                    tuple_(SyncOrderLine.order_source_id, SyncOrderLine.line_number).in_(pks)
                )
                .where(SyncOrderLine.article_source_id.is_not(None))
            ).scalars().all()
            for art_id in rows:
                article_ids.add(art_id.strip().upper())

        # sync_articles → ArticleSupplyDemandAggregate diretto
        for item in by_type.get("sync_articles", []):
            article_ids.add(item.source_id.strip().upper())

        # sync_stock_movements → ArticleSupplyDemandAggregate (batch lookup)
        stock_items = by_type.get("sync_stock_movements", [])
        if stock_items:
            source_ids = [int(item.source_id) for item in stock_items]
            rows = session.execute(
                select(SyncStockMovement.article_source_id)
                .where(SyncStockMovement.source_id.in_(source_ids))
                .where(SyncStockMovement.article_source_id.is_not(None))
            ).scalars().all()
            for art_id in rows:
                article_ids.add(art_id.strip().upper())

        # sync_productions → ArticleSupplyDemandAggregate (batch lookup)
        prod_items = by_type.get("sync_productions", [])
        if prod_items:
            source_ids = [int(item.source_id) for item in prod_items]
            rows = session.execute(
                select(SyncProduction.article_source_id)
                .where(SyncProduction.source_id.in_(source_ids))
                .where(SyncProduction.article_source_id.is_not(None))
            ).scalars().all()
            for art_id in rows:
                article_ids.add(art_id.strip().upper())

        result = {}
        if order_ids:
            result[OrderAggregate] = order_ids
        if article_ids:
            result[ArticleSupplyDemandAggregate] = article_ids
        return result
