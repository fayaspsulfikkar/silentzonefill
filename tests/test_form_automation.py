"""
Comprehensive tests for Playwright form automation (Phase 2 & Phase 3).
Tests field detection, filling, missing fields, invalid dropdown options,
closed forms, and submission confirmation using controlled HTML mocks and route interception.
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page

from app.automation.form_detector import (
    FormAvailability,
    detect_form_availability,
    is_valid_google_forms_url,
)
from app.automation.form_filler import FormFiller
from app.automation.form_submitter import submit_form
from app.config import Settings

# Sample mock HTML representing Google Forms structure
MOCK_GOOGLE_FORM_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Registration Form</title></head>
<body>
  <div role="list">
    <div role="listitem">
      <div role="heading">Name</div>
      <input type="text" aria-label="Your answer" />
    </div>
    <div role="listitem">
      <div role="heading">Phone Number</div>
      <input type="text" aria-label="Your answer" />
    </div>
    <div role="listitem">
      <div role="heading">Batch</div>
      <div role="listbox" aria-expanded="false">
        <div role="option" data-value="BCK-416">BCK-416</div>
        <div role="option" data-value="BCK-417">BCK-417</div>
      </div>
    </div>
    <div role="listitem">
      <div role="heading">Are you willing to follow the rules of Silent Zone?</div>
      <div role="radio" aria-label="YES">YES</div>
      <div role="radio" aria-label="NO">NO</div>
    </div>
    <div role="listitem">
      <div role="heading">Are you willing to be the coordinator?</div>
      <div role="radio" aria-label="YES">YES</div>
      <div role="radio" aria-label="NO">NO</div>
    </div>
  </div>
  <button type="submit" role="button">Submit</button>
</body>
</html>
"""

MOCK_CLOSED_FORM_HTML = """
<!DOCTYPE html>
<html>
<head><title>Closed Form</title></head>
<body>
  <h1>Test Registration Form</h1>
  <p>This form is no longer accepting responses.</p>
</body>
</html>
"""

MOCK_AUTH_REQUIRED_HTML = """
<!DOCTYPE html>
<html>
<head><title>Permission Required</title></head>
<body>
  <h1>You need permission</h1>
  <p>Sign in to your Google Account to view this form.</p>
</body>
</html>
"""


@pytest.fixture
def mock_settings():
    return Settings(
        reg_name="Test User",
        reg_phone="9876543210",
        reg_batch="BCK-416",
        reg_rules_agreement="YES",
        reg_coordinator="NO",
    )


class TestFormAvailabilityMock:
    @pytest.mark.asyncio
    async def test_detects_closed_form(self, page: Page):
        await page.route(
            "**/forms/**",
            lambda route: route.fulfill(
                body=MOCK_CLOSED_FORM_HTML,
                content_type="text/html",
                status=200,
            ),
        )
        result = await detect_form_availability(
            page, "https://docs.google.com/forms/d/e/test/viewform"
        )
        assert result.availability == FormAvailability.CLOSED

    @pytest.mark.asyncio
    async def test_detects_auth_required_form(self, page: Page):
        await page.route(
            "**/forms/**",
            lambda route: route.fulfill(
                body=MOCK_AUTH_REQUIRED_HTML,
                content_type="text/html",
                status=200,
            ),
        )
        result = await detect_form_availability(
            page, "https://docs.google.com/forms/d/e/test/viewform"
        )
        assert result.availability == FormAvailability.AUTH_REQUIRED

    @pytest.mark.asyncio
    async def test_detects_open_form(self, page: Page):
        await page.route(
            "**/forms/**",
            lambda route: route.fulfill(
                body=MOCK_GOOGLE_FORM_HTML,
                content_type="text/html",
                status=200,
            ),
        )
        result = await detect_form_availability(
            page, "https://docs.google.com/forms/d/e/test/viewform"
        )
        assert result.availability == FormAvailability.OPEN


class TestFormFillerMock:
    @pytest.mark.asyncio
    async def test_fills_all_fields_successfully(
        self, page: Page, mock_settings: Settings
    ):
        await page.set_content(MOCK_GOOGLE_FORM_HTML)
        filler = FormFiller(mock_settings)
        result = await filler.fill(page)
        assert result.success is True
        assert "name" in result.filled_fields
        assert "phone" in result.filled_fields
        assert "batch" in result.filled_fields
        assert "rules_agreement" in result.filled_fields
        assert "coordinator" in result.filled_fields
        assert len(result.missing_fields) == 0

    @pytest.mark.asyncio
    async def test_detects_missing_field(
        self, page: Page, mock_settings: Settings
    ):
        # Form missing the phone number question
        incomplete_html = """
        <div role="list">
          <div role="listitem">
            <div role="heading">Name</div>
            <input type="text" />
          </div>
          <div role="listitem">
            <div role="heading">Batch</div>
            <div role="listbox"><div role="option" data-value="BCK-416">BCK-416</div></div>
          </div>
          <div role="listitem">
            <div role="heading">Rules</div>
            <div role="radio" aria-label="YES">YES</div>
          </div>
          <div role="listitem">
            <div role="heading">Coordinator</div>
            <div role="radio" aria-label="NO">NO</div>
          </div>
        </div>
        """
        await page.set_content(incomplete_html)
        filler = FormFiller(mock_settings)
        result = await filler.fill(page)
        assert result.success is False
        assert "phone" in result.missing_fields
        assert "Missing required fields" in (result.error or "")

    @pytest.mark.asyncio
    async def test_incorrect_dropdown_option(
        self, page: Page, mock_settings: Settings
    ):
        # Form where batch options do not include the user's batch
        wrong_batch_html = """
        <div role="list">
          <div role="listitem">
            <div role="heading">Name</div>
            <input type="text" />
          </div>
          <div role="listitem">
            <div role="heading">Phone Number</div>
            <input type="text" />
          </div>
          <div role="listitem">
            <div role="heading">Batch</div>
            <div role="listbox">
              <div role="option" data-value="BCK-999">BCK-999</div>
            </div>
          </div>
          <div role="listitem">
            <div role="heading">Rules</div>
            <div role="radio" aria-label="YES">YES</div>
          </div>
          <div role="listitem">
            <div role="heading">Coordinator</div>
            <div role="radio" aria-label="NO">NO</div>
          </div>
        </div>
        """
        await page.set_content(wrong_batch_html)
        filler = FormFiller(mock_settings)
        result = await filler.fill(page)
        assert result.success is False
        assert "batch" in result.missing_fields


class TestFormSubmitterMock:
    @pytest.mark.asyncio
    async def test_confirms_submission(self, page: Page):
        form_page = """
        <!DOCTYPE html>
        <html>
        <body>
          <button id="sub" role="button">Submit</button>
          <script>
            document.getElementById('sub').onclick = function() {
              document.body.innerHTML = '<h1>Your response has been recorded.</h1>';
            };
          </script>
        </body>
        </html>
        """
        await page.set_content(form_page)
        result = await submit_form(page)
        assert result.success is True
        assert result.confirmed is True

    @pytest.mark.asyncio
    async def test_fails_when_no_confirmation(self, page: Page):
        dummy_page = """
        <!DOCTYPE html>
        <html>
        <body>
          <button role="button">Submit</button>
        </body>
        </html>
        """
        await page.set_content(dummy_page)
        result = await submit_form(page)
        assert result.success is False
        assert result.confirmed is False
        assert "Confirmation page not detected" in (result.error or "")
