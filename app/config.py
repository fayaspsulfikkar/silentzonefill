"""
Application configuration loaded from environment variables.
Uses Pydantic Settings for type-safe, validated config.
Personal information is loaded at runtime only — never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()

