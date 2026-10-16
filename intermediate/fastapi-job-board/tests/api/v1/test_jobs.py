from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_job, register_headers

SEED_PUBLISHED = "senior-fastapi-engineer"
SEED_DRAFT = "draft-frontend-contract"


def test_public_list_hides_drafts(client: TestClient) -> None:
    listed = client.get("/api/v1/jobs")
    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["slug"] == SEED_PUBLISHED
    assert page["items"][0]["status"] == "published"
    assert page["items"][0]["application_count"] == 1

    hidden = client.get("/api/v1/jobs", params={"status": "draft", "skill": "react"})
    assert hidden.status_code == 200
    assert hidden.json()["items"] == []

    draft = client.get(f"/api/v1/jobs/{SEED_DRAFT}")
    assert draft.status_code == 404
    assert draft.json()["detail"] == f"Job {SEED_DRAFT} not found"


def test_filters_combine_and_search_description(client: TestClient) -> None:
    by_skill = client.get("/api/v1/jobs", params={"skill": "FastAPI"})
    assert [item["slug"] for item in by_skill.json()["items"]] == [SEED_PUBLISHED]

    by_employer = client.get(
        "/api/v1/jobs",
        params={"employer_id": 1, "q": "mentor"},
    )
    assert [item["slug"] for item in by_employer.json()["items"]] == [SEED_PUBLISHED]

    missed = client.get("/api/v1/jobs", params={"q": "frontend contract"})
    assert missed.json()["total"] == 0


def test_pagination_reports_the_unpaged_total(client: TestClient) -> None:
    employer = register_headers(client, "pager@example.com", full_name="Pager")
    for index in range(2):
        created = create_job(client, employer, title=f"Open role {index}")
        published = client.post(f"/api/v1/jobs/{created['slug']}/publish", headers=employer)
        assert published.status_code == 200

    first = client.get("/api/v1/jobs", params={"limit": 1, "offset": 0}).json()
    second = client.get("/api/v1/jobs", params={"limit": 1, "offset": 1}).json()
    beyond = client.get("/api/v1/jobs", params={"limit": 1, "offset": 20}).json()

    assert first["total"] == second["total"] == 3
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert beyond["items"] == []
    assert beyond["total"] == 3


