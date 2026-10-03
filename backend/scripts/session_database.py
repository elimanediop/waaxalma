"""Inspect an existing session database or create a new consistent backup."""
import argparse
import json

from app.sessions.database_tools import backup_database, inspect_database


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--backup", help="New backup path; existing destinations are rejected")
    args = parser.parse_args()
    report = (backup_database(args.database, args.backup) if args.backup
              else inspect_database(args.database))
    # Only schema information and counts; no owners, messages or metadata.
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
