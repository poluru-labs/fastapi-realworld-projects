from fastapi.testclient import TestClient


def test_seed_students_and_report(client: TestClient) -> None:
    students = client.get("/api/v1/students")
    assert students.status_code == 200
    assert len(students.json()) == 2

    report = client.get("/api/v1/students/1/report")
    assert report.status_code == 200
    body = report.json()
    assert body["final_grade_count"] == 2
    assert body["average_percentage"] == 89.0


def test_list_grades_hides_drafts_by_default(client: TestClient) -> None:
    grades = client.get("/api/v1/grades", params={"course_id": 1})
    assert grades.status_code == 200
    assert len(grades.json()) == 2
    assert all(g["status"] == "final" for g in grades.json())

    with_drafts = client.get(
        "/api/v1/grades",
        params={"course_id": 1, "include_draft": True},
    )
    assert len(with_drafts.json()) == 3


def test_enroll_and_create_finalize_grade(client: TestClient) -> None:
    student = client.post(
        "/api/v1/students",
        json={"student_number": "stu-010", "full_name": "Carla Diaz"},
    )
    assert student.status_code == 201
    student_id = student.json()["id"]

    enrolled = client.post(
        "/api/v1/courses/2/enrollments",
        json={"student_id": student_id},
    )
    assert enrolled.status_code == 201

    again = client.post(
        "/api/v1/courses/2/enrollments",
        json={"student_id": student_id},
    )
    assert again.status_code == 409

    grade = client.post(
        "/api/v1/courses/2/grades",
        json={
            "student_id": student_id,
            "title": "Quiz 1",
            "category": "exam",
            "points_earned": 17,
            "points_possible": 20,
        },
    )
    assert grade.status_code == 201
    assert grade.json()["status"] == "draft"
    assert grade.json()["percentage"] == 85.0
    grade_id = grade.json()["id"]

    final = client.post(f"/api/v1/grades/{grade_id}/finalize")
    assert final.json()["status"] == "final"


def test_update_draft_only(client: TestClient) -> None:
    blocked = client.patch(
        "/api/v1/grades/1",
        json={"points_earned": 50},
    )
    assert blocked.status_code == 409

    ok = client.patch(
        "/api/v1/grades/3",
        json={"points_earned": 8},
    )
    assert ok.status_code == 200
    assert ok.json()["points_earned"] == 8.0


def test_duplicate_student_number(client: TestClient) -> None:
    response = client.post(
        "/api/v1/students",
        json={"student_number": "stu-001", "full_name": "Duplicate"},
    )
    assert response.status_code == 409


def test_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/students/999").status_code == 404


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
