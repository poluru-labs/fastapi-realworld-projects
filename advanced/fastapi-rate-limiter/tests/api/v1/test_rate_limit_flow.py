from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS, client_headers

SUBJECT = {"subject_key": "device-abc", "cost": 1}


def test_check_and_admin_usage(client: TestClient) -> None:
    check = client.post(
        "/api/v1/quota/check",
        headers=client_headers(),
        json=SUBJECT,
    )
    assert check.status_code == 200
    body = check.json()
    assert body["allowed"] is True
    assert body["window_count"] == 3
    assert body["remaining"] == 7

    usage = client.get("/api/v1/clients/mobile-app/usage", headers=ADMIN_HEADERS)
    assert usage.status_code == 200
    rows = {row["subject_key"]: row for row in usage.json()}
    assert rows["device-abc"]["window_count"] == 3


def test_consume_idempotency_and_limit(client: TestClient) -> None:
    headers = client_headers(idempotency_key="consume-1")
    first = client.post("/api/v1/quota/consume", headers=headers, json=SUBJECT)
    assert first.status_code == 200
    assert first.json()["window_count"] == 4

    retry = client.post("/api/v1/quota/consume", headers=headers, json=SUBJECT)
    assert retry.status_code == 200
    assert retry.json()["window_count"] == 4

    for index in range(2, 8):
        response = client.post(
            "/api/v1/quota/consume",
            headers=client_headers(idempotency_key=f"consume-{index}"),
            json=SUBJECT,
        )
        assert response.status_code == 200

    blocked = client.post(
        "/api/v1/quota/consume",
        headers=client_headers(idempotency_key="consume-over"),
        json=SUBJECT,
    )
    assert blocked.status_code == 429
    assert blocked.json()["allowed"] is False


def test_pause_policy_blocks_quota(client: TestClient) -> None:
    assert (
        client.post("/api/v1/policies/public-api/pause", headers=ADMIN_HEADERS).status_code == 200
    )
    check = client.post(
        "/api/v1/quota/check",
        headers=client_headers(),
        json={"subject_key": "device-new", "cost": 1},
    )
    assert check.status_code == 200
    assert check.json()["allowed"] is False


def test_provision_client_and_policy(client: TestClient) -> None:
    policy = client.post(
        "/api/v1/policies",
        headers=ADMIN_HEADERS,
        json={
            "key": "burst-api",
            "name": "Burst",
            "description": "",
            "limit": 5,
            "window_seconds": 30,
        },
    )
    assert policy.status_code == 201

    provisioned = client.post(
        "/api/v1/clients",
        headers=ADMIN_HEADERS,
        json={"key": "partner-svc", "name": "Partner", "policy_key": "burst-api"},
    )
    assert provisioned.status_code == 201
    assert provisioned.json()["client_key"]
