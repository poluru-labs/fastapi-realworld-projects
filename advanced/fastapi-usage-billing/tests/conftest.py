import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["APP_NAME"] = "FastAPI Usage Billing API"
os.environ["ADMIN_API_KEY"] = "test-admin-key"
os.environ["API_KEY_PEPPER"] = "test-pepper"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as test_client:
        yield test_client
    get_settings.cache_clear()
