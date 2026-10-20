from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS, ingest_headers


def test_seed_overview_and_time_series(client: TestClient) -> None:
    overview = client.get(
        "/api/v1/streams/web-traffic/metrics/overview",
        headers=ADMIN_HEADERS,
    )
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_events"] == 12
    assert body["events_last_15m"] >= 1

    series = client.get(
        "/api/v1/streams/web-traffic/metrics/time-series",
        headers=ADMIN_HEADERS,
        params={"window_minutes": 60, "bucket_seconds": 900},
    )
    assert series.status_code == 200
    assert len(series.json()["buckets"]) >= 1


def test_ingest_idempotency_and_dedupe(client: TestClient) -> None:
    headers = ingest_headers(idempotency_key="ingest-1")
    payload = {
        "event_name": "page_view",
        "properties": {"path": "/docs"},
        "dedupe_key": "client-99",
    }
    first = client.post(
        "/api/v1/streams/web-traffic/events",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201
    event_id = first.json()["id"]

    retry = client.post(
        "/api/v1/streams/web-traffic/events",
        headers=headers,
        json=payload,
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == event_id

    duplicate = client.post(
        "/api/v1/streams/web-traffic/events",
        headers=ingest_headers(idempotency_key="ingest-2"),
        json=payload,
    )
    assert duplicate.status_code == 409


def test_paused_stream_rejects_ingest(client: TestClient) -> None:
    response = client.post(
        "/api/v1/streams/checkout/events",
        headers=ingest_headers(idempotency_key="paused-1"),
        json={"event_name": "purchase", "properties": {"sku": "ABC"}},
    )
    assert response.status_code == 409


def test_alert_evaluation(client: TestClient) -> None:
    evaluation = client.get(
        "/api/v1/streams/web-traffic/alerts/evaluate",
        headers=ADMIN_HEADERS,
    )
    assert evaluation.status_code == 200
    rules = evaluation.json()
    assert len(rules) == 1
    assert rules[0]["rule"]["name"] == "Traffic spike"
    assert rules[0]["firing"] is False
