import os

os.environ.setdefault("APP_NAME", "API Aggregator")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-32chars")

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_refresh_token_repository, get_upstream_client, get_user_repository
from app.core.config import get_settings
from app.main import create_app
from app.repositories.aggregator_repository import get_aggregator_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_aggregator_repository.cache_clear()
    get_upstream_client.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_aggregator_repository.cache_clear()
    get_upstream_client.cache_clear()
