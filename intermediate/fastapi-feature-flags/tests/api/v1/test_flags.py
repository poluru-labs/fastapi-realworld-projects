from fastapi.testclient import TestClient

from tests.api.v1.helpers import demo_headers, runtime_headers


def test_allowlist_wins(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runtime/evaluate",
        headers=runtime_headers(),
        json={
            "flag_keys": ["new-checkout"],
            "context": {"user_id": "u_vip_1"},
        },
    )
    assert response.status_code == 200
    evaluation = response.json()["evaluations"][0]
    assert evaluation["enabled"] is True
    assert evaluation["reason"] == "allowlisted user"


def test_disabled_flag(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runtime/evaluate",
        headers=runtime_headers(),
        json={
            "flag_keys": ["beta-api"],
            "context": {"user_id": "u_vip_1"},
        },
    )
    assert response.status_code == 200
    assert response.json()["evaluations"][0]["enabled"] is False


def test_dark_mode_full_rollout(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runtime/evaluate",
        headers=runtime_headers(),
        json={
            "flag_keys": ["dark-mode"],
            "context": {"user_id": "any-user"},
        },
    )
    assert response.status_code == 200
    assert response.json()["evaluations"][0]["enabled"] is True


def test_create_flag(client: TestClient) -> None:
    headers = demo_headers(client)
    created = client.post(
        "/api/v1/flags",
        headers=headers,
        json={
            "key": "experiments-ui",
            "name": "Experiments UI",
            "rollout_percentage": 10,
        },
    )
    assert created.status_code == 201
    assert created.json()["rollout_percentage"] == 10


def test_invalid_runtime_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runtime/evaluate",
        headers={"X-Runtime-Token": "bad-token"},
        json={"flag_keys": ["dark-mode"], "context": {"user_id": "x"}},
    )
    assert response.status_code == 401
