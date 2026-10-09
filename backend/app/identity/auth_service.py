"""Database-backed, opaque cookie authentication for the optional public API."""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import psycopg
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.identity.tokens import generate_session_token, hash_session_token

PASSWORD_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
COOKIE_NAME = "waaxalma_session"
SESSION_DAYS = 7


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError("Invalid email")
    return value


def validate_password(password: str) -> None:
    if len(password) < 12 or len(password) > 1024:
        raise ValueError("Password must contain between 12 and 1024 characters")


def csrf_token(session_token: str) -> str:
    """Bound to the HttpOnly session secret; client sends it via X-CSRF-Token."""
    return hmac.new(session_token.encode(), b"waaxalma-csrf-v1", hashlib.sha256).hexdigest()


def csrf_valid(session_token: str, candidate: str | None) -> bool:
    return bool(candidate) and hmac.compare_digest(csrf_token(session_token), candidate)


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Authentication requires a PostgreSQL DATABASE_URL")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def connection():
    return psycopg.connect(database_url(), row_factory=dict_row, connect_timeout=5)


def register(email: str, password: str) -> dict:
    email = normalize_email(email)
    validate_password(password)
    hashed = PASSWORD_HASHER.hash(password)
    user_id = uuid.uuid4()
    try:
        with connection() as db:
            with db.cursor() as cur:
                cur.execute("INSERT INTO users (user_id, email_normalized, password_hash) VALUES (%s,%s,%s)", (user_id, email, hashed))
    except UniqueViolation:
        raise ValueError("Email already registered") from None
    return {"user_id": str(user_id), "email": email}


def authenticate(email: str, password: str) -> tuple[dict, str]:
    try:
        normalized = normalize_email(email)
    except ValueError:
        normalized = ""
    with connection() as db:
        with db.cursor() as cur:
            cur.execute("SELECT user_id, email_normalized, password_hash, is_active FROM users WHERE email_normalized=%s", (normalized,))
            row = cur.fetchone()
            # Equalize missing-account work with a fixed Argon2id hash.
            stored_hash = row["password_hash"] if row else DUMMY_PASSWORD_HASH
            try:
                valid = PASSWORD_HASHER.verify(stored_hash, password)
            except (VerifyMismatchError, VerificationError, ValueError):
                valid = False
            if not row or not row["is_active"] or not valid:
                raise ValueError("Invalid credentials")
            raw = generate_session_token()
            now = datetime.now(timezone.utc)
            cur.execute("INSERT INTO auth_sessions (session_id,user_id,token_hash,created_at,expires_at) VALUES (%s,%s,%s,%s,%s)", (uuid.uuid4(), row["user_id"], hash_session_token(raw), now, now + timedelta(days=SESSION_DAYS)))
            return {"user_id": str(row["user_id"]), "email": row["email_normalized"]}, raw


def resolve_user(token: str | None) -> dict | None:
    if not token:
        return None
    with connection() as db:
        with db.cursor() as cur:
            cur.execute("""SELECT u.user_id, u.email_normalized FROM auth_sessions s JOIN users u ON u.user_id=s.user_id
                WHERE s.token_hash=%s AND s.revoked_at IS NULL AND s.expires_at>now() AND u.is_active=TRUE""", (hash_session_token(token),))
            row = cur.fetchone()
    return {"user_id": str(row["user_id"]), "email": row["email_normalized"]} if row else None


def revoke(token: str) -> None:
    with connection() as db:
        with db.cursor() as cur:
            cur.execute("UPDATE auth_sessions SET revoked_at=now() WHERE token_hash=%s AND revoked_at IS NULL", (hash_session_token(token),))


def allowed_origin(origin: str | None, configured: str) -> bool:
    if not origin:
        return False
    return origin in {o.strip() for o in configured.split(",") if o.strip()}


# Fixed valid Argon2id hash to avoid fast unknown-user rejection. Never an actual account.
DUMMY_PASSWORD_HASH = PASSWORD_HASHER.hash("waaxalma-dummy-password-never-used")
