"""
Live integration test against the user's controlled Google Form.
Can be executed on demand:
    pytest tests/test_live_form.py -m live -v
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page

from app.automation.browser import BrowserManager, set_browser_manager
from app.automation.orchestrator import AutomationOrchestrator
from app.config import Settings, get_settings

LIVE_TEST_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScCaHWLIShewJ_UvawVMaRwEx8uossbaOWn_OrQV6upSn83Sw/viewform"
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_registration_orchestration():
    """Run the complete AutomationOrchestrator against the controlled live test form."""
    settings = get_settings()

    bm = BrowserManager(settings)
    await bm.start()
    set_browser_manager(bm)

    try:
        orchestrator = AutomationOrchestrator(settings)
        result = await orchestrator.run(form_url=LIVE_TEST_FORM_URL, attempt_id=101)
        assert result.success is True, f"Automation failed: {result.error}"
        assert result.seats_full is False
        assert result.manual_intervention is False
    finally:
        await bm.stop()

