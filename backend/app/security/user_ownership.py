"""Authenticated ownership cannot be forged with the legacy X-Client-Id syntax."""
from __future__ import annotations
from uuid import UUID


def user_owner_id(user_id: str) -> str:
    return f"user:{UUID(user_id)}"
