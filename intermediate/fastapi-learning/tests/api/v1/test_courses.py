from fastapi.testclient import TestClient

from tests.api.v1.helpers import admin_headers, register_headers


def test_public_catalog_hides_drafts(client: TestClient) -> None:
    courses = client.get("/api/v1/courses")
    assert courses.status_code == 200
    slugs = {row["slug"] for row in courses.json()}
    assert slugs == {"fastapi-fundamentals"}
    assert client.get("/api/v1/courses/draft-async-deep-dive").status_code == 404

    admin = admin_headers(client)
    assert client.get("/api/v1/courses/draft-async-deep-dive", headers=admin).status_code == 200


def test_lesson_body_hidden_until_enrolled(client: TestClient) -> None:
    guest = client.get("/api/v1/courses/fastapi-fundamentals/lessons/routing-and-deps")
    assert guest.status_code == 200
    assert guest.json()["body"] == ""

    student = register_headers(client, "learner@example.com")
    client.post(
        "/api/v1/enrollments",
        headers=student,
        json={"course_slug": "fastapi-fundamentals"},
    )
    enrolled = client.get(
        "/api/v1/courses/fastapi-fundamentals/lessons/routing-and-deps",
        headers=student,
    )
    assert enrolled.json()["body"] != ""


def test_admin_creates_course(client: TestClient) -> None:
    admin = admin_headers(client)
    created = client.post(
        "/api/v1/courses",
        headers=admin,
        json={
            "title": "API Design",
            "summary": "Contracts and docs.",
            "level": "advanced",
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"
