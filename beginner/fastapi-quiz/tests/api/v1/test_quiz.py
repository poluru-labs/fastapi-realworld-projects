from fastapi.testclient import TestClient

PUBLISHED_ID = 1
DRAFT_ID = 2


def test_list_defaults_to_published(client: TestClient) -> None:
    listed = client.get("/api/v1/quizzes")
    assert listed.status_code == 200
    assert [quiz["id"] for quiz in listed.json()] == [PUBLISHED_ID]

    drafts = client.get("/api/v1/quizzes", params={"status": "draft"})
    assert [quiz["id"] for quiz in drafts.json()] == [DRAFT_ID]


def test_play_hides_answers_and_submit_scores(client: TestClient) -> None:
    play = client.get(f"/api/v1/quizzes/{PUBLISHED_ID}/play")
    assert play.status_code == 200
    body = play.json()
    assert len(body["questions"]) == 3
    assert "correct_index" not in body["questions"][0]

    draft_play = client.get(f"/api/v1/quizzes/{DRAFT_ID}/play")
    assert draft_play.status_code == 404

    submit = client.post(
        f"/api/v1/quizzes/{PUBLISHED_ID}/submit",
        json={
            "participant_name": "Alex",
            "answers": [
                {"question_id": 1, "choice_index": 1},
                {"question_id": 2, "choice_index": 1},
                {"question_id": 3, "choice_index": 1},
            ],
        },
    )
    assert submit.status_code == 200
    result = submit.json()
    assert result["score"] == 3
    assert result["percentage"] == 100.0
    assert all(item["correct"] for item in result["results"])


def test_author_can_edit_draft_questions(client: TestClient) -> None:
    created = client.post(
        "/api/v1/quizzes",
        json={"title": "New quiz", "description": "Demo"},
    )
    assert created.status_code == 201
    quiz_id = created.json()["id"]

    question = client.post(
        f"/api/v1/quizzes/{quiz_id}/questions",
        json={
            "prompt": "2 + 2?",
            "choices": ["3", "4", "5"],
            "correct_index": 1,
        },
    )
    assert question.status_code == 201
    question_id = question.json()["id"]

    published = client.post(f"/api/v1/quizzes/{quiz_id}/publish")
    assert published.status_code == 200

    blocked = client.patch(
        f"/api/v1/questions/{question_id}",
        json={"prompt": "Changed"},
    )
    assert blocked.status_code == 409


def test_publish_requires_questions(client: TestClient) -> None:
    created = client.post("/api/v1/quizzes", json={"title": "Empty", "description": ""})
    quiz_id = created.json()["id"]
    assert client.post(f"/api/v1/quizzes/{quiz_id}/publish").status_code == 409
