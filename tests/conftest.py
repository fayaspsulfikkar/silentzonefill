"""
Pytest configuration and shared fixtures.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

# Point to a test-only SQLite DB and safe test credentials
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///./data/test_silentzone.db"
)
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-16chars")
os.environ.setdefault("WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("DASHBOARD_USERNAME", "admin")
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password")
os.environ.setdefault("REG_NAME", "Test User")
os.environ.setdefault("REG_PHONE", "0000000000")
os.environ.setdefault("REG_BATCH", "BCK-000")
os.environ.setdefault("BROWSER_HEADLESS", "true")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def browser() -> AsyncGenerator[Browser, None]:
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        yield b
        await b.close()


@pytest_asyncio.fixture(scope="function")
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    ctx = await browser.new_context()
    yield ctx
    await ctx.close()


@pytest_asyncio.fixture(scope="function")
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    p = await context.new_page()
    yield p
    await p.close()
