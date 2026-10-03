"""Verify a downloaded release directory using its SHA256SUMS (stdlib only)."""
import argparse
import hashlib
from pathlib import Path
import re


def verify(directory):
    records = (directory / 'SHA256SUMS').read_text(encoding='utf-8').splitlines()
    expected = set()
    if not records:
        raise ValueError('Empty checksum manifest')
    for line in records:
        digest, separator, name = line.partition('  ')
        if not separator or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Invalid checksum record')
        if not name or name in {'.', '..', 'SHA256SUMS'} or '/' in name or '\\' in name or ':' in name:
            raise ValueError('Invalid artifact filename')
        if name in expected:
            raise ValueError('Duplicate artifact filename')
        expected.add(name)
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or unsafe artifact: {name}')
        actual = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                actual.update(chunk)
        if actual.hexdigest() != digest:
            raise ValueError(f'Checksum mismatch: {name}')
    found = {p.name for p in directory.iterdir() if p.name != 'SHA256SUMS'}
    if found != expected:
        raise ValueError('Artifact directory differs from checksum manifest')
    print(f'Checksums verified: {len(expected)} artifacts')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    verify(parser.parse_args().directory)
