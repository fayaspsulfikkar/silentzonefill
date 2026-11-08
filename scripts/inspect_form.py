"""
Form Inspector — Phase 2 tool.
Opens a Google Form and dumps its structure WITHOUT filling or submitting anything.
Run: python3 scripts/inspect_form.py <URL>
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime

from playwright.async_api import async_playwright

FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLScCaHWLIShewJ_UvawVMaRwEx8uossbaOWn_OrQV6upSn83Sw/viewform"
)


async def inspect(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        page = await context.new_page()

        print(f"Opening: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(2000)  # Let React hydrate

        # Screenshot
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        shot_path = f"screenshots/form_inspect_{ts}.png"
        await page.screenshot(path=shot_path, full_page=True)
        print(f"Screenshot: {shot_path}")

        # Page title
        title = await page.title()

        # ── Collect all text inputs ──────────────────────────────────────────
        inputs_info = []
        inputs = page.locator("input[type='text'], input[type='email'], textarea")
        for i in range(await inputs.count()):
            el = inputs.nth(i)
            aria_label = await el.get_attribute("aria-label") or ""
            placeholder = await el.get_attribute("placeholder") or ""
            name_attr = await el.get_attribute("name") or ""
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            inputs_info.append({
                "tag": tag,
                "aria_label": aria_label,
                "placeholder": placeholder,
                "name": name_attr,
            })

        # ── Collect all radio/checkbox elements ─────────────────────────────
        radios_info = []
        radios = page.locator("[role='radio'], input[type='radio']")
        for i in range(await radios.count()):
            el = radios.nth(i)
            aria_label = await el.get_attribute("aria-label") or ""
            aria_checked = await el.get_attribute("aria-checked") or ""
            value = await el.get_attribute("value") or ""
            inner_text = (await el.inner_text()).strip()
            radios_info.append({
                "aria_label": aria_label,
                "aria_checked": aria_checked,
                "value": value,
                "inner_text": inner_text,
            })

        # ── Collect listbox / dropdown elements ─────────────────────────────
        listboxes_info = []
        listboxes = page.locator("[role='listbox'], select")
        for i in range(await listboxes.count()):
            el = listboxes.nth(i)
            aria_label = await el.get_attribute("aria-label") or ""
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            inner_text = (await el.inner_text()).strip()[:200]
            listboxes_info.append({
                "tag": tag,
                "aria_label": aria_label,
                "inner_text": inner_text,
            })

        # ── Collect question headings (Google Forms uses div.M7eMe or similar) ──
        question_texts = []
        heading_selectors = [
            "div[role='heading']",
            ".freebirdFormviewerComponentsQuestionBaseTitle",
            # More generic: grab all text in listitem containers
        ]
        for sel in heading_selectors:
            els = page.locator(sel)
            for i in range(await els.count()):
                txt = (await els.nth(i).inner_text()).strip()
                if txt:
                    question_texts.append(txt)

        # ── All listitem text (question containers) ─────────────────────────
        listitems_text = []
        listitems = page.locator("[role='listitem']")
        for i in range(await listitems.count()):
            txt = (await listitems.nth(i).inner_text()).strip()[:300]
            if txt:
                listitems_text.append(txt)

        # ── Submit buttons ───────────────────────────────────────────────────
        submit_btns = []
        btns = page.locator("[role='button'], button")
        for i in range(await btns.count()):
            el = btns.nth(i)
            aria_label = await el.get_attribute("aria-label") or ""
            inner = (await el.inner_text()).strip()
            if inner or aria_label:
                submit_btns.append({"aria_label": aria_label, "inner_text": inner})

        # ── Full body text (abbreviated) ─────────────────────────────────────
        body_text = (await page.inner_text("body"))[:3000]

        await context.close()
        await browser.close()

        return {
            "url": url,
            "title": title,
            "text_inputs": inputs_info,
            "radio_elements": radios_info,
            "listboxes": listboxes_info,
            "question_headings": question_texts,
            "listitem_texts": listitems_text,
            "buttons": submit_btns,
            "body_text_preview": body_text,
        }


async def main():
    url = sys.argv[1] if len(sys.argv) > 1 else FORM_URL
    result = await inspect(url)

    print("\n" + "=" * 60)
    print(f"TITLE: {result['title']}")
    print("=" * 60)

    print("\n── TEXT INPUTS ──")
    for inp in result["text_inputs"]:
        print(f"  <{inp['tag']}> aria-label={inp['aria_label']!r}  placeholder={inp['placeholder']!r}")

    print("\n── RADIO ELEMENTS ──")
    for r in result["radio_elements"]:
        print(f"  aria-label={r['aria_label']!r}  value={r['value']!r}  text={r['inner_text']!r}")

    print("\n── LISTBOXES/DROPDOWNS ──")
    for lb in result["listboxes"]:
        print(f"  <{lb['tag']}> aria-label={lb['aria_label']!r}")
        print(f"    text: {lb['inner_text']!r}")

    print("\n── QUESTION HEADINGS ──")
    for q in result["question_headings"]:
        print(f"  {q!r}")

    print("\n── LISTITEM CONTAINERS (question blocks) ──")
    for i, t in enumerate(result["listitem_texts"]):
        print(f"  [{i}] {t[:120]!r}")

    print("\n── BUTTONS ──")
    for b in result["buttons"]:
        print(f"  aria-label={b['aria_label']!r}  text={b['inner_text']!r}")

    print("\n── BODY TEXT PREVIEW ──")
    print(result["body_text_preview"][:1000])

    # Save full JSON
    out_path = "screenshots/form_inspect_result.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nFull JSON saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

