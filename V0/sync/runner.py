"""
Entry point del layer sync — full sync da Easy.

Utilizzo:
    python -m sync.runner
"""

from datetime import datetime, timezone

from db.session import get_session
from sync.easy.connector import get_easy_engine
from sync.models.sync_run import SyncRun
from sync.easy.extractors import (
    CustomerExtractor,
    DestinationExtractor,
    ArticleExtractor,
    OrderHeaderExtractor,
    OrderLineExtractor,
    StockMovementExtractor,
    ProductionExtractor,
)

EXTRACTORS = [
    CustomerExtractor(),
    DestinationExtractor(),
    ArticleExtractor(),
    OrderHeaderExtractor(),
    OrderLineExtractor(),
    StockMovementExtractor(),
    ProductionExtractor(),
]


def run_full_sync():
    easy_engine = get_easy_engine()

    with get_session() as session:
        sync_run = SyncRun(
            started_at=datetime.now(timezone.utc),
            status="STARTED",
            scope="full",
        )
        session.add(sync_run)
        session.flush()  # ottieni sync_run.id

        total_inserted = total_updated = total_deleted = total_read = 0
        has_warnings = False

        try:
            for extractor in EXTRACTORS:
                print(f"  -> {extractor.entity_type}...", end=" ", flush=True)
                result = extractor.run(session, easy_engine, sync_run.id)
                print(result)

                total_read += result.records_read
                total_inserted += result.records_inserted
                total_updated += result.records_updated
                total_deleted += result.records_deleted

                if result.errors:
                    has_warnings = True
                    for err in result.errors:
                        print(f"    WARN: {err}")

            sync_run.status = "COMPLETED_WITH_WARNINGS" if has_warnings else "COMPLETED"

        except Exception as e:
            sync_run.status = "FAILED"
            sync_run.error_message = str(e)
            raise

        finally:
            sync_run.finished_at = datetime.now(timezone.utc)
            sync_run.records_read = total_read
            sync_run.records_inserted = total_inserted
            sync_run.records_updated = total_updated
            sync_run.records_deleted = total_deleted

    return sync_run


if __name__ == "__main__":
    print("=" * 50)
    print("MRS Sync — full sync avviata")
    print("=" * 50)
    run = run_full_sync()
    print("=" * 50)
    print(f"Stato:     {run.status}")
    duration = (run.finished_at - run.started_at).total_seconds() if run.finished_at else 0
    print(f"Durata:    {duration:.1f}s")
    print(f"Letti:     {run.records_read}")
    print(f"Inseriti:  {run.records_inserted}")
    print(f"Aggiornati:{run.records_updated}")
    print(f"Eliminati: {run.records_deleted}")
    if run.error_message:
        print(f"Errore:    {run.error_message}")
