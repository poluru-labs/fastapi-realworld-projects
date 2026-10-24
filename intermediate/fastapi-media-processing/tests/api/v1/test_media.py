from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, demo_headers, register_headers


def test_admin_operations_and_preset_job(client: TestClient) -> None:
    headers = admin_headers(client)
    catalog = client.get("/api/v1/jobs/operations", headers=headers)
    assert catalog.status_code == 200
    assert len(catalog.json()) == 4

    jobs = client.get("/api/v1/jobs", headers=headers)
    assert jobs.status_code == 200
    assert jobs.json()[0]["status"] == "completed"
    assert jobs.json()[0]["result"]["output"]["width_px"] == 320

    submitted = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"asset_id": 1, "preset_id": 1},
    )
    assert submitted.status_code == 201
    assert submitted.json()["result"]["operation"] == "thumbnail"


def test_demo_transcode_video(client: TestClient) -> None:
    headers = demo_headers(client)
    job = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "asset_id": 2,
            "operation": "transcode",
            "parameters": {"format": "webm"},
        },
    )
    assert job.status_code == 201
    body = job.json()
    assert body["status"] == "completed"
    assert body["result"]["output"]["mime_type"] == "video/webm"


def test_wrong_operation_for_kind_is_conflict(client: TestClient) -> None:
    headers = admin_headers(client)
    response = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "asset_id": 1,
            "operation": "transcode",
            "parameters": {"format": "mp4"},
        },
    )
    assert response.status_code == 409


def test_non_admin_cannot_list_operations(client: TestClient) -> None:
    headers = register_headers(client, "creator@example.com")
    assert client.get("/api/v1/jobs/operations", headers=headers).status_code == 403


def test_user_cannot_read_other_job(client: TestClient) -> None:
    admin = admin_headers(client)
    job = client.post(
        "/api/v1/jobs",
        headers=admin,
        json={"asset_id": 1, "preset_id": 1},
    ).json()

    other = register_headers(client, "viewer@example.com")
    assert client.get(f"/api/v1/jobs/{job['id']}", headers=other).status_code == 404


def test_demo_cannot_submit_on_admin_asset(client: TestClient) -> None:
    headers = demo_headers(client)
    response = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={"asset_id": 1, "preset_id": 1},
    )
    assert response.status_code == 404
