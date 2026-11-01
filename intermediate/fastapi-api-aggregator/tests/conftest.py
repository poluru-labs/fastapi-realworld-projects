import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_comment_repository,
    get_post_repository,
    get_refresh_token_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_post_repository.cache_clear()
    get_comment_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_post_repository.cache_clear()
    get_comment_repository.cache_clear()
