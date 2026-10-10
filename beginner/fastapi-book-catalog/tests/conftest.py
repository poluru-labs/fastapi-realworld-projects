import os

os.environ["APP_NAME"] = "Book Catalog API"

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_book_repository
from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_book_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_book_repository.cache_clear()
