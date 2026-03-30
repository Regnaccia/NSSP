"""
APScheduler: job schedulati per sync EasyJob → MRS.

Frequenze (da config):
  - articoli, clienti:    ogni 60 min
  - ordini, righe_ordine: ogni 5 min
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from app.config import SYNC_INTERVAL_FAST_MIN, SYNC_INTERVAL_SLOW_MIN
from app.database import SessionLocal
from app.sync.handlers import sync_articoli, sync_clienti, sync_ordini_e_righe
from app.services.scorte import ricalcola_scorte_tutti

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_in_session(handler_fn):
    """Wrapper che apre una sessione, chiama handler_fn, chiude la sessione."""
    session = SessionLocal()
    try:
        handler_fn(session)
    except Exception as exc:
        logger.error("Scheduler job fallito [%s]: %s", handler_fn.__name__, exc)
    finally:
        session.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="Europe/Rome")

    _scheduler.add_job(
        lambda: _run_in_session(sync_articoli),
        trigger=IntervalTrigger(minutes=SYNC_INTERVAL_SLOW_MIN),
        id="sync_articoli",
        name="Sync articoli (ANAART)",
        replace_existing=True,
    )

    _scheduler.add_job(
        lambda: _run_in_session(sync_clienti),
        trigger=IntervalTrigger(minutes=SYNC_INTERVAL_SLOW_MIN),
        id="sync_clienti",
        name="Sync clienti (ANACLI)",
        replace_existing=True,
    )

    _scheduler.add_job(
        lambda: _run_in_session(sync_ordini_e_righe),
        trigger=IntervalTrigger(minutes=SYNC_INTERVAL_FAST_MIN),
        id="sync_ordini_e_righe",
        name="Sync ordini + righe (V_TORDCLI)",
        replace_existing=True,
    )

    _scheduler.add_job(
        lambda: _run_in_session(ricalcola_scorte_tutti),
        trigger=CronTrigger(day=1, hour=2, timezone="Europe/Rome"),
        id="ricalcolo_scorte_mensile",
        name="Ricalcolo scorte mensili (primo del mese alle 2:00)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "Scheduler avviato: articoli/clienti ogni %d min, ordini ogni %d min",
        SYNC_INTERVAL_SLOW_MIN,
        SYNC_INTERVAL_FAST_MIN,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler fermato")


def get_scheduler() -> BackgroundScheduler | None:
    return _scheduler
