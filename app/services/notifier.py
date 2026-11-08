"""
NotifierService: sends concise Telegram Bot API notifications to the user.
"""

from __future__ import annotations

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class NotifierService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def _send(self, text: str) -> None:
        token = self._settings.telegram_bot_token
        chat_id = self._settings.telegram_chat_id

        if not token or not chat_id:
            logger.debug("Telegram not configured — skipping notification")
            return

        url = _TELEGRAM_API.format(token=token)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url,
                    json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                )
                resp.raise_for_status()
        except Exception:
            logger.exception("Failed to send Telegram notification")

    async def send_announcement_detected(self, form_url: str) -> None:
        await self._send(
            "📡 <b>Silent Zone Registration</b>\n"
            "Status: ANNOUNCEMENT DETECTED\n"
            "Automation starting now..."
        )

    async def send_success(self) -> None:
        s = self._settings
        await self._send(
            "✅ <b>Silent Zone Registration</b>\n"
            f"Status: SUCCESS\n"
            f"Name: {s.reg_name}\n"
            f"Batch: {s.reg_batch}\n"
            "Submission confirmed."
        )

    async def send_failure(self, reason: str) -> None:
        await self._send(
            "❌ <b>Silent Zone Registration</b>\n"
            f"Status: FAILED\n"
            f"Reason: {reason}"
        )

    async def send_seats_full(self) -> None:
        await self._send(
            "🔴 <b>Silent Zone Registration</b>\n"
            "Status: SEATS FULL\n"
            "Form is no longer accepting responses."
        )

    async def send_manual_intervention(self, reason: str) -> None:
        await self._send(
            "⚠️ <b>Silent Zone Registration</b>\n"
            "Status: MANUAL INTERVENTION REQUIRED\n"
            f"Reason: {reason}\n"
            "Please open the dashboard."
        )

