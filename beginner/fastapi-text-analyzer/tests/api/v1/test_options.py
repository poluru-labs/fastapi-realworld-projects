from fastapi.testclient import TestClient


def test_list_options(client: TestClient) -> None:
    response = client.get("/api/v1/options")
    assert response.status_code == 200
    body = response.json()
    assert body["reading_words_per_minute"] == 200
    assert body["max_text_length"] == 10_000
    assert body["max_top_n"] == 50
    assert body["transform_modes"] == ["lower", "upper", "title", "reverse", "slug"]
    assert body["stop_word_count"] == len(body["stop_words"])
    assert body["stop_words"] == sorted(body["stop_words"])
    assert "the" in body["stop_words"]
    assert "and" in body["stop_words"]
