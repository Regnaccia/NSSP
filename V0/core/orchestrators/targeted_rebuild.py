"""
TargetedRebuildRunner — rebuild guidato dal change_set dell'ultima sync run.

Flusso:
  1. Legge l'ultimo core_run COMPLETED per sapere fino a quale sync_run_id si era arrivati
  2. Legge i SyncChangeItem successivi
  3. Risolve gli Aggregate impattati via DependencyRegistry
  4. Ricostruisce in ordine: OrderAggregate → ArticleSupplyDemandAggregate
  5. Applica FifoAllocationPolicy per tutti gli articoli impattati
     (inclusi quelli derivati dagli ordini ricostruiti)
  6. Logga il risultato in core_run
"""

from datetime import datetime, timezone
from sqlalchemy import select, func

from db.session import get_session
from core.models.core_run import CoreRun
from core.aggregates.order_aggregate import OrderAggregate
from core.aggregates.article_supply_demand_aggregate import ArticleSupplyDemandAggregate
from core.orchestrators.dependency_registry import DependencyRegistry
from core.policies.fifo_allocation import FifoAllocationPolicy
from core.computed_facts.models.computed_order_line import ComputedOrderLine
from sync.models.sync_change_item import SyncChangeItem


def _get_last_processed_sync_run_id(session) -> int:
    """
    Ritorna il sync_run_id_to dell'ultimo core_run COMPLETED (FULL o TARGETED).
    Il full rebuild fissa il baseline — il targeted parte da li'.
    """
    row = session.execute(
        select(func.max(CoreRun.sync_run_id_to))
        .where(CoreRun.status.in_(["COMPLETED", "COMPLETED_WITH_WARNINGS"]))
    ).scalar()
    return int(row) if row is not None else 0


def get_latest_sync_run_id(session) -> int:
    """Ritorna il massimo sync_run_id presente in sync_change_item."""
    row = session.execute(select(func.max(SyncChangeItem.sync_run_id))).scalar()
    return int(row) if row is not None else 0


def _get_article_ids_from_orders(session, order_ids: set) -> set:
    """
    Ritorna i distinti article_source_id presenti in computed_order_lines
    per gli ordini dati. Usato per estendere gli articoli da processare nella policy.
    """
    if not order_ids:
        return set()
    rows = session.execute(
        select(ComputedOrderLine.article_source_id)
        .where(ComputedOrderLine.order_source_id.in_([int(x) for x in order_ids]))
        .where(ComputedOrderLine.article_source_id.is_not(None))
        .distinct()
    ).scalars().all()
    return {r.strip().upper() for r in rows}


def run_targeted_rebuild() -> dict:
    started_at = datetime.now(timezone.utc)

    with get_session() as session:
        # Crea core_run in stato STARTED
        core_run = CoreRun(
            started_at=started_at,
            status="STARTED",
            rebuild_type="TARGETED",
        )
        session.add(core_run)
        session.flush()

        try:
            sync_run_id_from = _get_last_processed_sync_run_id(session) + 1
            sync_run_id_to = get_latest_sync_run_id(session)

            if sync_run_id_to < sync_run_id_from:
                core_run.finished_at = datetime.now(timezone.utc)
                core_run.status = "COMPLETED"
                core_run.sync_run_id_from = None
                core_run.sync_run_id_to = None
                core_run.aggregates_rebuilt = 0
                core_run.records_rebuilt = 0
                core_run.notes = "Nessuna sync run nuova"
                return {"status": "COMPLETED", "aggregates_rebuilt": 0, "records_rebuilt": 0}

            # Legge il change_set
            change_items = session.execute(
                select(SyncChangeItem)
                .where(SyncChangeItem.sync_run_id >= sync_run_id_from)
                .where(SyncChangeItem.sync_run_id <= sync_run_id_to)
            ).scalars().all()

            if not change_items:
                core_run.finished_at = datetime.now(timezone.utc)
                core_run.status = "COMPLETED"
                core_run.sync_run_id_from = sync_run_id_from
                core_run.sync_run_id_to = sync_run_id_to
                core_run.aggregates_rebuilt = 0
                core_run.records_rebuilt = 0
                core_run.notes = "Nessun change item nel range"
                return {"status": "COMPLETED", "aggregates_rebuilt": 0, "records_rebuilt": 0}

            # Risolve gli aggregate impattati
            registry = DependencyRegistry()
            affected = registry.resolve(session, change_items)

            total_aggregates = 0
            total_records = 0
            has_errors = False

            # Ordine sicuro: OrderAggregate prima, poi ArticleSupplyDemandAggregate
            for aggregate_class in [OrderAggregate, ArticleSupplyDemandAggregate]:
                ids = affected.get(aggregate_class, set())
                if not ids:
                    continue

                aggregate = aggregate_class()
                for agg_id in sorted(ids):
                    print(f"  -> {aggregate.aggregate_type}({agg_id})...", end=" ", flush=True)
                    try:
                        result = aggregate.rebuild(session, agg_id)
                        print(result)
                        total_aggregates += 1
                        total_records += result.records_rebuilt
                        if result.errors:
                            has_errors = True
                            for err in result.errors:
                                print(f"    WARN: {err}")
                    except Exception as e:
                        has_errors = True
                        print(f"ERROR: {e}")
                        raise

            # flush per rendere visibili i computed_order_lines appena ricostruiti
            session.flush()

            # Articoli da processare con la policy:
            # - quelli impattati direttamente (ArticleSupplyDemandAggregate)
            # - quelli derivati dagli ordini ricostruiti (le loro righe in computed_order_lines)
            order_ids = affected.get(OrderAggregate, set())
            article_ids_from_orders = _get_article_ids_from_orders(session, order_ids)
            article_ids_direct = affected.get(ArticleSupplyDemandAggregate, set())
            policy_article_ids = article_ids_direct | article_ids_from_orders

            policy = FifoAllocationPolicy()
            total_policy_updated = 0
            print("--- Policy ---")
            for article_id in sorted(policy_article_ids):
                print(f"  -> fifo_allocation({article_id})...", end=" ", flush=True)
                try:
                    policy_result = policy.apply(session, article_id)
                    print(policy_result)
                    total_policy_updated += policy_result.records_updated
                    if policy_result.errors:
                        has_errors = True
                        for err in policy_result.errors:
                            print(f"    WARN: {err}")
                except Exception as e:
                    has_errors = True
                    print(f"ERROR: {e}")
                    raise

            core_run.finished_at = datetime.now(timezone.utc)
            core_run.status = "COMPLETED_WITH_WARNINGS" if has_errors else "COMPLETED"
            core_run.sync_run_id_from = sync_run_id_from
            core_run.sync_run_id_to = sync_run_id_to
            core_run.aggregates_rebuilt = total_aggregates
            core_run.records_rebuilt = total_records + total_policy_updated

            return {
                "status": core_run.status,
                "aggregates_rebuilt": total_aggregates,
                "records_rebuilt": total_records,
                "policy_updated": total_policy_updated,
                "sync_run_id_from": sync_run_id_from,
                "sync_run_id_to": sync_run_id_to,
            }

        except Exception as e:
            core_run.finished_at = datetime.now(timezone.utc)
            core_run.status = "FAILED"
            core_run.notes = str(e)
            raise
