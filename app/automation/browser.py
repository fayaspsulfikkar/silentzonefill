"""
Browser lifecycle manager.
Maintains a single pre-warmed Playwright Chromium instance for speed.
Opens a fresh page (tab) for each registration attempt.
"""

from __future__ import annotations

import logging

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.config import Settings

logger = logging.getLogger(__name__)


class BrowserManager:
    """Singleton browser manager. Call start() on app startup, stop() on shutdown."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        """Launch Chromium. Called once at application startup."""
        logger.info("Starting Playwright Chromium browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.browser_headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
            ],
        )
        logger.info("Browser ready.")

    async def stop(self) -> None:
        """Shut down browser. Called on app shutdown."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser stopped.")

    async def new_page(self) -> tuple[BrowserContext, Page]:
        """Open a fresh context + page for one registration attempt."""
        if not self._browser:
            raise RuntimeError("BrowserManager.start() has not been called")
        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        page = await context.new_page()
        page.set_default_timeout(self._settings.browser_timeout_ms)
        return context, page


# Module-level singleton (populated in main.py lifespan)
_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    if _manager is None:
        raise RuntimeError("BrowserManager not initialized")
    return _manager


def set_browser_manager(manager: BrowserManager) -> None:
    global _manager
    _manager = manager

