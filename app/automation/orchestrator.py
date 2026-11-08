"""
AutomationOrchestrator: coordinates the full registration flow end-to-end.
Owns screenshot capture on error.
"""

from __future__ import annotations

import dataclasses
import logging
import os
from datetime import datetime, timezone

from app.automation.browser import get_browser_manager
from app.automation.form_detector import (
    FormAvailability,
    detect_form_availability,
    is_valid_google_forms_url,
)
from app.automation.form_filler import FormFiller
from app.automation.form_submitter import submit_form
from app.config import Settings

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = "screenshots"


@dataclasses.dataclass
class AutomationResult:
    success: bool
    seats_full: bool = False
    manual_intervention: bool = False
    error: str | None = None
    screenshot_path: str | None = None


class AutomationOrchestrator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(self, *, form_url: str, attempt_id: int) -> AutomationResult:
        # --- URL validation ---
        if not is_valid_google_forms_url(form_url):
            return AutomationResult(
                success=False, error=f"Invalid Google Forms URL: {form_url}"
            )

        manager = get_browser_manager()
        context, page = await manager.new_page()
        screenshot_path: str | None = None

        try:
            # --- Form availability check ---
            detection = await detect_form_availability(page, form_url)
            logger.info(
                "Form availability: %s (%s)", detection.availability, detection.detail
            )

            if detection.availability == FormAvailability.CLOSED:
                return AutomationResult(
                    success=False, seats_full=True, error=detection.detail
                )

            if detection.availability in (
                FormAvailability.AUTH_REQUIRED,
                FormAvailability.CAPTCHA_REQUIRED,
            ):
                return AutomationResult(
                    success=False,
                    manual_intervention=True,
                    error=f"Human intervention needed: {detection.availability}",
                )

            if detection.availability == FormAvailability.UNAVAILABLE:
                screenshot_path = await self._screenshot(
                    page, attempt_id, "unavailable"
                )
                return AutomationResult(
                    success=False,
                    error=f"Form unavailable: {detection.detail}",
                    screenshot_path=screenshot_path,
                )

            # --- Fill form ---
            filler = FormFiller(self._settings)
            fill_result = await filler.fill(page)

            if not fill_result.success:
                screenshot_path = await self._screenshot(
                    page, attempt_id, "fill_failed"
                )
                return AutomationResult(
                    success=False,
                    error=fill_result.error,
                    screenshot_path=screenshot_path,
                )

            # --- Submit ---
            submission = await submit_form(page)

            if not submission.success:
                screenshot_path = await self._screenshot(
                    page, attempt_id, "submit_failed"
                )
                return AutomationResult(
                    success=False,
                    seats_full="no longer accepting" in (submission.error or ""),
                    error=submission.error,
                    screenshot_path=screenshot_path,
                )

            return AutomationResult(success=True)

        except Exception as exc:
            logger.exception("Unhandled error in orchestrator")
            screenshot_path = await self._screenshot(page, attempt_id, "exception")
            return AutomationResult(
                success=False,
                error=str(exc),
                screenshot_path=screenshot_path,
            )

        finally:
            await context.close()

    @staticmethod
    async def _screenshot(page, attempt_id: int, label: str) -> str | None:
        os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = os.path.join(SCREENSHOTS_DIR, f"attempt_{attempt_id}_{label}_{ts}.png")
        try:
            await page.screenshot(path=path, full_page=True)
            logger.info("Screenshot saved: %s", path)
            return path
        except Exception:
            logger.warning("Could not save screenshot")
            return None

