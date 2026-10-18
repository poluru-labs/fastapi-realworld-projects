import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.product_repository import get_product_repository


@pytest.fixture
def client() -> TestClient:
    get_product_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_product_repository.cache_clear()
