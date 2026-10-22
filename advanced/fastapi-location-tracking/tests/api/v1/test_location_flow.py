from fastapi.testclient import TestClient

from app.db.seed import SEED_TRACKER_TOKEN
from tests.api.v1.helpers import ADMIN_HEADERS, tracker_headers

VAN = "delivery-van-01"


def test_overview_and_trail(client: TestClient) -> None:
    overview = client.get(f"/api/v1/trackers/{VAN}/overview", headers=ADMIN_HEADERS)
    assert overview.status_code == 200
    body = overview.json()
    assert body["total_pings"] == 5
    assert body["monitored_geofences"] == 1

    trail = client.get(
        f"/api/v1/trackers/{VAN}/locations/trail",
        headers=ADMIN_HEADERS,
        params={"window_minutes": 120},
    )
    assert trail.status_code == 200
    assert len(trail.json()["points"]) >= 1


def test_ingest_idempotency_and_dedupe(client: TestClient) -> None:
    headers = tracker_headers(idempotency_key="ping-1")
    payload = {"latitude": 37.7750, "longitude": -122.4194, "dedupe_key": "mobile-100"}
    first = client.post(
        f"/api/v1/trackers/{VAN}/locations",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201

    retry = client.post(
        f"/api/v1/trackers/{VAN}/locations",
        headers=headers,
        json=payload,
    )
    assert retry.status_code == 201
    assert retry.json()["ping"]["id"] == first.json()["ping"]["id"]

    duplicate = client.post(
        f"/api/v1/trackers/{VAN}/locations",
        headers=tracker_headers(idempotency_key="ping-2"),
        json=payload,
    )
    assert duplicate.status_code == 409


def test_geofence_exit_on_ingest(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/trackers/{VAN}/locations",
        headers=tracker_headers(idempotency_key="exit-1"),
        json={"latitude": 37.79, "longitude": -122.4194, "dedupe_key": "outside-depot"},
    )
    assert response.status_code == 201
    events = response.json()["geofence_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "exit"


def test_provision_returns_token(client: TestClient) -> None:
    created = client.post(
        "/api/v1/trackers",
        headers=ADMIN_HEADERS,
        json={"key": "bike-courier-02", "name": "Bike courier"},
    )
    assert created.status_code == 201
    assert created.json()["ingest_token"]
    assert SEED_TRACKER_TOKEN not in created.json()["ingest_token"]
