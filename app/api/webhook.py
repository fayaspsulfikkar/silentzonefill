"""
POST /api/registration/announcement
Receives WhatsApp notification data forwarded by Tasker on Android.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.announcement import AnnouncementService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/registration", tags=["registration"])


class AnnouncementPayload(BaseModel):
    """Payload sent by Tasker from the Android device."""

    app_package: str | None = Field(
        None, description="Source app package, e.g. com.whatsapp"
    )
    group_name: str | None = Field(
        None, description="WhatsApp group name if available"
    )
    message_text: str = Field(..., description="Raw notification message text")
    form_url: str | None = Field(
        None, description="Pre-extracted Google Forms URL (optional)"
    )
    timestamp: str | None = Field(
        None, description="ISO 8601 message timestamp from device"
    )


def _verify_webhook_secret(
    x_webhook_secret: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate the shared webhook secret token."""
    if not x_webhook_secret or x_webhook_secret != settings.webhook_secret:
        logger.warning("Rejected webhook request: invalid or missing secret token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret",
        )


@router.post(
    "/announcement",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(_verify_webhook_secret)],
)
async def receive_announcement(
    payload: AnnouncementPayload,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Accept a WhatsApp announcement notification from the Android device.
    Validates the source, extracts the form URL, and schedules automation.
    """
    svc = AnnouncementService(settings)
    return await svc.process(
        app_package=payload.app_package,
        group_name=payload.group_name,
        message_text=payload.message_text,
        form_url=payload.form_url,
        timestamp=payload.timestamp,
        background_tasks=background_tasks,
    )

