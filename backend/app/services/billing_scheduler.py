import asyncio
import logging

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.billing import process_due_invoices

logger = logging.getLogger(__name__)


def run_billing_cycle() -> None:
    db = SessionLocal()
    try:
        result = process_due_invoices(db)
    except Exception:
        db.rollback()
        logger.exception("Scheduled billing cycle failed.")
    else:
        logger.info("Scheduled billing cycle completed: %s", result)
    finally:
        db.close()


async def billing_scheduler_loop() -> None:
    while True:
        await asyncio.to_thread(run_billing_cycle)
        await asyncio.sleep(settings.billing_scheduler_interval_seconds)
