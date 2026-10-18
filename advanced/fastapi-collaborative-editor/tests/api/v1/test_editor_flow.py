from fastapi.testclient import TestClient

from tests.api.v1.helpers import auth_headers

SEED_DOC = "team-playbook"
PRIVATE_DOC = "private-design-doc"


def test_edit_idempotent_and_sync_delivery(client: TestClient) -> None:
    editor = auth_headers(client, "editor@example.com")
    collaborator = auth_headers(client, "collab@example.com")

    client.post(f"/api/v1/documents/{SEED_DOC}/join", headers=collaborator)
    client.post(f"/api/v1/documents/{SEED_DOC}/join", headers=editor)

    doc = client.get(f"/api/v1/documents/{SEED_DOC}", headers=editor).json()
    base = doc["revision"]

    submitted = client.post(
        f"/api/v1/documents/{SEED_DOC}/edits",
        headers={**editor, "Idempotency-Key": "edit-1"},
        json={
            "base_revision": base,
            "patch": {"start": len(doc["body"]), "delete": 0, "insert": " — collaborate!"},
        },
    )
    assert submitted.status_code == 201
    revision = submitted.json()
    assert revision["revision"] == base + 1

    again = client.post(
        f"/api/v1/documents/{SEED_DOC}/edits",
        headers={**editor, "Idempotency-Key": "edit-1"},
        json={"base_revision": 0, "patch": {"start": 0, "delete": 0, "insert": "x"}},
    )
    assert again.json()["id"] == revision["id"]

    sync_user = auth_headers(client, "sync@example.com")
    client.post(
        "/api/v1/sync/register",
        headers=sync_user,
        json={"node_id": "node-a", "document_slugs": [SEED_DOC]},
    )
    claimed = client.post(
        "/api/v1/sync/claim",
        headers=sync_user,
        json={"node_id": "node-a"},
    )
    assert claimed.status_code == 200
    job = claimed.json()
    assert job["recipient_id"] != revision["author_id"]
    assert job["status"] == "syncing"

    completed = client.post(
        f"/api/v1/sync/jobs/{job['id']}/complete",
        headers=sync_user,
        json={"node_id": "node-a", "expected_version": job["version"]},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "synced"


def test_stale_base_revision_conflict(client: TestClient) -> None:
    user = auth_headers(client, "stale@example.com")
    client.post(f"/api/v1/documents/{SEED_DOC}/join", headers=user)
    stale = client.post(
        f"/api/v1/documents/{SEED_DOC}/edits",
        headers={**user, "Idempotency-Key": "stale-edit"},
        json={
            "base_revision": 0,
            "patch": {"start": 0, "delete": 0, "insert": "?"},
        },
    )
    assert stale.status_code == 409


def test_private_document_hidden(client: TestClient) -> None:
    outsider = auth_headers(client, "outsider@example.com")
    hidden = client.get(f"/api/v1/documents/{PRIVATE_DOC}", headers=outsider)
    assert hidden.status_code == 404


def test_revision_cursor_and_seen_state(client: TestClient) -> None:
    reader = auth_headers(client, "reader@example.com")
    client.post(f"/api/v1/documents/{SEED_DOC}/join", headers=reader)

    page = client.get(
        f"/api/v1/documents/{SEED_DOC}/edits?after_revision=0",
        headers=reader,
    )
    assert page.status_code == 200

    doc = client.get(f"/api/v1/documents/{SEED_DOC}", headers=reader).json()
    updated = client.patch(
        f"/api/v1/documents/{SEED_DOC}/members/me/seen",
        headers=reader,
        json={"last_seen_revision": doc["revision"]},
    )
    assert updated.status_code == 200
    assert updated.json()["last_seen_revision"] == doc["revision"]
