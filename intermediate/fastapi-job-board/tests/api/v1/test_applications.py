from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, create_job, register_headers

SEED_PUBLISHED = "senior-fastapi-engineer"
SEED_DRAFT = "draft-frontend-contract"


def test_applications_follow_publish_state(client: TestClient) -> None:
    employer = register_headers(client, "employer@example.com", full_name="Employer")
    candidate = register_headers(client, "candidate@example.com", full_name="Candidate")
    created = create_job(client, employer, title="Application target")
    slug = created["slug"]

    hidden_from_candidate = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "Cannot see this draft."},
    )
    assert hidden_from_candidate.status_code == 404

    on_draft = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=employer,
        json={"cover_letter": "Too early."},
    )
    assert on_draft.status_code == 409
    assert on_draft.json()["detail"] == "Only published jobs accept applications"

    missing_token = client.post(
        f"/api/v1/jobs/{SEED_PUBLISHED}/applications",
        json={"cover_letter": "Hello."},
    )
    assert missing_token.status_code == 401

    client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    created_application = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "  Ready to join.  "},
    )
    assert created_application.status_code == 201
    body = created_application.json()
    assert body["cover_letter"] == "Ready to join."
    assert body["applicant_name"] == "Candidate"
    assert body["status"] == "submitted"

    listed = client.get(
        f"/api/v1/jobs/{slug}/applications",
        headers=employer,
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == body["id"]

    job = client.get(f"/api/v1/jobs/{slug}").json()
    assert job["application_count"] == 1


def test_employer_only_application_list(client: TestClient) -> None:
    stranger = register_headers(client, "lurker@example.com")
    denied = client.get(
        f"/api/v1/jobs/{SEED_PUBLISHED}/applications",
        headers=stranger,
    )
    assert denied.status_code == 403

    anonymous = client.get(f"/api/v1/jobs/{SEED_PUBLISHED}/applications")
    assert anonymous.status_code == 401


def test_who_can_delete_an_application(client: TestClient) -> None:
    employer = register_headers(client, "poster@example.com", full_name="Poster")
    candidate = register_headers(client, "fan@example.com", full_name="Fan")
    stranger = register_headers(client, "passer@example.com", full_name="Passer")
    created = create_job(client, employer, title="Moderation")
    slug = created["slug"]
    client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)

    application = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "First."},
    ).json()

    denied = client.delete(
        f"/api/v1/jobs/{slug}/applications/{application['id']}",
        headers=stranger,
    )
    assert denied.status_code == 403

    by_employer = client.delete(
        f"/api/v1/jobs/{slug}/applications/{application['id']}",
        headers=employer,
    )
    assert by_employer.status_code == 204

    again = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "Second try."},
    ).json()

    by_candidate = client.delete(
        f"/api/v1/jobs/{slug}/applications/{again['id']}",
        headers=candidate,
    )
    assert by_candidate.status_code == 204

    third = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "Third."},
    ).json()
    by_admin = client.delete(
        f"/api/v1/jobs/{slug}/applications/{third['id']}",
        headers=admin_headers(client),
    )
    assert by_admin.status_code == 204
    assert client.get(f"/api/v1/jobs/{slug}/applications", headers=employer).json()["total"] == 0


def test_application_must_belong_to_the_job_in_the_path(client: TestClient) -> None:
    seed = client.get(
        f"/api/v1/jobs/{SEED_PUBLISHED}/applications",
        headers=admin_headers(client),
    ).json()
    seed_application_id = seed["items"][0]["id"]

    employer = register_headers(client, "otherjob@example.com")
    created = create_job(client, employer, title="Different job")
    client.post(f"/api/v1/jobs/{created['slug']}/publish", headers=employer)

    missing = client.delete(
        f"/api/v1/jobs/{created['slug']}/applications/{seed_application_id}",
        headers=employer,
    )
    assert missing.status_code == 404

    draft_list = client.get(
        f"/api/v1/jobs/{SEED_DRAFT}/applications",
        headers=admin_headers(client),
    )
    assert draft_list.status_code == 200
    assert draft_list.json()["total"] == 0


def test_deleting_a_job_deletes_its_applications(client: TestClient) -> None:
    employer = register_headers(client, "cleaner@example.com")
    candidate = register_headers(client, "applicant@example.com")
    created = create_job(client, employer, title="Temporary")
    slug = created["slug"]
    client.post(f"/api/v1/jobs/{slug}/publish", headers=employer)
    application = client.post(
        f"/api/v1/jobs/{slug}/applications",
        headers=candidate,
        json={"cover_letter": "Gone with the job."},
    ).json()

    removed = client.delete(f"/api/v1/jobs/{slug}", headers=employer)
    assert removed.status_code == 204

    leftover = client.delete(
        f"/api/v1/jobs/{slug}/applications/{application['id']}",
        headers=employer,
    )
    assert leftover.status_code == 404
