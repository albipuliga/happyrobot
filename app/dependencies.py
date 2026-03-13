from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.config import Settings, get_settings
from app.services.fmcsa import FMCSAClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


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


def require_dashboard_session(request: Request) -> None:
    if request.session.get("dashboard_authenticated") is not True:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard authentication required.",
        )


def get_fmcsa_client(settings: Settings = Depends(get_settings)) -> FMCSAClient:
    return FMCSAClient(settings=settings)
