import os

os.environ["APP_NAME"] = "Support Tickets API"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.repositories.ticket_repository import get_ticket_repository


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    get_ticket_repository.cache_clear()
    application = create_app()
    yield TestClient(application)
    get_ticket_repository.cache_clear()
    get_settings.cache_clear()
