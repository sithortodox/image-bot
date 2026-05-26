from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_telegram_ids: str = Field(default="", alias="ADMIN_TELEGRAM_IDS")

    openrouter_api_key: str = Field(alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(alias="OPENROUTER_MODEL")
    openrouter_fallback_model: str = Field(alias="OPENROUTER_FALLBACK_MODEL")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_prompt: str = Field(
        default="Улучши это изображение, сохрани смысл. Верни результат как изображение.",
        alias="OPENROUTER_PROMPT",
    )
    openrouter_timeout_sec: int = Field(default=120, alias="OPENROUTER_TIMEOUT_SEC")

    max_image_size_mb: int = Field(default=10, alias="MAX_IMAGE_SIZE_MB")

    tbank_terminal_key: str = Field(alias="TBANK_TERMINAL_KEY")
    tbank_password: str = Field(alias="TBANK_PASSWORD")
    tbank_api_url: str = Field(
        default="https://securepay.tinkoff.ru/v2",
        alias="TBANK_API_URL",
    )
    tbank_notification_url: str = Field(alias="TBANK_NOTIFICATION_URL")
    tbank_success_url: str = Field(alias="TBANK_SUCCESS_URL")
    tbank_fail_url: str = Field(alias="TBANK_FAIL_URL")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/bot.db",
        alias="DATABASE_URL",
    )
    web_host: str = Field(default="0.0.0.0", alias="WEB_HOST")
    web_port: int = Field(default=8000, alias="WEB_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def admin_ids(self) -> set[int]:
        if not self.admin_telegram_ids.strip():
            return set()
        return {
            int(x.strip())
            for x in self.admin_telegram_ids.split(",")
            if x.strip().isdigit()
        }

    @property
    def max_image_size_bytes(self) -> int:
        return self.max_image_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
