from fastapi.testclient import TestClient

from tests.api.v1.helpers import auth_headers


def test_register_and_me(client: TestClient) -> None:
    headers = auth_headers(client, "buyer@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "buyer@example.com"
