"""Optional closed-session maintenance; no active-session expiry or file deletion."""
import asyncio
from datetime import datetime, timedelta, timezone
from prometheus_client import Counter
from app.observability.events import emit

DELETED = Counter("waaxalma_sessions_deleted_total", "Closed sessions deleted by retention maintenance.")
FAILURES = Counter("waaxalma_session_cleanup_failures_total", "Failed automatic retention runs.")


def cleanup(repository, days, *, dry_run=True, now=None):
    if type(days) is not int or days < 1:
        raise ValueError("Retention days must be a positive integer")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("Maintenance clock must have a timezone")
    count = repository.purge_closed_before(current-timedelta(days=days), dry_run=dry_run)
    if not dry_run:
        DELETED.inc(count)
    emit("session.cleanup", status="dry_run" if dry_run else "success")
    return count


class RetentionWorker:
    def __init__(self, repository, settings):
        self.repository = repository
        self.settings = settings
        self.stop_event = asyncio.Event()
        self.task = None

    def start(self):
        if self.settings.session_cleanup_enabled:
            self.task = asyncio.create_task(self.run(), name="waaxalma-retention")

    async def run(self):
        while not self.stop_event.is_set():
            try:
                await asyncio.to_thread(cleanup, self.repository, self.settings.session_retention_days, dry_run=False)
            except Exception:
                FAILURES.inc()
                emit("session.cleanup", status="error", error_type="retention_error")
            try:
                await asyncio.wait_for(self.stop_event.wait(), timeout=self.settings.session_cleanup_interval_seconds)
            except TimeoutError:
                pass

    async def stop(self):
        self.stop_event.set()
        if self.task is not None:
            # Allow an in-flight SQLite transaction to finish rather than cancel it.
            await self.task
