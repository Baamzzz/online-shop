"""Application configuration, loaded from environment cariables or a .env file."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "dev-only-insecure-secret-change-me"

class Settings(BaseSettings):
    """Central settings object. Values in .env override the defaults below."""

    app_name: str = "Online Shop"
    environment: str = "development"
    # Local SQLite fallback so the app and CI still start without a .env file.
    # The real Neon URL comes from .env locally and from Secret Manager in the cloud.
    database_url: str = "sqlite:///./local.db"

    # Auth Settings
    jwt_secret_key: str = DEFAULT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # Secure cookies are only sent over HTTPS: off locally, on in production
    cookie_secure: bool = False

    model_config = SettingsConfigDict(env_file=".env")

    @model_validator(mode="after")
    def refuse_default_secret_in_production(self) -> "Settings":
        """Fail fast rather than run in production with a guessable signing key."""
        if self.environment == "production" and self.jwt_secret_key == DEFAULT_SECRET:
            raise ValueError("JWT_SECRET_KEY must be set in production")
        return self


settings = Settings()