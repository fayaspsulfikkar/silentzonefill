"""
Tests for form_detector.py: URL validation logic.
"""

from __future__ import annotations

import pytest

from app.automation.form_detector import is_valid_google_forms_url


class TestUrlValidation:
    def test_valid_viewform_url(self):
        assert is_valid_google_forms_url(
            "https://docs.google.com/forms/d/e/1FAIpQLSexample/viewform"
        )

    def test_valid_forms_gle_url(self):
        assert is_valid_google_forms_url("https://forms.gle/abc123XYZ")

    def test_invalid_edit_url(self):
        assert not is_valid_google_forms_url(
            "https://docs.google.com/forms/d/1abc/edit"
        )

    def test_invalid_random_url(self):
        assert not is_valid_google_forms_url("https://example.com/form")

    def test_invalid_empty_string(self):
        assert not is_valid_google_forms_url("")

    def test_valid_viewform_with_query(self):
        assert is_valid_google_forms_url(
            "https://docs.google.com/forms/d/e/1FAIpQLSexample/viewform?usp=sf_link"
        )