def test_create_slug_rules(client: TestClient) -> None:
    employer = register_headers(client, "employer@example.com", full_name="Ada Employer")
    created = create_job(client, employer, title="Hello, World!")
    assert created["slug"] == "hello-world"
    assert created["status"] == "draft"
    assert created["employer_name"] == "Ada Employer"
    assert created["published_at"] is None
    assert created["skills"] == ["python"]

    folded = create_job(
        client,
        employer,
        title="Skill folding",
        skills=["Python", "python", "fastapi"],
    )
    assert folded["skills"] == ["python", "fastapi"]

    custom = create_job(client, employer, title="Hello, World!", slug="second-hello")
    assert custom["slug"] == "second-hello"

    duplicate = client.post(
        "/api/v1/jobs",
        headers=employer,
        json={
            "title": "Hello, World!",
            "company": "Acme",
            "description": "Again.",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "Another job already uses this slug"

    symbols = client.post(
        "/api/v1/jobs",
        headers=employer,
        json={"title": "!!!", "company": "X", "description": "No letters."},
    )
    assert symbols.status_code == 422

    bad_skill = client.post(
        "/api/v1/jobs",
        headers=employer,
        json={
            "title": "Bad skill",
            "company": "X",
            "description": "Nope.",
            "skills": ["fast api"],
        },
    )
    assert bad_skill.status_code == 422


def test_draft_visibility(client: TestClient) -> None:
    employer = register_headers(client, "writer@example.com", full_name="Writer")
    stranger = register_headers(client, "reader@example.com", full_name="Reader")
    created = create_job(client, employer, title="Private draft")
    slug = created["slug"]

    own = client.get(f"/api/v1/jobs/{slug}", headers=employer)
    assert own.status_code == 200
    assert own.json()["status"] == "draft"

    hidden = client.get(f"/api/v1/jobs/{slug}", headers=stranger)
    assert hidden.status_code == 404

    admin = client.get(f"/api/v1/jobs/{slug}", headers=admin_headers(client))
    assert admin.status_code == 200

    mine = client.get("/api/v1/jobs/mine", headers=employer).json()
    assert [item["slug"] for item in mine["items"]] == [slug]

    admin_mine = client.get("/api/v1/jobs/mine", headers=admin_headers(client)).json()
    assert slug not in [item["slug"] for item in admin_mine["items"]]
    assert SEED_DRAFT in [item["slug"] for item in admin_mine["items"]]


def test_publish_unpublish_close_and_reopen(client: TestClient) -> None:
    employer = register_headers(client, "editor@example.com", full_name="Editor")
    created = create_job(client, employer, title="Status walk")
    slug = created["slug"]

    too_soon = client.post(f"/api/v1/jobs/{slug}/close", headers=employer)
    assert too_soon.status_code == 409
    assert "Only a published job can be closed" in too_soon.json()["detail"]

    published = client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None
    assert client.get(f"/api/v1/jobs/{slug}").status_code == 200

    again = client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    assert again.status_code == 409

    draft_again = client.post(f"/api/v1/jobs/{slug}/unpublish", headers=employer)
    assert draft_again.status_code == 200
    assert draft_again.json()["status"] == "draft"
    assert draft_again.json()["published_at"] is None
    assert client.get(f"/api/v1/jobs/{slug}").status_code == 404

    client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    closed = client.post(f"/api/v1/jobs/{slug}/close", headers=admin_headers(client))
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert closed.json()["published_at"] is not None
    assert client.get(f"/api/v1/jobs/{slug}").status_code == 404

    reopened = client.post(f"/api/v1/jobs/{slug}/reopen", headers=employer)
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "draft"
    assert reopened.json()["published_at"] is None


def test_edit_and_delete_permissions(client: TestClient) -> None:
    employer = register_headers(client, "owner@example.com", full_name="Owner")
    stranger = register_headers(client, "other@example.com", full_name="Other")
    created = create_job(client, employer, title="Owned role")
    slug = created["slug"]

    sneaky = client.patch(
        f"/api/v1/jobs/{slug}",
        headers=stranger,
        json={"title": "Taken"},
    )
    assert sneaky.status_code == 404

    client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    forbidden = client.patch(
        f"/api/v1/jobs/{slug}",
        headers=stranger,
        json={"title": "Taken"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Only the employer can edit this job"

    admin_edit = client.patch(
        f"/api/v1/jobs/{slug}",
        headers=admin_headers(client),
        json={"description": "Rewritten by admin."},
    )
    assert admin_edit.status_code == 403

    still_draft = create_job(client, employer, title="Unpublished role")
    admin_publish = client.post(
        f"/api/v1/jobs/{still_draft['slug']}/publish",
        headers=admin_headers(client),
    )
    assert admin_publish.status_code == 403
    assert admin_publish.json()["detail"] == "Only the employer can publish this job"

    cannot_delete = client.delete(f"/api/v1/jobs/{slug}", headers=stranger)
    assert cannot_delete.status_code == 403

    edited = client.patch(
        f"/api/v1/jobs/{slug}",
        headers=employer,
        json={"title": "Renamed", "skills": []},
    )
    assert edited.status_code == 200
    assert edited.json()["title"] == "Renamed"
    assert edited.json()["slug"] == slug
    assert edited.json()["skills"] == []

    removed = client.delete(f"/api/v1/jobs/{slug}", headers=admin_headers(client))
    assert removed.status_code == 204
    assert client.get(f"/api/v1/jobs/{slug}", headers=employer).status_code == 404


def test_bad_token_is_not_anonymous(client: TestClient) -> None:
    ok = client.get(f"/api/v1/jobs/{SEED_PUBLISHED}")
    assert ok.status_code == 200

    bad = client.get(
        f"/api/v1/jobs/{SEED_PUBLISHED}",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert bad.status_code == 401


def test_skills_count_published_jobs_only(client: TestClient) -> None:
    skills = client.get("/api/v1/skills")
    assert skills.status_code == 200
    counted = {item["name"]: item["job_count"] for item in skills.json()}
    assert counted == {"fastapi": 1, "postgres": 1, "python": 1}

    employer = register_headers(client, "tagger@example.com")
    created = create_job(client, employer, title="Soon live", skills=["django"])
    still = {item["name"] for item in client.get("/api/v1/skills").json()}
    assert "django" not in still

    client.post(f"/api/v1/jobs/{created['slug']}/publish", headers=employer)
    after = {item["name"]: item["job_count"] for item in client.get("/api/v1/skills").json()}
    assert after["django"] == 1


def test_openapi_documents_visibility_and_publish(client: TestClient) -> None:
    root = client.get("/")
    assert "/docs" in root.json()["message"]

    schema = client.get("/openapi.json").json()
    description = schema["info"]["description"].lower()
    assert "draft" in description
    assert "404" in description

    read_one = schema["paths"]["/api/v1/jobs/{slug}"]["get"]
    assert read_one["security"] == [{}, {"OAuth2PasswordBearer": []}]

    publish = schema["paths"]["/api/v1/jobs/{slug}/publish"]["post"]
    assert "draft" in publish["description"]
    assert publish["summary"] == "Publish a draft"

    create = schema["paths"]["/api/v1/jobs"]["post"]
    examples = create["requestBody"]["content"]["application/json"]["examples"]
    assert "from_title" in examples
    assert "custom_slug" in examples
