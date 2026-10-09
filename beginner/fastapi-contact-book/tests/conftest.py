import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_item_repository
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_item_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_item_repository.cache_clear()
