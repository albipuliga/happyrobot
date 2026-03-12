import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("APP_API_KEY", "test-api-key")
    monkeypatch.delenv("FMCSA_API_KEY", raising=False)

    from app.config import get_settings
    from app.db.session import reset_db_state

    get_settings.cache_clear()
    reset_db_state()

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    get_settings.cache_clear()
    reset_db_state()
    if db_path.exists():
        os.remove(db_path)
