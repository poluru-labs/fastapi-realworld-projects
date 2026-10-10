import os

os.environ["APP_NAME"] = "Event Registration API"

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_event_repository,
    get_refresh_token_repository,
    get_registration_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_event_repository.cache_clear()
    get_registration_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_event_repository.cache_clear()
    get_registration_repository.cache_clear()
