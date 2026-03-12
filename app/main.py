from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import router as api_router
from app.config import get_settings
from app.db.seed import seed_loads_if_empty
from app.db.session import create_db_and_tables, get_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    seed_loads_if_empty()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["health"])
def healthcheck() -> dict[str, str]:
    with Session(get_engine(settings.database_url)) as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
