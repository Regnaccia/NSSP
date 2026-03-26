"""
Entry point del layer core.

Utilizzo:
    python -m core.runner           # full rebuild
    python -m core.runner targeted  # targeted rebuild dal change_set
"""

import sys
from datetime import datetime, timezone

from db.session import get_session
from core.facts.builders import (
    ArticleBuilder,
    CustomerBuilder,
    DestinationBuilder,
    OrderBuilder,
    OrderLineBuilder,
    StockMovementBuilder,
    ProductionBuilder,
)
from core.computed_facts.builders import (
    ComputedOrderLineBuilder,
    ComputedStockBalanceBuilder,
    ComputedProductionStatusBuilder,
    ComputedArticleDemandBuilder,
)
from core.orchestrators.targeted_rebuild import run_targeted_rebuild, get_latest_sync_run_id
from core.models.core_run import CoreRun
from core.policies.fifo_allocation import FifoAllocationPolicy
from core.computed_facts.models.computed_article_demand import ComputedArticleDemand
from core.states.builders.order_state_builder import OrderStateBuilder
from core.facts.models.fact_order import FactOrder
from sqlalchemy import select

# Ordine rispetta le dipendenze di chiave:
# Destination dipende da Customer → CustomerBuilder prima di DestinationBuilder
SOURCE_BUILDERS = [
    ArticleBuilder(),
    CustomerBuilder(),
    DestinationBuilder(),
    OrderBuilder(),
    OrderLineBuilder(),
    StockMovementBuilder(),
    ProductionBuilder(),
]

# Computed Facts leggono da fact_* → eseguiti dopo i Source Facts
COMPUTED_BUILDERS = [
    ComputedOrderLineBuilder(),
    ComputedStockBalanceBuilder(),
    ComputedProductionStatusBuilder(),
    ComputedArticleDemandBuilder(),
]


def _run_builders(session, builders) -> tuple[int, bool]:
    """Esegue una lista di builder. Ritorna (total_built, has_errors)."""
    total_built = 0
    has_errors = False

    for builder in builders:
        print(f"  -> {builder.entity_type}...", end=" ", flush=True)
        try:
            result = builder.build(session)
            print(result)
            total_built += result.records_built
            if result.errors:
                has_errors = True
                for err in result.errors:
                    print(f"    WARN: {err}")
        except Exception as e:
            has_errors = True
            print(f"ERROR: {e}")
            raise

    return total_built, has_errors


def run_full_rebuild():
    started_at = datetime.now(timezone.utc)
    total_built = 0
    has_errors = False

    with get_session() as session:
        print("--- Fase 1: Source Facts ---")
        built, errors = _run_builders(session, SOURCE_BUILDERS)
        total_built += built
        if errors:
            has_errors = True

        session.flush()  # rende visibili i Source Facts ai builder successivi
        print("--- Fase 2: Computed Facts ---")
        built, errors = _run_builders(session, COMPUTED_BUILDERS)
        total_built += built
        if errors:
            has_errors = True

        session.flush()  # rende visibili i Computed Facts alla policy
        print("--- Fase 3: Policy ---")
        policy = FifoAllocationPolicy()
        article_ids = session.execute(
            select(ComputedArticleDemand.article_source_id)
        ).scalars().all()
        for article_id in article_ids:
            print(f"  -> fifo_allocation({article_id})...", end=" ", flush=True)
            try:
                policy_result = policy.apply(session, article_id)
                print(policy_result)
                total_built += policy_result.records_updated
                if policy_result.errors:
                    has_errors = True
                    for err in policy_result.errors:
                        print(f"    WARN: {err}")
            except Exception as e:
                has_errors = True
                print(f"ERROR: {e}")
                raise

        session.flush()  # rende visibili i campi policy agli state builder
        print("--- Fase 4: States ---")
        state_builder = OrderStateBuilder()
        order_ids = session.execute(
            select(FactOrder.source_id)
        ).scalars().all()
        for order_id in order_ids:
            print(f"  -> order_state_builder({order_id})...", end=" ", flush=True)
            try:
                state_result = state_builder.build(session, order_id)
                print(state_result)
                total_built += state_result.line_states_built + 1
                if state_result.errors:
                    has_errors = True
                    for err in state_result.errors:
                        print(f"    WARN: {err}")
            except Exception as e:
                has_errors = True
                print(f"ERROR: {e}")
                raise

        # Logga il full rebuild in core_run — fissa il baseline per i targeted rebuild
        sync_run_id_to = get_latest_sync_run_id(session)
        finished_at = datetime.now(timezone.utc)
        status = "COMPLETED_WITH_WARNINGS" if has_errors else "COMPLETED"
        session.add(CoreRun(
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            rebuild_type="FULL",
            sync_run_id_to=sync_run_id_to,
            records_rebuilt=total_built,
        ))

    return total_built, has_errors, started_at, finished_at


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "full"

    if mode == "targeted":
        print("=" * 50)
        print("MRS Core — targeted rebuild")
        print("=" * 50)
        started = datetime.now(timezone.utc)
        result = run_targeted_rebuild()
        finished = datetime.now(timezone.utc)
        duration = (finished - started).total_seconds()
        print("=" * 50)
        print(f"Stato:      {result['status']}")
        print(f"Durata:     {duration:.1f}s")
        print(f"Aggregates: {result['aggregates_rebuilt']}")
        print(f"Records:    {result['records_rebuilt']}")
    else:
        print("=" * 50)
        print("MRS Core — full rebuild")
        print("=" * 50)
        total, errors, started, finished = run_full_rebuild()
        duration = (finished - started).total_seconds()
        print("=" * 50)
        status = "COMPLETED_WITH_WARNINGS" if errors else "COMPLETED"
        print(f"Stato:     {status}")
        print(f"Durata:    {duration:.1f}s")
        print(f"Costruiti: {total}")
