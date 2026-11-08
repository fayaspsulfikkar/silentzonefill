"""
AnnouncementService: validates incoming notifications, extracts Google Forms URLs,
deduplicates, and dispatches the automation workflow.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone

from fastapi import BackgroundTasks

from app.config import Settings

logger = logging.getLogger(__name__)

# Regex for Google Forms URLs (respondent-facing and shortened)
_FORMS_URL_RE = re.compile(
    r"https?://(?:docs\.google\.com/forms/d/e/[\w-]+/viewform[\w?=&]*"
    r"|forms\.gle/[\w-]+)",
    re.IGNORECASE,
)

# WhatsApp app packages on Android
_WHATSAPP_PACKAGES = {
    "com.whatsapp",
    "com.whatsapp.w4b",  # WhatsApp Business
}


class AnnouncementService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def process(
        self,
        *,
        app_package: str | None,
        group_name: str | None,
        message_text: str,
        form_url: str | None,
        timestamp: str | None,
        background_tasks: BackgroundTasks,
        source: str = "whatsapp",
    ) -> dict:
        # 1. Source filter (skip if not WhatsApp and not manual)
        if source != "manual" and not self._is_whatsapp(app_package):
            logger.info(
                "Ignored notification: source is not WhatsApp (%s)", app_package
            )
            return {"accepted": False, "reason": "not_whatsapp"}

        # 2. Extract form URL
        extracted_url = form_url or self._extract_url(message_text)
        if not extracted_url:
            logger.info("Ignored notification: no Google Forms URL found in message")
            return {"accepted": False, "reason": "no_form_url"}

        # 3. Validate URL domain
        if not self._is_allowed_url(extracted_url):
            logger.warning(
                "Rejected URL — not an allowed Google Forms domain: %s", extracted_url
            )
            return {"accepted": False, "reason": "invalid_url_domain"}

        # 4. Convert /edit URL to viewform if needed
        extracted_url = self._normalize_url(extracted_url)

        # 5. Idempotency check (hash-based dedup)
        url_hash = self._hash_url(extracted_url)
        if await self._is_duplicate(url_hash):
            logger.info(
                "Duplicate announcement for URL hash %s — ignoring", url_hash[:8]
            )
            return {"accepted": False, "reason": "duplicate"}

        # 6. Parse announcement timestamp
        announced_at = self._parse_timestamp(timestamp)

        # 7. Dispatch automation in background
        logger.info(
            "Accepted form URL (hash=%s). Scheduling automation.", url_hash[:8]
        )
        background_tasks.add_task(
            self._run_automation,
            url=extracted_url,
            url_hash=url_hash,
            message_text=message_text,
            source=source,
            announced_at=announced_at,
        )

        return {"accepted": True, "url_hash": url_hash[:12], "source": source}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_whatsapp(self, package: str | None) -> bool:
        if package is None:
            return True  # Allow if package not provided (older Tasker setups)
        return package in _WHATSAPP_PACKAGES

    def _extract_url(self, text: str) -> str | None:
        match = _FORMS_URL_RE.search(text)
        return match.group(0) if match else None

    def _is_allowed_url(self, url: str) -> bool:
        allowed = self._settings.parsed_allowed_domains()
        return any(domain in url for domain in allowed)

    def _normalize_url(self, url: str) -> str:
        """Replace /edit suffix with /viewform so we always use the respondent URL."""
        if url.endswith("/edit"):
            normalized = url[: -len("/edit")] + "/viewform"
            logger.warning("Editor URL detected and normalized to: %s", normalized)
            return normalized
        return url

    @staticmethod
    def _hash_url(url: str) -> str:
        # Strip query params and trailing slashes for stable dedup key
        normalized = url.strip().lower().split("?")[0].rstrip("/")
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def _is_duplicate(self, url_hash: str) -> bool:
        """Check DB for a prior attempt with this URL hash."""
        from app.database.database import get_session
        from app.database.models import RegistrationAttempt
        from sqlalchemy import select

        async with get_session() as session:
            result = await session.execute(
                select(RegistrationAttempt).where(
                    RegistrationAttempt.form_url_hash == url_hash
                )
            )
            return result.scalar_one_or_none() is not None

    @staticmethod
    def _parse_timestamp(ts: str | None) -> datetime:
        if not ts:
            return datetime.now(tz=timezone.utc)
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            return datetime.now(tz=timezone.utc)

    async def _run_automation(
        self,
        *,
        url: str,
        url_hash: str,
        message_text: str,
        source: str,
        announced_at: datetime,
    ) -> None:
        """Entry point for the background automation task."""
        from app.services.registration import RegistrationService

        svc = RegistrationService(self._settings)
        await svc.run(
            form_url=url,
            form_url_hash=url_hash,
            announcement_text=message_text[:500],  # Truncate; never store full conv
            announcement_source=source,
            announced_at=announced_at,
        )

