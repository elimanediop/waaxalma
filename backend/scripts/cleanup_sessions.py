"""Offline maintenance: dry-run by default, existing SQLite databases only."""
import argparse
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--apply", action="store_true", help="Delete eligible closed rows and their messages")
    args = parser.parse_args(argv)
    if args.retention_days < 1:
        parser.error("retention-days must be positive")
    # Do not construct a repository: its constructor performs startup migration.
    cutoff = datetime.now(timezone.utc)-timedelta(days=args.retention_days)
    try:
        with closing(sqlite3.connect(args.database.resolve().as_uri()+"?mode=rw", uri=True, timeout=5)) as db, db:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("BEGIN IMMEDIATE")
            clause = "status='closed' AND closed_at IS NOT NULL AND julianday(closed_at)<julianday(?)"
            params = (cutoff.isoformat(),)
            count = db.execute("SELECT COUNT(*) FROM sessions WHERE "+clause, params).fetchone()[0]
            if args.apply:
                db.execute("DELETE FROM sessions WHERE "+clause, params)
        print(json.dumps({"dry_run":not args.apply,"eligible_sessions":count,"cutoff":cutoff.isoformat()}))
    except sqlite3.Error:
        parser.exit(1, "Maintenance failed: verify the existing database, schema and access permissions.\n")


if __name__ == "__main__":
    main()
