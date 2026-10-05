from fastapi.testclient import TestClient


def _convert(client: TestClient, payload: dict) -> dict:
    response = client.post("/api/v1/convert", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_celsius_to_fahrenheit(client: TestClient) -> None:
    body = _convert(
        client,
        {
            "category": "temperature",
            "value": 100,
            "from_unit": "celsius",
            "to_unit": "fahrenheit",
        },
    )
    assert body["result"] == 212
    assert body["from_symbol"] == "°C"
    assert body["to_symbol"] == "°F"
    assert body["formula"] == "°F = (°C × 9/5) + 32"


def test_alias_case_and_whitespace(client: TestClient) -> None:
    body = _convert(
        client,
        {"category": " Temperature ", "value": 0, "from_unit": " C ", "to_unit": "F"},
    )
    assert body["result"] == 32
    assert body["from_unit"] == "celsius"
    assert body["to_unit"] == "fahrenheit"


def test_celsius_to_kelvin_and_absolute_zero(client: TestClient) -> None:
    freezing = _convert(
        client,
        {"category": "temperature", "value": 0, "from_unit": "celsius", "to_unit": "kelvin"},
    )
    assert freezing["result"] == 273.15

    absolute = _convert(
        client,
        {
            "category": "temperature",
            "value": -273.15,
            "from_unit": "celsius",
            "to_unit": "fahrenheit",
        },
    )
    assert absolute["result"] == -459.67

    zero_kelvin = _convert(
        client,
        {"category": "temperature", "value": 0, "from_unit": "k", "to_unit": "celsius"},
    )
    assert zero_kelvin["result"] == -273.15
    assert zero_kelvin["from_unit"] == "kelvin"


def test_negative_forty_is_the_same_on_both_scales(client: TestClient) -> None:
    body = _convert(
        client,
        {"category": "temperature", "value": -40, "from_unit": "celsius", "to_unit": "f"},
    )
    assert body["result"] == -40


def test_below_absolute_zero(client: TestClient) -> None:
    response = client.post(
        "/api/v1/convert",
        json={"category": "temperature", "value": -300, "from_unit": "celsius", "to_unit": "k"},
    )
    assert response.status_code == 422
    assert "absolute zero" in response.json()["detail"]


def test_inch_to_centimeter_and_foot_to_inch(client: TestClient) -> None:
    inch = _convert(
        client,
        {"category": "distance", "value": 1, "from_unit": "in", "to_unit": "cm"},
    )
    assert inch["result"] == 2.54
    assert inch["from_unit"] == "inch"
    assert "base unit: meter" in inch["formula"]

    foot = _convert(
        client,
        {"category": "distance", "value": 1, "from_unit": "foot", "to_unit": "inch"},
    )
    assert foot["result"] == 12


def test_mile_and_kilometer(client: TestClient) -> None:
    mile = _convert(
        client,
        {"category": "distance", "value": 1, "from_unit": "mile", "to_unit": "kilometer"},
    )
    assert mile["result"] == 1.609344

    back = _convert(
        client,
        {"category": "distance", "value": 1.609344, "from_unit": "km", "to_unit": "mi"},
    )
    assert back["result"] == 1


def test_weight_conversions(client: TestClient) -> None:
    grams = _convert(
        client,
        {"category": "weight", "value": 1000, "from_unit": "g", "to_unit": "kg"},
    )
    assert grams["result"] == 1

    pounds = _convert(
        client,
        {"category": "weight", "value": 1, "from_unit": "kg", "to_unit": "lb"},
    )
    assert pounds["result"] == 2.204623

    ounces = _convert(
        client,
        {"category": "weight", "value": 1, "from_unit": "lb", "to_unit": "g"},
    )
    assert ounces["result"] == 453.59237


def test_same_unit_returns_input(client: TestClient) -> None:
    body = _convert(
        client,
        {"category": "distance", "value": 5.5, "from_unit": "mm", "to_unit": "millimeter"},
    )
    assert body["result"] == 5.5
    assert body["formula"] == "result = value"
    assert body["from_unit"] == "millimeter"


def test_unknown_unit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/convert",
        json={"category": "distance", "value": 1, "from_unit": "stone", "to_unit": "meter"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "stone" in detail
    assert "meter" in detail


def test_unit_must_belong_to_category(client: TestClient) -> None:
    response = client.post(
        "/api/v1/convert",
        json={"category": "distance", "value": 1, "from_unit": "celsius", "to_unit": "meter"},
    )
    assert response.status_code == 400


def test_negative_distance_and_non_finite_value(client: TestClient) -> None:
    negative = client.post(
        "/api/v1/convert",
        json={"category": "distance", "value": -1, "from_unit": "meter", "to_unit": "foot"},
    )
    assert negative.status_code == 422

    infinite = client.post(
        "/api/v1/convert",
        json={
            "category": "temperature",
            "value": "NaN",
            "from_unit": "celsius",
            "to_unit": "kelvin",
        },
    )
    assert infinite.status_code == 422

    missing = client.post("/api/v1/convert", json={"category": "weight", "value": 1})
    assert missing.status_code == 422
