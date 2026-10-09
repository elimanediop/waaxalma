"""Unit tests independent of PostgreSQL and HTTP authentication."""
import re
import pytest
from app.identity.tokens import generate_session_token, hash_session_token


def test_tokens_are_random_and_hashes_are_stable():
    first, second = generate_session_token(), generate_session_token()
    assert first != second
    assert len(first) >= 40
    assert hash_session_token(first) == hash_session_token(first)
    assert hash_session_token(first) != hash_session_token(second)
    assert re.fullmatch(r'[0-9a-f]{64}', hash_session_token(first))


def test_empty_token_is_rejected():
    with pytest.raises(ValueError):
        hash_session_token('')
