import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.gradebook_repository import get_gradebook_repository


@pytest.fixture
def client() -> TestClient:
    get_gradebook_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_gradebook_repository.cache_clear()
