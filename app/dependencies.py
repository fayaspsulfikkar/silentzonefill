"""
FastAPI shared dependencies: authentication helpers.
"""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import Settings, get_settings

_basic_security = HTTPBasic()


def require_dashboard_auth(
    credentials: HTTPBasicCredentials = Depends(_basic_security),
    settings: Settings = Depends(get_settings),
) -> str:
    """HTTP Basic Auth guard for dashboard and status endpoints."""
    username_ok = secrets.compare_digest(
        credentials.username.encode(), settings.dashboard_username.encode()
    )
    password_ok = secrets.compare_digest(
        credentials.password.encode(), settings.dashboard_password.encode()
    )
    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

