from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.services.fmcsa import FMCSAClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_db_session(db: Session = Depends(get_db)) -> Session:
    return db


def get_app_settings(settings: Settings = Depends(get_settings)) -> Settings:
    return settings


def require_api_key(
    provided_key: str | None = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> str:
    if provided_key != settings.app_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
    return provided_key


def get_fmcsa_client(settings: Settings = Depends(get_settings)) -> FMCSAClient:
    return FMCSAClient(settings=settings)
