"""
Entry point del layer core — full rebuild dei Source Facts e Computed Facts.

Utilizzo:
    python -m core.runner
"""

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
)

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

    finished_at = datetime.now(timezone.utc)
    return total_built, has_errors, started_at, finished_at


if __name__ == "__main__":
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
