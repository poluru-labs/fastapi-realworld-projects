import os

os.environ.setdefault("APP_NAME", "Webhook Inbox API")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-32chars")

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_refresh_token_repository, get_user_repository
from app.core.config import get_settings
from app.main import create_app
from app.repositories.webhook_repository import get_webhook_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_webhook_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_webhook_repository.cache_clear()
