from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.base import Base


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


@lru_cache
def get_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    return create_engine(url, connect_args=_connect_args(url))


@lru_cache
def get_session_factory(database_url: str | None = None):
    engine = get_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def reset_db_state() -> None:
    get_session_factory.cache_clear()
    get_engine.cache_clear()


def create_db_and_tables() -> None:
    settings = get_settings()
    engine = get_engine(settings.database_url)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.execute(text("SELECT 1"))


def get_db():
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
