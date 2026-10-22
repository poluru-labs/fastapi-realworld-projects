import os

os.environ.setdefault("APP_NAME", "Quiz API")

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.repositories.quiz_repository import get_quiz_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_quiz_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_settings.cache_clear()
    get_quiz_repository.cache_clear()
