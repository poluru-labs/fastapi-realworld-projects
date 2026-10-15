import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_habit_repository
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_habit_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_habit_repository.cache_clear()
