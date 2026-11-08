"""
Test Telegram Bot integration.

Usage:
    .venv/bin/python3 scripts/test_telegram.py
"""

from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.services.notifier import NotifierService


async def test_telegram():
    settings = get_settings()

    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        print("[!] Telegram is not configured in .env yet.")
        print("    Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env first.")
        print("\nQuick setup:")
        print("  1. Search @BotFather on Telegram -> /newbot -> get token")
        print("  2. Search @userinfobot on Telegram -> /start -> get chat ID")
        print("  3. Add both to .env")
        sys.exit(1)

    print(f"[*] Testing Telegram with Chat ID: {settings.TELEGRAM_CHAT_ID}...")
    notifier = NotifierService(settings)

    await notifier._send(
        "🤖 <b>Silent Zone Automation Test</b>\n\n"
        "Your Telegram alert connection is working perfectly!\n"
        "You will receive instant alerts here whenever a registration is submitted."
    )
    print("[✓] Test message sent successfully! Check your Telegram app.")


if __name__ == "__main__":
    asyncio.run(test_telegram())

