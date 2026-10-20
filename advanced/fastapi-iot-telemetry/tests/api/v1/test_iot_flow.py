from fastapi.testclient import TestClient

from app.db.seed import SEED_DEVICE_TOKEN
from tests.api.v1.helpers import ADMIN_HEADERS, device_headers

WAREHOUSE = "warehouse-temp-01"
SUSPENDED = "legacy-pump-02"


def test_overview_and_metric_series(client: TestClient) -> None:
    overview = client.get(
        f"/api/v1/devices/{WAREHOUSE}/metrics/overview",
        headers=ADMIN_HEADERS,
    )
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_readings"] == 10
    assert body["latest_metrics"]["temp_c"] is not None

    series = client.get(
        f"/api/v1/devices/{WAREHOUSE}/metrics/series",
        headers=ADMIN_HEADERS,
        params={"metric_key": "temp_c", "window_minutes": 120},
    )
    assert series.status_code == 200
    assert len(series.json()["points"]) >= 1


def test_ingest_idempotency_and_dedupe(client: TestClient) -> None:
    headers = device_headers(idempotency_key="read-1")
    payload = {
        "metrics": {"temp_c": 19.5, "humidity_pct": 42},
        "dedupe_key": "fw-100",
    }
    first = client.post(
        f"/api/v1/devices/{WAREHOUSE}/telemetry",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201

    retry = client.post(
        f"/api/v1/devices/{WAREHOUSE}/telemetry",
        headers=headers,
        json=payload,
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]

    duplicate = client.post(
        f"/api/v1/devices/{WAREHOUSE}/telemetry",
        headers=device_headers(idempotency_key="read-2"),
        json=payload,
    )
    assert duplicate.status_code == 409


def test_suspended_device_rejects_ingest(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/devices/{SUSPENDED}/telemetry",
        headers={
            "X-Device-Token": "seed-token-legacy-pump",
            "Idempotency-Key": "blocked-1",
        },
        json={"metrics": {"pressure_psi": 12}},
    )
    assert response.status_code == 409


def test_alert_evaluation(client: TestClient) -> None:
    evaluation = client.get(
        f"/api/v1/devices/{WAREHOUSE}/alerts/evaluate",
        headers=ADMIN_HEADERS,
    )
    assert evaluation.status_code == 200
    rules = evaluation.json()
    assert len(rules) == 1
    assert rules[0]["rule"]["name"] == "High temperature"
    assert rules[0]["firing"] is False


def test_provision_returns_token(client: TestClient) -> None:
    created = client.post(
        "/api/v1/devices",
        headers=ADMIN_HEADERS,
        json={"key": "new-sensor-03", "name": "New sensor", "site": "Roof"},
    )
    assert created.status_code == 201
    assert created.json()["ingest_token"]
    assert SEED_DEVICE_TOKEN not in created.json()["ingest_token"]
