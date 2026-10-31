import asyncio

from app import main
from app.services import billing_scheduler


def test_enabled_scheduler_starts_with_application_and_is_cancelled_on_shutdown(monkeypatch):
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def scheduler_loop():
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    monkeypatch.setattr(main.settings, "billing_scheduler_enabled", True)
    monkeypatch.setattr(main, "billing_scheduler_loop", scheduler_loop)

    async def exercise_lifespan():
        async with main.lifespan(main.app):
            await asyncio.wait_for(started.wait(), timeout=1)
        assert stopped.is_set()

    asyncio.run(exercise_lifespan())


def test_scheduled_billing_cycle_invokes_due_processor_and_closes_session(monkeypatch):
    class Session:
        closed = False
        rolled_back = False

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    session = Session()
    processed = []
    monkeypatch.setattr(billing_scheduler, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        billing_scheduler,
        "process_due_invoices",
        lambda db: processed.append(db) or {"invoices_created": 2},
    )

    billing_scheduler.run_billing_cycle()

    assert processed == [session]
    assert session.closed
    assert not session.rolled_back


def test_failed_scheduled_billing_cycle_rolls_back_and_closes_session(monkeypatch):
    class Session:
        closed = False
        rolled_back = False

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    session = Session()
    monkeypatch.setattr(billing_scheduler, "SessionLocal", lambda: session)

    def fail(_db):
        raise RuntimeError("billing failed")

    monkeypatch.setattr(billing_scheduler, "process_due_invoices", fail)

    billing_scheduler.run_billing_cycle()

    assert session.rolled_back
    assert session.closed
