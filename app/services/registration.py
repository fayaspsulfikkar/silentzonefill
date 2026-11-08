"""
RegistrationService: owns the state machine and coordinates automation steps.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from app.config import Settings
from app.database.database import get_session
from app.database.models import RegistrationAttempt, RegistrationStatus

logger = logging.getLogger(__name__)


class RegistrationService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def run(
        self,
        *,
        form_url: str,
        form_url_hash: str,
        announcement_text: str,
        announcement_source: str,
        announced_at: datetime,
    ) -> None:
        from app.services.notifier import NotifierService
        from app.automation.orchestrator import AutomationOrchestrator

        notifier = NotifierService(self._settings)
        start_time = time.monotonic()

        # --- Create DB record ---
        attempt = await self._create_attempt(
            form_url=form_url,
            form_url_hash=form_url_hash,
            announcement_text=announcement_text,
            announcement_source=announcement_source,
            announced_at=announced_at,
        )

        await notifier.send_announcement_detected(form_url)

        try:
            orchestrator = AutomationOrchestrator(self._settings)
            result = await orchestrator.run(
                form_url=form_url, attempt_id=attempt.id
            )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if result.success:
                await self._update_status(
                    attempt.id,
                    status=RegistrationStatus.SUBMITTED,
                    submitted_at=datetime.now(tz=timezone.utc),
                    duration_ms=duration_ms,
                )
                await notifier.send_success()

            elif result.seats_full:
                await self._update_status(
                    attempt.id,
                    status=RegistrationStatus.SEATS_FULL,
                    duration_ms=duration_ms,
                )
                await notifier.send_seats_full()

            elif result.manual_intervention:
                await self._update_status(
                    attempt.id,
                    status=RegistrationStatus.MANUAL_INTERVENTION_REQUIRED,
                    error_detail=result.error,
                    duration_ms=duration_ms,
                )
                await notifier.send_manual_intervention(result.error or "")

            else:
                await self._update_status(
                    attempt.id,
                    status=RegistrationStatus.FAILED,
                    error_detail=result.error,
                    screenshot_path=result.screenshot_path,
                    duration_ms=duration_ms,
                )
                await notifier.send_failure(result.error or "Unknown error")

        except Exception as exc:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Unhandled error in registration automation")
            await self._update_status(
                attempt.id,
                status=RegistrationStatus.FAILED,
                error_detail=str(exc),
                duration_ms=duration_ms,
            )
            await notifier.send_failure(str(exc))

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _create_attempt(self, **kwargs) -> RegistrationAttempt:
        async with get_session() as session:
            attempt = RegistrationAttempt(
                status=RegistrationStatus.ANNOUNCEMENT_DETECTED,
                processing_started_at=datetime.now(tz=timezone.utc),
                **kwargs,
            )
            session.add(attempt)
            await session.flush()
            await session.refresh(attempt)
            return attempt

    async def _update_status(
        self,
        attempt_id: int,
        *,
        status: RegistrationStatus,
        submitted_at: datetime | None = None,
        error_detail: str | None = None,
        screenshot_path: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        async with get_session() as session:
            attempt = await session.get(RegistrationAttempt, attempt_id)
            if attempt:
                attempt.status = status
                if submitted_at:
                    attempt.submitted_at = submitted_at
                if error_detail:
                    attempt.error_detail = error_detail
                if screenshot_path:
                    attempt.screenshot_path = screenshot_path
                if duration_ms is not None:
                    attempt.processing_duration_ms = duration_ms

