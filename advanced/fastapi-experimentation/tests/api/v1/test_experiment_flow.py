from fastapi.testclient import TestClient

from app.db.seed import SEED_EXPERIMENT_TOKEN
from tests.api.v1.helpers import ADMIN_HEADERS, experiment_headers

CHECKOUT = "checkout-button"


def test_assignment_and_results(client: TestClient) -> None:
    assignment = client.get(
        f"/api/v1/experiments/{CHECKOUT}/assignment",
        params={"subject_id": "user-300"},
    )
    assert assignment.status_code == 200
    assert assignment.json()["variant_key"] in {"control", "treatment"}

    results = client.get(
        f"/api/v1/experiments/{CHECKOUT}/results",
        headers=ADMIN_HEADERS,
        params={"window_minutes": 120},
    )
    assert results.status_code == 200
    variants = {row["variant_key"]: row for row in results.json()["variants"]}
    assert variants["control"]["exposures"] >= 1


def test_ingest_idempotency_and_variant_guard(client: TestClient) -> None:
    assignment = client.get(
        f"/api/v1/experiments/{CHECKOUT}/assignment",
        params={"subject_id": "user-400"},
    ).json()
    headers = experiment_headers(idempotency_key="evt-1")
    payload = {
        "subject_id": "user-400",
        "event_type": "exposure",
        "variant_key": assignment["variant_key"],
        "dedupe_key": "user-400-exp",
    }
    first = client.post(
        f"/api/v1/experiments/{CHECKOUT}/events",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201

    retry = client.post(
        f"/api/v1/experiments/{CHECKOUT}/events",
        headers=headers,
        json=payload,
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == first.json()["id"]

    wrong = client.post(
        f"/api/v1/experiments/{CHECKOUT}/events",
        headers=experiment_headers(idempotency_key="evt-2"),
        json={**payload, "variant_key": "wrong-arm", "dedupe_key": "user-400-wrong"},
    )
    assert wrong.status_code == 409


def test_draft_variant_and_start_flow(client: TestClient) -> None:
    created = client.post(
        "/api/v1/experiments",
        headers=ADMIN_HEADERS,
        json={"key": "hero-copy-test", "name": "Hero copy", "description": ""},
    )
    assert created.status_code == 201
    assert created.json()["ingest_token"]
    assert SEED_EXPERIMENT_TOKEN not in created.json()["ingest_token"]
    key = created.json()["key"]

    for variant in (
        {"key": "control", "name": "A", "weight": 50},
        {"key": "treatment", "name": "B", "weight": 50},
    ):
        assert (
            client.post(
                f"/api/v1/experiments/{key}/variants",
                headers=ADMIN_HEADERS,
                json=variant,
            ).status_code
            == 201
        )

    started = client.post(f"/api/v1/experiments/{key}/start", headers=ADMIN_HEADERS)
    assert started.status_code == 200
    assert started.json()["status"] == "running"


def test_stopped_experiment_rejects_ingest(client: TestClient) -> None:
    assert (
        client.post(f"/api/v1/experiments/{CHECKOUT}/stop", headers=ADMIN_HEADERS).status_code
        == 200
    )
    assignment = client.get(
        f"/api/v1/experiments/{CHECKOUT}/assignment",
        params={"subject_id": "user-500"},
    )
    assert assignment.status_code == 404
