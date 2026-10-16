import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.bookmark_repository import get_bookmark_repository


@pytest.fixture
def client() -> TestClient:
    get_bookmark_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_bookmark_repository.cache_clear()
