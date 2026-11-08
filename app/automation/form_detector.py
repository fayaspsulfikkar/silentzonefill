"""
Form availability detector.
Validates URLs and determines whether a Google Form is open for responses.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from enum import Enum

from playwright.async_api import Page

logger = logging.getLogger(__name__)

_GOOGLE_FORMS_PATTERN = re.compile(
    r"^https?://(?:docs\.google\.com/forms/d/(?:e/)?[\w-]+/(?:viewform|formResponse)|forms\.gle/[\w-]+)",
    re.IGNORECASE,
)

# Precise phrases indicating a closed Google Form
_CLOSED_PHRASES = [
    "no longer accepting responses",
    "is no longer accepting responses",
    "this form is no longer accepting responses",
    "not accepting responses",
    "has reached its response limit",
    "response limit reached",
]

# Phrases indicating mandatory Google Account authentication or org restriction
_AUTH_PHRASES = [
    "you need permission",
    "you need access",
    "sign in to your google account to view this form",
    "this form can only be viewed by users in the owner's organization",
]


class FormAvailability(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


@dataclasses.dataclass
class DetectionResult:
    availability: FormAvailability
    page_title: str = ""
    detail: str = ""


def is_valid_google_forms_url(url: str) -> bool:
    """Return True if the URL matches a valid respondent Google Forms pattern."""
    if not url:
        return False
    clean = url.strip()
    # Reject editor links
    if "/edit" in clean:
        return False
    return bool(_GOOGLE_FORMS_PATTERN.match(clean))


async def detect_form_availability(page: Page, url: str) -> DetectionResult:
    """
    Navigate to the form URL and determine its availability status.
    Does NOT fill or submit anything.
    """
    logger.info("Detecting form availability: %s", url)
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
        if response and response.status >= 400:
            return DetectionResult(
                availability=FormAvailability.UNAVAILABLE,
                detail=f"HTTP status {response.status}",
            )
    except Exception as exc:
        return DetectionResult(
            availability=FormAvailability.UNAVAILABLE,
            detail=f"Navigation failed: {exc}",
        )

    # 1. Check if redirected to Google Accounts login
    current_url = page.url.lower()
    if "accounts.google.com" in current_url:
        return DetectionResult(
            availability=FormAvailability.AUTH_REQUIRED,
            page_title=await page.title(),
            detail="Redirected to accounts.google.com login",
        )

    page_text = (await page.inner_text("body")).lower()
    page_title = await page.title()

    # 2. Check for closed form phrases
    for phrase in _CLOSED_PHRASES:
        if phrase in page_text:
            return DetectionResult(
                availability=FormAvailability.CLOSED,
                page_title=page_title,
                detail=f"Form closed: matched '{phrase}'",
            )

    # 3. Check for mandatory auth / permission barrier
    for phrase in _AUTH_PHRASES:
        if phrase in page_text:
            return DetectionResult(
                availability=FormAvailability.AUTH_REQUIRED,
                page_title=page_title,
                detail=f"Auth required: matched '{phrase}'",
            )

    # 4. Check for active CAPTCHA challenges
    captcha_frames = page.locator("iframe[src*='recaptcha'], iframe[title*='reCAPTCHA']")
    if await captcha_frames.count() > 0:
        try:
            if await captcha_frames.first.is_visible():
                return DetectionResult(
                    availability=FormAvailability.CAPTCHA_REQUIRED,
                    page_title=page_title,
                    detail="reCAPTCHA challenge frame is visible",
                )
        except Exception:
            pass

    # 5. Positive signal: presence of questions or submit button
    submit_btn = page.get_by_role("button", name=re.compile(r"^submit$", re.IGNORECASE))
    questions = page.locator("[role='listitem']")
    if (await submit_btn.count() > 0) or (await questions.count() > 0):
        return DetectionResult(
            availability=FormAvailability.OPEN,
            page_title=page_title,
            detail="Form is open and accepting responses",
        )

    return DetectionResult(
        availability=FormAvailability.UNKNOWN,
        page_title=page_title,
        detail="Could not determine form state from page content",
    )
