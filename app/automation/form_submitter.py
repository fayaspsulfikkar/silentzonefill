"""
Form submitter and confirmation verifier.

Rule: never claim success unless the confirmation page is detected.
Rule: never submit more than once.
"""

from __future__ import annotations

import dataclasses
import logging
import re

from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Google Forms confirmation page signals
_CONFIRMATION_PATTERNS = [
    "your response has been recorded",
    "thanks for your response",
    "thank you for your response",
    "response recorded",
    "submit another response",
    "submitted",
    "response has been recorded",
]


@dataclasses.dataclass
class SubmissionResult:
    success: bool
    confirmed: bool = False
    error: str | None = None


async def submit_form(page: Page) -> SubmissionResult:
    """
    Click the Submit button and wait for the confirmation page.
    Returns SubmissionResult.
    """
    # Locate Submit button — exact match first
    submit_locator = page.get_by_role("button", name=re.compile(r"^submit$", re.IGNORECASE))
    if await submit_locator.count() == 0:
        # Fallback: [role="button"] with text or aria-label containing submit
        submit_locator = page.locator("[role='button']:has-text('Submit'), button:has-text('Submit')")

    if await submit_locator.count() == 0:
        return SubmissionResult(success=False, error="Submit button not found on page")

    logger.info("Found Submit button. Clicking...")
    try:
        await submit_locator.first.scroll_into_view_if_needed()
        await submit_locator.first.click()
    except Exception as exc:
        return SubmissionResult(success=False, error=f"Failed to click Submit: {exc}")

    return await _verify_confirmation(page)


async def _verify_confirmation(page: Page) -> SubmissionResult:
    """
    Wait for the confirmation page and verify its content.
    Never relies on the click alone.
    """
    try:
        # Wait up to 10 seconds for navigation or page update
        await page.wait_for_timeout(2000)
        await page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except Exception:
        pass

    page_text = (await page.inner_text("body")).lower()

    # 1. Success confirmation
    for pattern in _CONFIRMATION_PATTERNS:
        if pattern in page_text:
            logger.info("Confirmation verified with pattern: '%s'", pattern)
            return SubmissionResult(success=True, confirmed=True)

    # 2. Check if the URL changed to formResponse
    if "formresponse" in page.url.lower():
        logger.info("Confirmation verified by response URL: %s", page.url)
        return SubmissionResult(success=True, confirmed=True)

    # 3. Check if form closed in the interim
    if "no longer accepting" in page_text or "not accepting" in page_text:
        return SubmissionResult(
            success=False,
            confirmed=False,
            error="Form stopped accepting responses just before submission",
        )

    # 4. Check for form validation error alerts
    alerts = page.locator("[role='alert'], .freebirdFormviewerViewResponseError")
    alert_count = await alerts.count()
    if alert_count > 0:
        alert_texts = [await alerts.nth(i).inner_text() for i in range(alert_count)]
        joined_alerts = "; ".join(t.strip() for t in alert_texts if t.strip())
        logger.warning("Form validation errors prevented submit: %s", joined_alerts)
        return SubmissionResult(
            success=False,
            confirmed=False,
            error=f"Form validation errors: {joined_alerts}",
        )

    return SubmissionResult(
        success=False,
        confirmed=False,
        error="Confirmation page not detected after submit click",
    )
