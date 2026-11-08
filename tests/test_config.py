"""
Tests for configuration validation, production credential enforcement, and health checks.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestConfigValidation:
    def test_production_rejects_default_dashboard_password(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                app_secret_key="a" * 24,
                webhook_secret="b" * 24,
                dashboard_password="change-me",
                reg_name="Valid Name",
                reg_phone="9876543210",
                reg_batch="BCK-100",
            )
        assert "Insecure DASHBOARD_PASSWORD" in str(exc_info.value)

    def test_production_rejects_short_dashboard_password(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                app_secret_key="a" * 24,
                webhook_secret="b" * 24,
                dashboard_password="short",
                reg_name="Valid Name",
                reg_phone="9876543210",
                reg_batch="BCK-100",
            )
        assert "Insecure DASHBOARD_PASSWORD" in str(exc_info.value)

    def test_production_rejects_default_webhook_secret(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                app_secret_key="a" * 24,
                webhook_secret="change-me-to-another-long-random-string",
                dashboard_password="secure-password-123",
                reg_name="Valid Name",
                reg_phone="9876543210",
                reg_batch="BCK-100",
            )
        assert "Insecure WEBHOOK_SECRET" in str(exc_info.value)

    def test_production_rejects_default_app_secret_key(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                app_secret_key="change-me-to-a-long-random-string",
                webhook_secret="b" * 24,
                dashboard_password="secure-password-123",
                reg_name="Valid Name",
                reg_phone="9876543210",
                reg_batch="BCK-100",
            )
        assert "Insecure APP_SECRET_KEY" in str(exc_info.value)

    def test_production_rejects_missing_registration_info(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                app_env="production",
                app_secret_key="a" * 24,
                webhook_secret="b" * 24,
                dashboard_password="secure-password-123",
                reg_name="",
                reg_phone="",
                reg_batch="",
            )
        assert "REG_NAME is required in production" in str(exc_info.value)

    def test_production_accepts_valid_config(self):
        s = Settings(
            app_env="production",
            app_secret_key="valid-secret-key-at-least-16-chars",
            webhook_secret="valid-webhook-secret-at-least-16-chars",
            dashboard_password="secure-password-123",
            reg_name="Valid Name",
            reg_phone="9876543210",
            reg_batch="BCK-100",
        )
        assert s.app_env == "production"
        assert s.reg_name == "Valid Name"

    def test_test_environment_allows_defaults(self):
        s = Settings(
            app_env="test",
            app_secret_key="test-key",
            webhook_secret="test-secret",
            dashboard_password="test",
            reg_name="",
            reg_phone="",
            reg_batch="",
        )
        assert s.app_env == "test"

