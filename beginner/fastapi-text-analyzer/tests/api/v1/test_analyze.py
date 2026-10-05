from fastapi.testclient import TestClient


def _analyze(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_greeting_counts(client: TestClient) -> None:
    body = _analyze(client, {"text": "Hello, world! Hello."})
    assert body["characters"] == 20
    assert body["characters_no_spaces"] == 18
    assert body["words"] == 3
    assert body["unique_words"] == 2
    assert body["sentences"] == 2
    assert body["paragraphs"] == 1
    assert body["average_word_length"] == 5
    assert body["reading_time_seconds"] == 1
    assert body["is_palindrome"] is False
    assert body["top_words"] == [
        {"word": "hello", "count": 2},
        {"word": "world", "count": 1},
    ]


def test_palindrome_ignores_punctuation(client: TestClient) -> None:
    body = _analyze(client, {"text": "A man, a plan, a canal: Panama"})
    assert body["is_palindrome"] is True
    assert body["words"] == 7


def test_stop_words_affect_ranking_only(client: TestClient) -> None:
    body = _analyze(
        client,
        {"text": "The cat and the dog", "ignore_stop_words": True, "top_n": 5},
    )
    assert body["words"] == 5
    assert body["unique_words"] == 4
    assert body["top_words"] == [
        {"word": "cat", "count": 1},
        {"word": "dog", "count": 1},
    ]


def test_paragraphs_and_contraction(client: TestClient) -> None:
    body = _analyze(client, {"text": "Don't stop.\n\nKeep going!"})
    assert body["paragraphs"] == 2
    assert body["sentences"] == 2
    assert body["words"] == 4
    assert "don't" in {item["word"] for item in body["top_words"]}


def test_punctuation_only_has_no_words(client: TestClient) -> None:
    body = _analyze(client, {"text": "!!!"})
    assert body["words"] == 0
    assert body["sentences"] == 0
    assert body["paragraphs"] == 1
    assert body["average_word_length"] == 0
    assert body["reading_time_seconds"] == 0
    assert body["is_palindrome"] is False
    assert body["top_words"] == []


def test_reading_time_rounds_half_up(client: TestClient) -> None:
    one_word = _analyze(client, {"text": "Hi"})
    assert one_word["reading_time_seconds"] == 0
    two_words = _analyze(client, {"text": "Hi there"})
    assert two_words["reading_time_seconds"] == 1
    passage = _analyze(client, {"text": "word " * 200})
    assert passage["words"] == 200
    assert passage["reading_time_seconds"] == 60


def test_top_n_limits_the_list(client: TestClient) -> None:
    body = _analyze(client, {"text": "one two three", "top_n": 1})
    assert body["top_words"] == [{"word": "one", "count": 1}]


def test_blank_and_oversized_text(client: TestClient) -> None:
    blank = client.post("/api/v1/analyze", json={"text": "   "})
    assert blank.status_code == 422
    oversized = client.post("/api/v1/analyze", json={"text": "a" * 10_001})
    assert oversized.status_code == 422
    bad_top = client.post("/api/v1/analyze", json={"text": "Hello", "top_n": 0})
    assert bad_top.status_code == 422
