import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.entry_repository import get_entry_repository


@pytest.fixture
def client() -> TestClient:
    get_entry_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_entry_repository.cache_clear()
