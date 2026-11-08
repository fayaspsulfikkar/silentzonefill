"""
FastAPI application entry point.
Manages browser lifecycle and mounts all routers.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.automation.browser import BrowserManager, set_browser_manager
from app.config import get_settings
from app.database.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    settings = get_settings()

    # Ensure runtime directories
    os.makedirs("screenshots", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # Init database
    logger.info("Initializing database...")
    await init_db()

    # Start browser
    manager = BrowserManager(settings)
    await manager.start()
    set_browser_manager(manager)

    logger.info("Application startup complete.")
    yield

    # Shutdown
    await manager.stop()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Silent Zone Registration Automation",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )

    # Routers
    from app.api import dashboard, manual, status, webhook

    app.include_router(dashboard.router)
    app.include_router(webhook.router)
    app.include_router(manual.router)
    app.include_router(status.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()

