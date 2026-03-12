from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.dependencies import get_db_session, get_fmcsa_client, require_api_key, require_dashboard_session
from app.schemas.calls import CallCompleteRequest, CallCompleteResponse
from app.schemas.dashboard import DashboardDataResponse, DashboardLoginRequest, DashboardLoginResponse
from app.schemas.carriers import VerifyCarrierRequest, VerifyCarrierResponse
from app.schemas.loads import LoadSearchRequest, LoadSearchResponse
from app.schemas.metrics import MetricsSummaryResponse
from app.schemas.negotiation import NegotiateRequest, NegotiateResponse
from app.services.calls import complete_call
from app.services.dashboard import build_dashboard_data
from app.services.fmcsa import FMCSAClient
from app.services.loads import search_loads
from app.services.metrics import build_metrics_summary
from app.services.negotiation import negotiate_rate

router = APIRouter()
api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_api_key)])
_DASHBOARD_INDEX = Path(__file__).resolve().parent.parent / "static" / "dashboard" / "index.html"
_DASHBOARD_LOGIN_INDEX = Path(__file__).resolve().parent.parent / "static" / "dashboard" / "login.html"


@api_router.post("/carriers/verify", response_model=VerifyCarrierResponse, tags=["carriers"])
def verify_carrier(
    payload: VerifyCarrierRequest,
    db: Session = Depends(get_db_session),
    fmcsa_client: FMCSAClient = Depends(get_fmcsa_client),
) -> VerifyCarrierResponse:
    result = fmcsa_client.verify_carrier(db=db, external_call_id=payload.external_call_id, mc_number=payload.mc_number)
    return VerifyCarrierResponse(**result)


@api_router.post("/loads/search", response_model=LoadSearchResponse, tags=["loads"])
def search_for_loads(
    payload: LoadSearchRequest,
    db: Session = Depends(get_db_session),
) -> LoadSearchResponse:
    return search_loads(db=db, payload=payload)


@api_router.post("/loads/negotiate", response_model=NegotiateResponse, tags=["loads"])
def negotiate_load_rate(
    payload: NegotiateRequest,
    db: Session = Depends(get_db_session),
) -> NegotiateResponse:
    return negotiate_rate(db=db, payload=payload)


@api_router.post("/calls/complete", response_model=CallCompleteResponse, tags=["calls"])
def finalize_call(
    payload: CallCompleteRequest,
    db: Session = Depends(get_db_session),
) -> CallCompleteResponse:
    return complete_call(db=db, payload=payload)


@api_router.get("/metrics/summary", response_model=MetricsSummaryResponse, tags=["metrics"])
def metrics_summary(db: Session = Depends(get_db_session)) -> MetricsSummaryResponse:
    return build_metrics_summary(db=db)


@router.get("/dashboard", include_in_schema=False)
def dashboard_page(request: Request) -> FileResponse:
    if request.session.get("dashboard_authenticated") is not True:
        return FileResponse(_DASHBOARD_LOGIN_INDEX)
    return FileResponse(_DASHBOARD_INDEX)


@router.post("/dashboard/login", response_model=DashboardLoginResponse, include_in_schema=False)
def dashboard_login(
    payload: DashboardLoginRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> DashboardLoginResponse:
    if payload.password != settings.app_api_key:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    request.session.clear()
    request.session["dashboard_authenticated"] = True
    return DashboardLoginResponse(success=True)


@router.get("/dashboard/data", response_model=DashboardDataResponse, tags=["dashboard"])
def dashboard_data(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
    _: None = Depends(require_dashboard_session),
) -> DashboardDataResponse:
    return build_dashboard_data(db=db, limit=limit, offset=offset)


router.include_router(api_router)
