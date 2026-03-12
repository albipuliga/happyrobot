from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "HappyRobot Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./happyrobot.db"
    app_api_key: str = Field(default="development-api-key", alias="APP_API_KEY")
    fmcsa_api_key: str | None = Field(default=None, alias="FMCSA_API_KEY")
    fmcsa_base_url: str = Field(
        default="https://mobile.fmcsa.dot.gov/qc/services",
        alias="FMCSA_BASE_URL",
    )
    request_timeout_seconds: float = 10.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
