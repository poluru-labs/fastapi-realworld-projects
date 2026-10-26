from fastapi.testclient import TestClient

from tests.api.v1.helpers import ADMIN_HEADERS, upload_headers

DEMO_KEY = "demo-archive"


def test_admin_list_and_resume_status(client: TestClient) -> None:
    listed = client.get("/api/v1/uploads", headers=ADMIN_HEADERS)
    assert listed.status_code == 200
    assert any(row["key"] == DEMO_KEY for row in listed.json())

    status = client.get(
        f"/api/v1/uploads/{DEMO_KEY}/status",
        headers={"X-Upload-Token": "seed-upload-demo-archive"},
    )
    assert status.status_code == 200
    body = status.json()
    assert body["parts_received"] == 2
    assert body["expected_parts"] == 4
    assert body["missing_part_indexes"] == [2, 3]


def test_part_idempotency_and_complete(client: TestClient) -> None:
    headers = upload_headers(part_index=2, idempotency_key="part-2")
    first = client.post(
        f"/api/v1/uploads/{DEMO_KEY}/parts",
        headers=headers,
        content=b"c" * 250,
    )
    assert first.status_code == 201

    retry = client.post(
        f"/api/v1/uploads/{DEMO_KEY}/parts",
        headers=headers,
        content=b"c" * 250,
    )
    assert retry.status_code == 201
    assert retry.json()["part_index"] == first.json()["part_index"]

    last = client.post(
        f"/api/v1/uploads/{DEMO_KEY}/parts",
        headers=upload_headers(part_index=3, idempotency_key="part-3"),
        content=b"d" * 250,
    )
    assert last.status_code == 201

    done = client.post(
        f"/api/v1/uploads/{DEMO_KEY}/complete",
        headers={"X-Upload-Token": "seed-upload-demo-archive"},
    )
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["missing_part_indexes"] == []


def test_wrong_part_size_is_conflict(client: TestClient) -> None:
    response = client.post(
        f"/api/v1/uploads/{DEMO_KEY}/parts",
        headers=upload_headers(part_index=0, idempotency_key="bad-size"),
        content=b"x" * 100,
    )
    assert response.status_code == 409


def test_provision_upload(client: TestClient) -> None:
    created = client.post(
        "/api/v1/uploads",
        headers=ADMIN_HEADERS,
        json={
            "key": "new-bundle",
            "filename": "bundle.tar",
            "total_bytes": 512,
            "chunk_size_bytes": 256,
        },
    )
    assert created.status_code == 201
    assert created.json()["upload_token"]
    assert created.json()["expected_parts"] == 2
