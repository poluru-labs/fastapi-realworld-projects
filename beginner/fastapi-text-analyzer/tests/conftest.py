import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_analyzer_repository
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_analyzer_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_analyzer_repository.cache_clear()
