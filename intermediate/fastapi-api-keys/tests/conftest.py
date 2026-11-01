import os

os.environ.setdefault("APP_NAME", "API Keys Service")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-32chars")
os.environ.setdefault("API_KEY_PEPPER", "dev-api-key-pepper-change-me")

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_refresh_token_repository, get_user_repository
from app.core.config import get_settings
from app.main import create_app
from app.repositories.key_repository import get_key_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_key_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_key_repository.cache_clear()
