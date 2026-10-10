import asyncio
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["APP_NAME"] = "Multitenant SaaS API"

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.bootstrap import create_all_tables
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    get_settings.cache_clear()
    application = create_app()
    with TestClient(application) as test_client:
        asyncio.run(create_all_tables(application.state.engine))
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register acme tenant and return Authorization + X-Tenant-Slug headers."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@acme.example",
            "password": "SecurePass123!",
            "full_name": "Alex Owner",
            "tenant_name": "Acme Corp",
            "tenant_slug": "acme-corp",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return {
        "Authorization": f"Bearer {body['tokens']['access_token']}",
        "X-Tenant-Slug": body["tenant"]["slug"],
    }
