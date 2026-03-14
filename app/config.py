from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "HappyRobot Backend"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(default="sqlite:///./happyrobot.db", alias="DATABASE_URL")
    app_api_key: str = Field(alias="APP_API_KEY")
    fmcsa_api_key: str | None = Field(default=None, alias="FMCSA_API_KEY")
    fmcsa_base_url: str = Field(
        default="https://mobile.fmcsa.dot.gov/qc/services",
        alias="FMCSA_BASE_URL",
    )
    request_timeout_seconds: float = Field(default=10.0, alias="REQUEST_TIMEOUT_SECONDS")
    negotiation_max_counter_rounds: int = Field(default=3, alias="NEGOTIATION_MAX_COUNTER_ROUNDS", ge=1)
    dashboard_session_max_age_seconds: int = Field(
        default=14400,
        alias="DASHBOARD_SESSION_MAX_AGE_SECONDS",
        ge=300,
    )
    dashboard_session_cookie_name: str = Field(
        default="happyrobot_dashboard_session",
        alias="DASHBOARD_SESSION_COOKIE_NAME",
    )
    session_https_only: bool = Field(default=False, alias="SESSION_HTTPS_ONLY")


@lru_cache
def get_settings() -> Settings:
    return Settings()
