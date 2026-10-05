import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_refresh_token_repository,
    get_task_repository,
    get_team_repository,
    get_user_repository,
)
from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_team_repository.cache_clear()
    get_task_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_user_repository.cache_clear()
    get_refresh_token_repository.cache_clear()
    get_team_repository.cache_clear()
    get_task_repository.cache_clear()
