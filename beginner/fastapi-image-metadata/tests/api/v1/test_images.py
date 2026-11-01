from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.main import create_app
from app.repositories.image_repository import get_image_repository


def _png_file(*, width: int, height: int, name: str = "sample.png") -> tuple[str, bytes, str]:
    buffer = BytesIO()
    Image.new("RGB", (width, height), (100, 149, 237)).save(buffer, format="PNG")
    return (name, buffer.getvalue(), "image/png")


def test_list_seed_metadata(client: TestClient) -> None:
    listed = client.get("/api/v1/images")
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 2
    hero = next(row for row in body if row["filename"] == "hero.jpg")
    assert hero["width"] == 1280
    assert hero["format"] == "JPEG"
    assert "hero" in hero["tags"]


def test_download_seed_image(client: TestClient) -> None:
    response = client.get("/api/v1/images/2/content")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/png")
    with Image.open(BytesIO(response.content)) as image:
        assert image.size == (64, 64)


def test_upload_patch_and_delete(client: TestClient) -> None:
    created = client.post(
        "/api/v1/images",
        files={"file": _png_file(width=100, height=50)},
        data={"caption": "Test shot", "tags": "demo, upload"},
    )
    assert created.status_code == 201
    image_id = created.json()["id"]
    assert created.json()["width"] == 100
    assert created.json()["height"] == 50
    assert created.json()["tags"] == ["demo", "upload"]

    updated = client.patch(
        f"/api/v1/images/{image_id}",
        json={"caption": "Updated caption", "tags": ["demo"]},
    )
    assert updated.status_code == 200
    assert updated.json()["caption"] == "Updated caption"
    assert updated.json()["tags"] == ["demo"]

    assert client.delete(f"/api/v1/images/{image_id}").status_code == 204
    assert client.get(f"/api/v1/images/{image_id}").status_code == 404


def test_filter_by_min_width(client: TestClient) -> None:
    response = client.get("/api/v1/images", params={"min_width": 1000})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["filename"] == "hero.jpg"


def test_reject_non_image(client: TestClient) -> None:
    response = client.post(
        "/api/v1/images",
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400
    assert "not a recognizable image" in response.json()["detail"]


def test_upload_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "50")
    get_settings.cache_clear()
    get_image_repository.cache_clear()
    with TestClient(create_app()) as test_client:
        response = test_client.post(
            "/api/v1/images",
            files={"file": _png_file(width=200, height=200)},
        )
        assert response.status_code == 413
    get_settings.cache_clear()
