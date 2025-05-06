from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.lib.constants import PROJECT_ROOT


WORKING_DIRECTORY = Path(__file__).parent.absolute()


class Settings(BaseSettings):
    """Application settings."""

    # API Keys
    GEMINI_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
