import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_NAME"] = "Distributed Orders API"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.bootstrap import create_all_tables
from app.db.seed import seed_reference_data
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as test_client:
        asyncio.run(create_all_tables(application.state.engine))
        asyncio.run(_seed(application))
        yield test_client
    get_settings.cache_clear()


async def _seed(application) -> None:
    session_factory = application.state.session_factory
    async with session_factory() as session:
        await seed_reference_data(session)
