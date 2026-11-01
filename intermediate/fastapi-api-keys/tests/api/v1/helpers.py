from fastapi.testclient import TestClient

from app.repositories.key_repository import DEMO_SEED_API_KEY


def demo_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "demo@example.com", "password": "DemoPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def seed_api_key_headers() -> dict[str, str]:
    return {"X-Api-Key": DEMO_SEED_API_KEY}
