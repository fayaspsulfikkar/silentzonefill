"""
Tests for AnnouncementService: URL extraction, deduplication, source filtering.
"""

from __future__ import annotations

import pytest

from app.services.announcement import _FORMS_URL_RE


class TestUrlExtraction:
    def test_extracts_docs_google_com_viewform(self):
        text = (
            "Register here: "
            "https://docs.google.com/forms/d/e/1FAIpQLSexample/viewform"
        )
        m = _FORMS_URL_RE.search(text)
        assert m is not None
        assert "docs.google.com" in m.group(0)

    def test_extracts_forms_gle_url(self):
        text = "Silent Zone registration: https://forms.gle/abcXYZ123"
        m = _FORMS_URL_RE.search(text)
        assert m is not None
        assert "forms.gle" in m.group(0)

    def test_no_url_in_text(self):
        text = "Please join us for the Silent Zone session tomorrow."
        m = _FORMS_URL_RE.search(text)
        assert m is None

    def test_ignores_non_forms_url(self):
        text = "Visit https://www.google.com for more info."
        m = _FORMS_URL_RE.search(text)
        assert m is None

    def test_editor_url_not_matched(self):
        # /edit links must NOT match the viewform pattern
        text = "https://docs.google.com/forms/d/1abc/edit"
        m = _FORMS_URL_RE.search(text)
        assert m is None

    def test_url_with_query_params(self):
        text = (
            "https://docs.google.com/forms/d/e/1FAIpQLSexample/viewform"
            "?usp=sf_link"
        )
        m = _FORMS_URL_RE.search(text)
        assert m is not None

