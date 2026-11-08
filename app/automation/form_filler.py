"""
Form filler: identifies Google Form questions and fills them using configured answers.

Architecture:
  Primary: Container-scoped identification ([role="listitem"]).
           Scopes inputs, radios, and custom dropdowns to their specific question header.
           Prevents cross-field collision (e.g. two separate YES/NO radio questions).
  Fallback: Page-wide ARIA roles and labels if listitems are not found.

Verification:
  Checks that every required field was populated before returning.
"""

from __future__ import annotations

import dataclasses
import logging
import re

from playwright.async_api import Locator, Page

from app.config import Settings

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class FillResult:
    success: bool
    filled_fields: list[str] = dataclasses.field(default_factory=list)
    missing_fields: list[str] = dataclasses.field(default_factory=list)
    error: str | None = None


class FormFiller:
    """Fills a Google Form with the preconfigured registration answers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def fill(self, page: Page) -> FillResult:
        """
        Attempt to identify and fill all required registration fields.
        Returns FillResult indicating success, filled fields, and any missing fields.
        """
        result = FillResult(success=False)

        try:
            # Let the page settle
            await page.wait_for_timeout(1000)

            listitems = page.locator("[role='listitem']")
            item_count = await listitems.count()

            if item_count > 0:
                logger.info(
                    "Found %d question containers ([role='listitem']). Using container-scoped filler.",
                    item_count,
                )
                await self._fill_by_containers(page, listitems, item_count, result)
            else:
                logger.info(
                    "No [role='listitem'] containers found. Using fallback page-wide filler."
                )
                await self._fill_page_wide_fallback(page, result)

        except Exception as exc:
            result.error = f"Exception during form filling: {exc}"
            logger.exception("Error during form filling")
            return result

        # Required fields check
        required_fields = ["name", "phone", "batch", "rules_agreement", "coordinator"]
        for req in required_fields:
            if req not in result.filled_fields:
                result.missing_fields.append(req)

        if result.missing_fields:
            result.error = f"Missing required fields: {', '.join(result.missing_fields)}"
            result.success = False
            return result

        result.success = True
        logger.info("Successfully filled all fields: %s", result.filled_fields)
        return result

    # ------------------------------------------------------------------
    # Container-scoped filling (Google Forms primary strategy)
    # ------------------------------------------------------------------

    async def _fill_by_containers(
        self,
        page: Page,
        listitems: Locator,
        count: int,
        result: FillResult,
    ) -> None:
        """Iterate through each question container and match question to answer."""
        for i in range(count):
            item = listitems.nth(i)
            header_text = await self._get_question_heading(item)
            header_lower = header_text.lower()
            logger.debug("Inspecting question container [%d]: %s", i, header_text)

            # 1. Email (if present on form)
            if self._matches_email(header_lower):
                email_val = self._settings.reg_email or "registered.user@gmail.com"
                if await self._fill_text_input(item, email_val):
                    result.filled_fields.append("email")
                continue

            # 2. Coordinator (check before generic yes/no or name)
            if self._matches_coordinator(header_lower):
                ans = self._settings.reg_coordinator.upper()
                if await self._fill_radio_in_container(item, ans):
                    result.filled_fields.append("coordinator")
                continue

            # 3. Rules agreement
            if self._matches_rules(header_lower):
                ans = self._settings.reg_rules_agreement.upper()
                if await self._fill_radio_in_container(item, ans):
                    result.filled_fields.append("rules_agreement")
                continue

            # 4. Batch
            if self._matches_batch(header_lower):
                batch_val = self._settings.reg_batch
                if await self._fill_dropdown_or_radio(page, item, batch_val):
                    result.filled_fields.append("batch")
                continue

            # 5. Phone number
            if self._matches_phone(header_lower):
                phone_val = self._settings.reg_phone
                if await self._fill_text_input(item, phone_val):
                    result.filled_fields.append("phone")
                continue

            # 6. Name
            if self._matches_name(header_lower):
                name_val = self._settings.reg_name
                if await self._fill_text_input(item, name_val):
                    result.filled_fields.append("name")
                continue

    # ------------------------------------------------------------------
    # Question Header Matching
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_question_heading(item: Locator) -> str:
        """Extract the question title from within the container."""
        for sel in ["[role='heading']", ".M7eMe", "div[dir='auto']"]:
            heading = item.locator(sel).first
            if await heading.count() > 0:
                text = (await heading.inner_text()).strip()
                if text:
                    return text
        raw = await item.inner_text()
        return raw.split("\n")[0].strip()

    @staticmethod
    def _matches_name(text: str) -> bool:
        if "coordinator" in text or "silent zone" in text:
            return False
        return bool(
            re.search(r"\bname\b|full\s*name|student\s*name|applicant\s*name", text, re.I)
        )

    @staticmethod
    def _matches_phone(text: str) -> bool:
        return bool(re.search(r"phone|mobile|contact|whatsapp", text, re.I))

    @staticmethod
    def _matches_email(text: str) -> bool:
        return bool(re.search(r"\bemail\b|e-mail", text, re.I))

    @staticmethod
    def _matches_batch(text: str) -> bool:
        return bool(re.search(r"\bbatch\b", text, re.I))

    @staticmethod
    def _matches_rules(text: str) -> bool:
        return bool(re.search(r"rules|silent\s*zone|guidelines|agree", text, re.I))

    @staticmethod
    def _matches_coordinator(text: str) -> bool:
        return bool(re.search(r"coordinator|co-ordinator", text, re.I))

    # ------------------------------------------------------------------
    # Form Input Helpers
    # ------------------------------------------------------------------

    async def _fill_text_input(self, container: Locator, value: str) -> bool:
        """Find and fill a text or email input inside container."""
        inputs = container.locator(
            "input[type='text'], input[type='email'], input:not([type]), textarea"
        )
        if await inputs.count() > 0:
            inp = inputs.first
            await inp.click()
            await inp.fill(value)
            val = await inp.input_value()
            if val == value:
                return True
        return False

    async def _fill_radio_in_container(self, container: Locator, value: str) -> bool:
        """Select a radio option within a specific question container."""
        # Check actual [role='radio'] elements only
        radios = container.locator("[role='radio']")
        r_count = await radios.count()
        for i in range(r_count):
            r = radios.nth(i)
            aria_label = (await r.get_attribute("aria-label") or "").strip().upper()
            data_val = (await r.get_attribute("data-value") or "").strip().upper()
            if aria_label == value or data_val == value:
                await r.click(timeout=3000)
                await container.page.wait_for_timeout(200)
                logger.info("Selected radio matching '%s'", value)
                return True

        # Fallback: radio with parent/sibling container text matching value
        for i in range(r_count):
            r = radios.nth(i)
            parent_text = (await r.locator("..").inner_text()).strip().upper()
            if value in parent_text:
                await r.click(timeout=3000)
                await container.page.wait_for_timeout(200)
                logger.info("Selected radio by parent text '%s'", value)
                return True

        return False

    async def _fill_dropdown_or_radio(
        self, page: Page, container: Locator, value: str
    ) -> bool:
        """Handle dropdown (Google Forms custom listbox) or radio group for Batch."""
        # 1. Custom Google Forms dropdown trigger
        listbox = container.locator("[role='listbox'], [role='combobox']")
        if await listbox.count() > 0:
            logger.debug("Opening dropdown trigger for Batch...")
            try:
                await listbox.first.click(timeout=3000)
            except Exception:
                pass
            await page.wait_for_timeout(400)

            # Look for the visible option in the popup
            visible_options = page.locator("[role='option']:visible")
            v_count = await visible_options.count()
            for i in range(v_count):
                opt = visible_options.nth(i)
                opt_text = (await opt.inner_text()).strip()
                if value.lower() in opt_text.lower():
                    await opt.scroll_into_view_if_needed()
                    await opt.click(timeout=3000)
                    await page.wait_for_timeout(400)
                    logger.info("Selected batch option '%s'", opt_text)
                    return True

        # 2. Standard HTML <select> element
        select = container.locator("select")
        if await select.count() > 0:
            await select.first.select_option(label=re.compile(value, re.IGNORECASE))
            return True

        # 3. Radio buttons (if batch was configured as radio options instead of dropdown)
        if await self._fill_radio_in_container(container, value):
            return True

        return False

    # ------------------------------------------------------------------
    # Page-Wide Fallback (used only if [role='listitem'] is not present)
    # ------------------------------------------------------------------

    async def _fill_page_wide_fallback(self, page: Page, result: FillResult) -> None:
        """Fallback to page-wide label search when containers are absent."""
        name_input = page.get_by_role("textbox", name=re.compile(r"name", re.I))
        if await name_input.count() > 0:
            await name_input.first.fill(self._settings.reg_name)
            result.filled_fields.append("name")

        phone_input = page.get_by_role(
            "textbox", name=re.compile(r"phone|mobile|contact", re.I)
        )
        if await phone_input.count() > 0:
            await phone_input.first.fill(self._settings.reg_phone)
            result.filled_fields.append("phone")

        batch_trigger = page.locator("[role='listbox']").first
        if await batch_trigger.count() > 0:
            await batch_trigger.click()
            await page.wait_for_timeout(400)
            opt = page.locator(
                f"[role='option']:visible:has-text('{self._settings.reg_batch}')"
            ).first
            if await opt.count() > 0:
                await opt.click()
                result.filled_fields.append("batch")
