"""Regression tests for authenticated WebSocket session revocation."""
import asyncio
from unittest.mock import Mock

import pytest

from app.api import user_realtime


def test_session_still_valid_matches_same_user(monkeypatch):
    monkeypatch.setattr(user_realtime.auth, "resolve_user", lambda token: {"user_id": "a"} if token == "live" else None)
    assert user_realtime.session_still_valid("live", "a")
    assert not user_realtime.session_still_valid("live", "b")
    assert not user_realtime.session_still_valid("revoked", "a")


def test_session_still_valid_fails_closed_on_database_error(monkeypatch):
    def broken(_token):
        raise RuntimeError("database unavailable")
    monkeypatch.setattr(user_realtime.auth, "resolve_user", broken)
    assert not user_realtime.session_still_valid("token", "a")


@pytest.mark.asyncio
async def test_monitor_closes_revoked_socket(monkeypatch):
    monkeypatch.setattr(user_realtime, "REVOCATION_CHECK_SECONDS", 0.001)
    monkeypatch.setattr(user_realtime, "session_still_valid", lambda token, user_id: False)
    socket = Mock()
    socket.close = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    await asyncio.wait_for(user_realtime.close_when_revoked(socket, "token", "user"), timeout=1)
    socket.close.assert_awaited_once_with(code=1008, reason="Authentication expired")


@pytest.mark.asyncio
async def test_monitor_does_not_close_valid_socket(monkeypatch):
    monkeypatch.setattr(user_realtime, "REVOCATION_CHECK_SECONDS", 0.001)
    monkeypatch.setattr(user_realtime, "session_still_valid", lambda token, user_id: True)
    socket = Mock()
    socket.close = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(user_realtime.close_when_revoked(socket, "token", "user"), timeout=0.02)
    socket.close.assert_not_awaited()
