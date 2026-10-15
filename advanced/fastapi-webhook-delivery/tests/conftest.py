import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_NAME"] = "Webhook Delivery API"

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport

from app.api.v1.endpoints import capture
from app.core.config import get_settings
from app.db.bootstrap import create_all_tables
from app.db.seed import seed_reference_data
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    capture.CAPTURED.clear()
    application = create_app()
    application.state.webhook_http_client = httpx.AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver",
    )
    with TestClient(application) as test_client:
        asyncio.run(create_all_tables(application.state.engine))
        asyncio.run(_seed(application))
        yield test_client
    get_settings.cache_clear()


async def _seed(application) -> None:
    session_factory = application.state.session_factory
    async with session_factory() as session:
        await seed_reference_data(session)
