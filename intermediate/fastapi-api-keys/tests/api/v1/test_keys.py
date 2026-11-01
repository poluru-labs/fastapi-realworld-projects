from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers


def test_create_key_returns_secret_once(client: TestClient) -> None:
    headers = demo_headers(client)
    created = client.post(
        "/api/v1/keys",
        headers=headers,
        json={"name": "Local dev", "scopes": ["projects:read"]},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["secret"].startswith("sk_live_")
    listed = client.get("/api/v1/keys", headers=headers)
    assert "secret" not in listed.text


def test_revoked_key_rejected(client: TestClient) -> None:
    headers = demo_headers(client)
    created = client.post(
        "/api/v1/keys",
        headers=headers,
        json={"name": "Temp", "scopes": ["metrics:read"]},
    )
    key_id = created.json()["key"]["id"]
    secret = created.json()["secret"]
    client.post(f"/api/v1/keys/{key_id}/revoke", headers=headers)
    denied = client.get("/api/v1/access/metrics", headers={"X-Api-Key": secret})
    assert denied.status_code == 401
