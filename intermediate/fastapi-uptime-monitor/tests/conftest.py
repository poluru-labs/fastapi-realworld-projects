import os

os.environ.setdefault("APP_NAME", "Uptime Monitor API")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-32chars")

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_probe_client, get_refresh_token_repository, get_user_repository
from app.core.config import get_settings
from app.main import create_app
from app.repositories.monitor_repository import get_monitor_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_monitor_repository.cache_clear()
    get_probe_client.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_monitor_repository.cache_clear()
    get_probe_client.cache_clear()
