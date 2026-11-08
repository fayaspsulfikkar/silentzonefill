"""
Application configuration loaded from environment variables.
Uses Pydantic Settings for type-safe, validated config.
Personal information is loaded at runtime only — never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_PASSWORDS = {
    "change-me",
    "password",
    "admin",
    "123456",
    "12345678",
    "default",
    "",
}

INSECURE_SECRETS = {
    "change-me",
    "change-me-to-a-long-random-string",
    "change-me-to-another-long-random-string",
    "secret",
    "default",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment ---
    app_env: str = "production"

    # --- App ---
    app_secret_key: str = "change-me"
    webhook_secret: str = "change-me"

    # --- Registration (personal info from env) ---
    reg_name: str = ""
    reg_phone: str = ""
    reg_email: str = ""
    reg_batch: str = ""
    reg_rules_agreement: str = "YES"
    reg_coordinator: str = "NO"

    # --- Telegram ---
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # --- Dashboard ---
    dashboard_username: str = "admin"
    dashboard_password: str = "change-me"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/silentzone.db"

    # --- Playwright ---
    browser_headless: bool = True
    browser_timeout_ms: int = 30_000

    # --- Allowed Google Forms domains ---
    allowed_form_domains: str = "docs.google.com,forms.gle"

    def parsed_allowed_domains(self) -> list[str]:
        return [d.strip() for d in self.allowed_form_domains.split(",") if d.strip()]

    @model_validator(mode="after")
    def validate_production_credentials(self) -> Settings:
        env = (self.app_env or "production").strip().lower()
        if env in ("prod", "production"):
            pw = (self.dashboard_password or "").strip()
            if pw in INSECURE_PASSWORDS or len(pw) < 8:
                raise ValueError(
                    "Insecure DASHBOARD_PASSWORD: Default or weak password is not permitted in production (minimum 8 characters required)."
                )

            sec = (self.webhook_secret or "").strip()
            if sec in INSECURE_SECRETS or len(sec) < 16:
                raise ValueError(
                    "Insecure WEBHOOK_SECRET: Default or weak secret is not permitted in production (minimum 16 characters required)."
                )

            key = (self.app_secret_key or "").strip()
            if key in INSECURE_SECRETS or len(key) < 16:
                raise ValueError(
                    "Insecure APP_SECRET_KEY: Default or weak key is not permitted in production (minimum 16 characters required)."
                )

            if not (self.reg_name or "").strip():
                raise ValueError("REG_NAME is required in production.")
            if not (self.reg_phone or "").strip():
                raise ValueError("REG_PHONE is required in production.")
            if not (self.reg_batch or "").strip():
                raise ValueError("REG_BATCH is required in production.")

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
