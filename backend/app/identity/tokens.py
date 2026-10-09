"""Opaque authentication token helpers; raw tokens must never be persisted."""
from __future__ import annotations

import hashlib
import secrets


def generate_session_token() -> str:
    """Return a cryptographically random bearer token (256-bit entropy)."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """Return the SHA-256 hex digest used for token lookup in PostgreSQL."""
    if not isinstance(token, str) or not token:
        raise ValueError('Session token must be a nonempty string')
    return hashlib.sha256(token.encode('utf-8')).hexdigest()
