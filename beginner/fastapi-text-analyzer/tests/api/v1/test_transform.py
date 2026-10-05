from fastapi.testclient import TestClient


def _transform(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/v1/transform", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_slug_title_and_reverse(client: TestClient) -> None:
    slug = _transform(client, {"text": "Hello, World!", "mode": "slug"})
    assert slug["result"] == "hello-world"
    assert slug["original"] == "Hello, World!"

    title = _transform(client, {"text": "don't stop", "mode": "title"})
    assert title["result"] == "Don't Stop"

    reverse = _transform(client, {"text": "ab c", "mode": "reverse"})
    assert reverse["result"] == "c ba"


def test_case_modes(client: TestClient) -> None:
    assert _transform(client, {"text": "Hello", "mode": "upper"})["result"] == "HELLO"
    assert _transform(client, {"text": "Hello", "mode": "LOWER"})["result"] == "hello"


def test_slug_without_letters_is_empty(client: TestClient) -> None:
    body = _transform(client, {"text": "!!!", "mode": "slug"})
    assert body["result"] == ""


def test_unknown_mode_and_blank_text(client: TestClient) -> None:
    unknown = client.post("/api/v1/transform", json={"text": "Hello", "mode": "camel"})
    assert unknown.status_code == 422
    blank = client.post("/api/v1/transform", json={"text": "\n\t", "mode": "lower"})
    assert blank.status_code == 422
