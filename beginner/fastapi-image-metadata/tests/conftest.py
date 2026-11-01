import os

os.environ["APP_NAME"] = "Image Metadata API"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.repositories.image_repository import get_image_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_image_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_image_repository.cache_clear()
    get_settings.cache_clear()
