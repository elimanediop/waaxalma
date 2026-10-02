"""Local health checks; no paid or remote provider requests."""
from contextlib import closing
import logging
from pathlib import Path
import sqlite3
import tempfile
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.settings import get_settings
from app.version import __version__

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
@router.get("/health/live")
def live():
    return {"status": "ok", "service": "waaxalma", "version": __version__}


def writable_directory(path: Path) -> None:
    with tempfile.TemporaryFile(dir=path) as file:
        file.write(b"health")
        file.flush()


def check_local_resources() -> None:
    from app.bootstrap.container import session_manager
    settings = get_settings()
    for path in (settings.static_dir / "audio", settings.upload_dir):
        writable_directory(path)
    repo = session_manager.repository
    if hasattr(repo, "database_path"):
        # rw prevents accidentally creating a missing DB; transaction is rolled
        # back and persists no changes. This also tests DB write availability.
        path = Path(repo.database_path)
        with closing(sqlite3.connect(path.as_uri()+"?mode=rw", uri=True, timeout=0.25)) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("SELECT owner_id FROM sessions LIMIT 1")
            db.execute("UPDATE sessions SET updated_at=updated_at WHERE 0")
            db.rollback()
    else:
        session_manager.get_session("readiness-probe")


@router.get("/health/ready")
def ready(request: Request):
    if not getattr(request.app.state, "startup_complete", False):
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    try:
        check_local_resources()
    except Exception:
        logger.warning("Local readiness check failed", exc_info=True)
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready", "service": "waaxalma", "version": __version__}
