"""
Web Dashboard route (Phase 6).
Renders the registration overview dashboard using Jinja2 templates.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select

from app.database.database import get_session
from app.database.models import RegistrationAttempt
from app.dependencies import require_dashboard_auth

router = APIRouter(tags=["dashboard"])

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TEMPLATES_DIR = os.path.join(_BASE_DIR, "dashboard", "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_dashboard_auth)])
async def dashboard_index(request: Request):
    """Render the web dashboard showing registration attempts and manual trigger."""
    async with get_session() as session:
        result = await session.execute(
            select(RegistrationAttempt)
            .order_by(RegistrationAttempt.created_at.desc())
            .limit(20)
        )
        attempts = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"attempts": attempts},
    )
