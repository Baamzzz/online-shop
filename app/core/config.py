"""Application configuration, loaded from environment cariables or a .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Values in .env override the defaults below."""

    app_name: str = "Online Shop"
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()