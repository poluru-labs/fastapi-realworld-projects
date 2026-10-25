from fastapi.testclient import TestClient

from tests.api.v1.helpers import register_headers

VALID_CSV = """title,summary,body,tags,slug,publish
Import one,Blurb,Body text.,fastapi|csv,csv-import-one,false
Import two,,Second body.,docs,csv-import-two,true
"""

BAD_ROW_CSV = """title,body
Good title,Good body
,Missing title
"""


def test_download_template(client: TestClient) -> None:
    response = client.get("/api/v1/imports/template")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "title,summary,body" in response.text


def test_import_requires_auth(client: TestClient) -> None:
    response = client.post(
        "/api/v1/imports/posts",
        files={"file": ("posts.csv", VALID_CSV, "text/csv")},
    )
    assert response.status_code == 401


def test_dry_run_validates_without_creating(client: TestClient) -> None:
    headers = register_headers(client, email="importer@example.com")
    before = client.get("/api/v1/posts/mine", headers=headers).json()["total"]

    response = client.post(
        "/api/v1/imports/posts?dry_run=true",
        headers=headers,
        files={"file": ("posts.csv", VALID_CSV, "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["dry_run"] is True
    assert body["total_rows"] == 2
    assert body["created_count"] == 0
    assert body["skipped_count"] == 0

    after = client.get("/api/v1/posts/mine", headers=headers).json()["total"]
    assert after == before


def test_import_creates_and_publishes(client: TestClient) -> None:
    headers = register_headers(client, email="bulk@example.com")
    response = client.post(
        "/api/v1/imports/posts",
        headers=headers,
        files={"file": ("posts.csv", VALID_CSV, "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 2
    assert body["published_count"] == 1
    assert "csv-import-one" in body["created_slugs"]

    draft = client.get("/api/v1/posts/csv-import-one", headers=headers).json()
    assert draft["status"] == "draft"

    public = client.get("/api/v1/posts/csv-import-two").json()
    assert public["status"] == "published"

    job = client.get(f"/api/v1/imports/{body['id']}", headers=headers).json()
    assert job["filename"] == "posts.csv"


def test_import_reports_row_errors(client: TestClient) -> None:
    headers = register_headers(client, email="errors@example.com")
    response = client.post(
        "/api/v1/imports/posts",
        headers=headers,
        files={"file": ("bad.csv", BAD_ROW_CSV, "text/csv")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["created_count"] == 1
    assert body["skipped_count"] == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row_number"] == 3


def test_import_rejects_missing_columns(client: TestClient) -> None:
    headers = register_headers(client, email="missing-col@example.com")
    response = client.post(
        "/api/v1/imports/posts",
        headers=headers,
        files={"file": ("nope.csv", "title,summary\nx,y\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "body" in response.json()["detail"]
