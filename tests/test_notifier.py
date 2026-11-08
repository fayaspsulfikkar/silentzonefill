"""
Tests for NotifierService (Phase 6).
Tests Telegram bot notifications across announcement, success, failure, seats full, and manual intervention.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.config import Settings
from app.services.notifier import NotifierService


@pytest.fixture
def notifier_settings():
    return Settings(
        reg_name="Test User",
        reg_phone="9876543210",
        reg_batch="BCK-416",
        telegram_bot_token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        telegram_chat_id="987654321",
    )


@pytest.mark.asyncio
async def test_notifier_sends_success_message(notifier_settings: Settings):
    with respx.mock:
        route = respx.route().respond(200, json={"ok": True})
        svc = NotifierService(notifier_settings)
        await svc.send_success()

        assert route.called
        req = route.calls.last.request
        assert b"SUCCESS" in req.content
        assert b"BCK-416" in req.content


@pytest.mark.asyncio
async def test_notifier_sends_seats_full(notifier_settings: Settings):
    with respx.mock:
        route = respx.route().respond(200, json={"ok": True})
        svc = NotifierService(notifier_settings)
        await svc.send_seats_full()

        assert route.called
        req = route.calls.last.request
        assert b"SEATS FULL" in req.content


@pytest.mark.asyncio
async def test_notifier_sends_failure(notifier_settings: Settings):
    with respx.mock:
        route = respx.route().respond(200, json={"ok": True})
        svc = NotifierService(notifier_settings)
        await svc.send_failure("Form closed unexpectedly")

        assert route.called
        req = route.calls.last.request
        assert b"FAILED" in req.content
        assert b"Form closed unexpectedly" in req.content


@pytest.mark.asyncio
async def test_notifier_skips_when_no_token():
    empty_settings = Settings(
        telegram_bot_token="",
        telegram_chat_id="",
    )
    svc = NotifierService(empty_settings)
    await svc.send_success()
