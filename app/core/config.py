"""Application configuration, loaded from environment cariables or a .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Values in .env override the defaults below."""

    app_name: str = "Online Shop"
    environment: str = "development"
    # Local SQLite fallback so the app and CI still start without a .env file.
    # The real Neon URL comes from .env locally and from Secret Manager in the cloud.
    database_url: str = "sqlite:///./local.db"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()