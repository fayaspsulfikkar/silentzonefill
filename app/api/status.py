"""
GET /api/registration/status   — list recent attempts
GET /api/registration/{id}     — single attempt detail
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database.database import get_session
from app.database.models import RegistrationAttempt
from app.dependencies import require_dashboard_auth

router = APIRouter(
    prefix="/api/registration",
    tags=["registration"],
    dependencies=[Depends(require_dashboard_auth)],
)


@router.get("/status")
async def list_attempts(limit: int = 20) -> list[dict]:
    """Return the most recent registration attempts."""
    async with get_session() as session:
        result = await session.execute(
            select(RegistrationAttempt)
            .order_by(RegistrationAttempt.created_at.desc())
            .limit(limit)
        )
        attempts = result.scalars().all()
    return [_serialize(a) for a in attempts]


@router.get("/{attempt_id}")
async def get_attempt(attempt_id: int) -> dict:
    """Return a single registration attempt by ID."""
    async with get_session() as session:
        attempt = await session.get(RegistrationAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _serialize(attempt)


def _serialize(a: RegistrationAttempt) -> dict:
    return {
        "id": a.id,
        "status": a.status,
        "form_url_hash": a.form_url_hash[:12] + "...",
        "announcement_source": a.announcement_source,
        "announced_at": a.announced_at.isoformat() if a.announced_at else None,
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "processing_duration_ms": a.processing_duration_ms,
        "error_detail": a.error_detail,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }

