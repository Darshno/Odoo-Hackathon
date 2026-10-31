import json
import secrets
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Brightloop Subscription Management System"
    environment: str = "development"
    secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite:///./brightloop.db"
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    reset_token_expire_minutes: int = 30
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@brightloop.local"
    reset_preview_enabled: bool = True
    frontend_url: str = "http://localhost:3000"
    bootstrap_admin_name: str | None = None
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            if value.lstrip().startswith("["):
                parsed = json.loads(value)
                if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                    raise ValueError("CORS_ORIGINS must be a comma-separated string or JSON array of strings.")
                return [item.strip() for item in parsed if item.strip()]
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("database_url", mode="after")
    @classmethod
    def normalize_database_driver(cls, value: str) -> str:
        if value.startswith("mysql://"):
            return value.replace("mysql://", "mysql+pymysql://", 1)
        return value

    @model_validator(mode="after")
    def validate_runtime_configuration(self):
        if not self.secret_key:
            if self.environment not in {"development", "test"}:
                raise ValueError("SECRET_KEY must be configured outside development and test environments.")
            self.secret_key = secrets.token_urlsafe(32)
        if self.environment in {"production", "staging"} and self.database_url.startswith("sqlite"):
            raise ValueError("DATABASE_URL must point to a server database outside development and test environments.")
        if self.environment != "development" and self.reset_preview_enabled:
            raise ValueError("RESET_PREVIEW_ENABLED must be false outside development.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
