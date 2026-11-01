import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.repositories.file_repository import get_file_repository


def test_list_and_download_seed(client: TestClient) -> None:
    listed = client.get("/api/v1/files")
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    download = client.get("/api/v1/files/1/content")
    assert download.status_code == 200
    assert download.content == b"Hello from the file upload API!"
    assert "welcome.txt" in download.headers["content-disposition"]


def test_upload_and_delete(client: TestClient) -> None:
    created = client.post(
        "/api/v1/files",
        files={"file": ("demo.txt", b"demo content", "text/plain")},
        data={"description": "A demo upload"},
    )
    assert created.status_code == 201
    file_id = created.json()["id"]
    assert created.json()["size_bytes"] == 12

    updated = client.patch(
        f"/api/v1/files/{file_id}",
        json={"description": "Updated note"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Updated note"

    assert client.delete(f"/api/v1/files/{file_id}").status_code == 204
    assert client.get(f"/api/v1/files/{file_id}").status_code == 404


def test_filter_by_content_type(client: TestClient) -> None:
    response = client.get("/api/v1/files", params={"content_type": "markdown"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "notes.md"


def test_upload_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "10")
    get_settings.cache_clear()
    get_file_repository.cache_clear()
    with TestClient(create_app()) as test_client:
        response = test_client.post(
            "/api/v1/files",
            files={"file": ("big.bin", b"x" * 20, "application/octet-stream")},
        )
        assert response.status_code == 413
    get_settings.cache_clear()
