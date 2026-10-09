import pytest
from app.identity.auth_service import normalize_email, validate_password, csrf_token, csrf_valid, allowed_origin, PASSWORD_HASHER


def test_email_normalization():
    assert normalize_email('  User@Example.COM ') == 'user@example.com'
    with pytest.raises(ValueError):
        normalize_email('invalid')


def test_password_policy_and_argon2id():
    validate_password('long-enough-secret')
    with pytest.raises(ValueError):
        validate_password('short')
    digest = PASSWORD_HASHER.hash('long-enough-secret')
    assert digest.startswith('$argon2id$')
    assert PASSWORD_HASHER.verify(digest, 'long-enough-secret')


def test_csrf_binding():
    token = 'opaque-session-token'
    assert csrf_valid(token, csrf_token(token))
    assert not csrf_valid('different-token', csrf_token(token))
    assert not csrf_valid(token, None)


def test_origin_exact_match():
    assert allowed_origin('http://localhost:3000', 'http://localhost:3000,https://example.com')
    assert not allowed_origin('https://evil.example.com', 'https://example.com')
    assert not allowed_origin(None, 'https://example.com')
