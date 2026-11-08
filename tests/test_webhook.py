"""
Tests for FastAPI webhook and API endpoints (Phase 4 & Phase 6).
Tests secret token validation, payload parsing, deduplication, manual submission, and dashboard.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database.database import Base, engine
from app.main import create_app


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Drop and recreate all tables for a fresh test state."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_webhook_unauthorized_without_secret():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/registration/announcement",
            json={"message_text": "https://forms.gle/test1234"},
        )
        assert resp.status_code == 401
        assert "Invalid webhook secret" in resp.text


@pytest.mark.asyncio
async def test_webhook_unauthorized_with_wrong_secret():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "wrong-secret"},
            json={"message_text": "https://forms.gle/test1234"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_webhook_rejects_non_whatsapp_package():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "test-secret"},
            json={
                "app_package": "com.telegram.messenger",
                "message_text": "Silent Zone: https://forms.gle/valid123",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted"] is False
        assert data["reason"] == "not_whatsapp"


@pytest.mark.asyncio
async def test_webhook_ignores_message_without_url():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "test-secret"},
            json={
                "app_package": "com.whatsapp",
                "message_text": "Registration will happen tomorrow morning.",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted"] is False
        assert data["reason"] == "no_form_url"


@pytest.mark.asyncio
async def test_webhook_accepts_valid_announcement():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        url = "https://docs.google.com/forms/d/e/1FAIpQLSxyz999/viewform"
        resp = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "test-secret"},
            json={
                "app_package": "com.whatsapp",
                "message_text": f"Registration link: {url}",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["accepted"] is True
        assert "url_hash" in data


@pytest.mark.asyncio
async def test_webhook_rejects_duplicate_announcement():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        url = "https://docs.google.com/forms/d/e/1FAIpQLSduplicate123/viewform"
        resp1 = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "test-secret"},
            json={
                "app_package": "com.whatsapp",
                "message_text": f"First post: {url}",
            },
        )
        assert resp1.status_code == 202
        assert resp1.json()["accepted"] is True

        from app.database.database import get_session
        from app.database.models import RegistrationAttempt
        from app.services.announcement import AnnouncementService
        from sqlalchemy import select

        url_hash = AnnouncementService._hash_url(url)
        async with get_session() as session:
            res = await session.execute(
                select(RegistrationAttempt).where(
                    RegistrationAttempt.form_url_hash == url_hash
                )
            )
            if not res.scalar_one_or_none():
                attempt = RegistrationAttempt(
                    form_url=url,
                    form_url_hash=url_hash,
                    announcement_source="whatsapp",
                )
                session.add(attempt)

        resp2 = await client.post(
            "/api/registration/announcement",
            headers={"X-Webhook-Secret": "test-secret"},
            json={
                "app_package": "com.whatsapp",
                "message_text": f"Second post: {url}",
            },
        )
        assert resp2.status_code == 202
        data2 = resp2.json()
        assert data2["accepted"] is False
        assert data2["reason"] == "duplicate"


@pytest.mark.asyncio
async def test_manual_submission_endpoint():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        unauth_resp = await client.post(
            "/api/registration/manual",
            json={
                "form_url": "https://docs.google.com/forms/d/e/1FAIpQLSmanual1/viewform"
            },
        )
        assert unauth_resp.status_code == 401

        auth_resp = await client.post(
            "/api/registration/manual",
            auth=("admin", "test-password"),
            json={
                "form_url": "https://docs.google.com/forms/d/e/1FAIpQLSmanual1/viewform"
            },
        )
        assert auth_resp.status_code == 202
        data = auth_resp.json()
        assert data["accepted"] is True


@pytest.mark.asyncio
async def test_manual_submission_form_encoded_redirect():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/registration/manual",
            auth=("admin", "test-password"),
            data={
                "form_url": "https://docs.google.com/forms/d/e/1FAIpQLSformpost1/viewform"
            },
            headers={"Accept": "text/html"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"


@pytest.mark.asyncio
async def test_dashboard_ui_endpoint():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Unauthenticated -> 401
        unauth = await client.get("/")
        assert unauth.status_code == 401

        # Authenticated -> 200 HTML
        auth = await client.get("/", auth=("admin", "test-password"))
        assert auth.status_code == 200
        assert "text/html" in auth.headers["content-type"]
        assert "Silent Zone Registration Bot" in auth.text
        assert "Manual URL Submission" in auth.text


@pytest.mark.asyncio
async def test_health_check_endpoint():
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
