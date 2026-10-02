"""Explicit offline ownership assignment for an unowned Slice 1 session."""
from contextlib import closing
import argparse
from pathlib import Path
import sqlite3
from app.security.client_identity import ClientIdentity


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--session-id', required=True)
    parser.add_argument('--client-id', required=True)
    args = parser.parse_args()
    identity = ClientIdentity(args.client_id)
    path = Path(args.database).resolve()
    # mode=rw prevents an accidental empty database creation for a wrong path.
    with closing(sqlite3.connect(path.as_uri()+'?mode=rw', uri=True)) as connection, connection:
        cursor = connection.execute(
            'UPDATE sessions SET owner_id = ? WHERE session_id = ? AND owner_id IS NULL',
            (identity.client_id, args.session_id),
        )
        if cursor.rowcount != 1:
            raise SystemExit('No unowned session matched; no ownership changed.')
    print('Legacy session owner assigned.')


if __name__ == '__main__':
    main()
