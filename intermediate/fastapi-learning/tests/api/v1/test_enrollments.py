from fastapi.testclient import TestClient

from tests.api.v1.helpers import register_headers


def test_enroll_and_complete_course(client: TestClient) -> None:
    student = register_headers(client, "graduate@example.com")
    enrolled = client.post(
        "/api/v1/enrollments",
        headers=student,
        json={"course_slug": "fastapi-fundamentals"},
    )
    assert enrolled.status_code == 201
    enrollment_id = enrolled.json()["id"]
    assert enrolled.json()["total_lessons"] == 2

    client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/welcome/complete",
        headers=student,
    )
    mid = client.get(f"/api/v1/enrollments/{enrollment_id}", headers=student).json()
    assert mid["completed_lessons"] == 1
    assert mid["status"] == "active"

    done = client.post(
        f"/api/v1/enrollments/{enrollment_id}/lessons/routing-and-deps/complete",
        headers=student,
    )
    assert done.json()["status"] == "completed"
    assert done.json()["progress_percent"] == 100


def test_duplicate_enrollment_conflict(client: TestClient) -> None:
    student = register_headers(client, "dup@example.com")
    payload = {"course_slug": "fastapi-fundamentals"}
    assert client.post("/api/v1/enrollments", headers=student, json=payload).status_code == 201
    again = client.post("/api/v1/enrollments", headers=student, json=payload)
    assert again.status_code == 409


def test_other_users_enrollment_not_found(client: TestClient) -> None:
    owner = register_headers(client, "owner@example.com")
    other = register_headers(client, "other@example.com")
    enrollment = client.post(
        "/api/v1/enrollments",
        headers=owner,
        json={"course_slug": "fastapi-fundamentals"},
    ).json()
    response = client.get(f"/api/v1/enrollments/{enrollment['id']}", headers=other)
    assert response.status_code == 404
