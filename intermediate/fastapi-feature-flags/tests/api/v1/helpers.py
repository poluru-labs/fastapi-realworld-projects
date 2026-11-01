from fastapi.testclient import TestClient

from app.repositories.flag_repository import RUNTIME_TOKEN_DEMO


def demo_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "demo@example.com", "password": "DemoPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def runtime_headers() -> dict[str, str]:
    return {"X-Runtime-Token": RUNTIME_TOKEN_DEMO}
