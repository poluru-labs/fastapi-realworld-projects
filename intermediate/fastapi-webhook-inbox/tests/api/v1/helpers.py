from fastapi.testclient import TestClient

from app.repositories.webhook_repository import SEED_WEBHOOK_TOKEN


def admin_headers(client: TestClient) -> dict[str, str]:
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPass123!"},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def ingest_headers(*, idempotency_key: str) -> dict[str, str]:
    return {
        "X-Webhook-Token": SEED_WEBHOOK_TOKEN,
        "Idempotency-Key": idempotency_key,
    }
