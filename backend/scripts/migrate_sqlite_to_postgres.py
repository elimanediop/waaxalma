"""Explicit, atomic SQLite v2 -> PostgreSQL translation data import.

Run from backend: python -m scripts.migrate_sqlite_to_postgres --sqlite PATH --database-url URL [--apply]
Default mode is a read-only preflight. Never imports into a non-empty destination.
"""
from __future__ import annotations
import argparse
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from app.sessions.database_tools import inspect_database


def _timestamp(value: str | None):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Naive SQLite timestamp is not safe to import: ' + repr(value))
    return parsed


def migrate(sqlite_path: str, database_url: str, *, apply: bool = False) -> dict:
    import psycopg
    source = Path(sqlite_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f'SQLite source not found: {source}')
    report = inspect_database(source)
    if report['schema_version'] != 2:
        raise ValueError('Migrate SQLite schema to v2 with the existing upgrade tooling first')
    url = database_url.replace('postgresql+psycopg://', 'postgresql://', 1)
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as sq:
        sq.row_factory = sqlite3.Row
        with psycopg.connect(url, connect_timeout=5) as pg:
            with pg.cursor() as cur:
                # Prevent two importers from passing the empty-destination check concurrently.
                cur.execute('LOCK TABLE translation_sessions, translation_messages IN ACCESS EXCLUSIVE MODE')
                cur.execute('SELECT (SELECT count(*) FROM translation_sessions), (SELECT count(*) FROM translation_messages)')
                existing = cur.fetchone()
                if existing != (0, 0):
                    raise ValueError('Destination must be empty; refusing to merge or overwrite data')
                result = {'source_sessions': report['sessions'], 'source_messages': report['messages'],
                          'unowned_sessions': report['unowned_sessions'], 'mode': 'apply' if apply else 'preflight'}
                if not apply:
                    pg.rollback()
                    return result
                # Read-only SQLite transaction provides a consistent snapshot across both tables.
                sq.execute('BEGIN')
                for row in sq.execute('SELECT * FROM sessions ORDER BY session_id'):
                    d = dict(row)
                    metadata = json.loads(d['metadata_json'])
                    if not isinstance(metadata, dict):
                        raise ValueError('Expected object metadata for session ' + d['session_id'])
                    cur.execute('''INSERT INTO translation_sessions
                        (session_id,agent_name,owner_id,execution_mode,source_language,target_language,
                         status,created_at,updated_at,closed_at,metadata_json)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)''',
                        (d['session_id'], d['agent_name'], d['owner_id'], d['execution_mode'],
                         d['source_language'], d['target_language'], d['status'],
                         _timestamp(d['created_at']), _timestamp(d['updated_at']),
                         _timestamp(d['closed_at']), json.dumps(metadata)))
                for row in sq.execute('SELECT * FROM session_messages ORDER BY id'):
                    d = dict(row)
                    cur.execute('''INSERT INTO translation_messages (session_id,role,content,created_at)
                                   VALUES (%s,%s,%s,%s)''',
                                (d['session_id'], d['role'], d['content'], d['created_at']))
                cur.execute('SELECT (SELECT count(*) FROM translation_sessions), (SELECT count(*) FROM translation_messages)')
                actual = cur.fetchone()
                if actual != (report['sessions'], report['messages']):
                    raise ValueError(f'Count mismatch: source={report["sessions"], report["messages"]} target={actual}')
                # Compare each session's message order and content, not just aggregate counts.
                src = [(r['session_id'], r['role'], r['content'], r['created_at']) for r in
                       sq.execute('SELECT session_id,role,content,created_at FROM session_messages ORDER BY id')]
                cur.execute('SELECT session_id,role,content,created_at FROM translation_messages ORDER BY id')
                dst = list(cur.fetchall())
                if src != dst:
                    raise ValueError('Message order/content verification failed; transaction rolled back')
                # Explicit commit only after verification. A failure rolls back on connection exit.
                pg.commit()
                result['verified_sessions'], result['verified_messages'] = actual
                return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sqlite', required=True, help='Path to existing SQLite v2 file')
    parser.add_argument('--database-url', required=True, help='PostgreSQL DSN (avoid shell history for secrets)')
    parser.add_argument('--apply', action='store_true', help='Actually write; default is preflight')
    args = parser.parse_args()
    print(json.dumps(migrate(args.sqlite, args.database_url, apply=args.apply), indent=2))


if __name__ == '__main__':
    main()
