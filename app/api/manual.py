"""
POST /api/registration/manual
Allows manual form URL submission from the dashboard.
Supports both JSON API payloads and HTML form submissions.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.dependencies import require_dashboard_auth
from app.services.announcement import AnnouncementService

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/registration",
    tags=["registration"],
    dependencies=[Depends(require_dashboard_auth)],
)


class ManualSubmissionPayload(BaseModel):
    form_url: str = Field(..., description="Google Forms respondent URL")


@router.post("/manual", status_code=202)
async def manual_submission(
    request: Request,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    form_url: str | None = Form(None),
):
    """Submit a registration URL manually (dashboard fallback)."""
    target_url = form_url

    # Check if request was sent as JSON
    if not target_url:
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body = await request.json()
                target_url = body.get("form_url")
            except Exception:
                pass

    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: form_url",
        )

    svc = AnnouncementService(settings)
    result = await svc.process(
        app_package=None,
        group_name=None,
        message_text=target_url,
        form_url=target_url,
        timestamp=None,
        background_tasks=background_tasks,
        source="manual",
    )

    # If submitted from browser form, redirect back to dashboard
    accept_header = request.headers.get("accept", "")
    if "text/html" in accept_header and form_url is not None:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    return JSONResponse(content=result, status_code=status.HTTP_202_ACCEPTED)
